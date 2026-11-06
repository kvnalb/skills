#!/usr/bin/env python3
"""slides-rag: index lecture PDFs once, then retrieve single slides cheaply.

Artifacts live in $SLIDES_RAG_HOME (default ~/.local/share/slides-rag):
    <sha16>/manifest.json   source, hash, page count, timing, file locations
    <sha16>/lecture.md      Markdown with explicit page boundaries
    <sha16>/pages.jsonl     per-page text, OCR, flags (source of the search index)
    <sha16>/pages/p0001.png slide images
    index.sqlite            FTS5 index, derived; rebuilt from pages.jsonl if lost
    usage.jsonl             retrieval log
"""
import argparse, hashlib, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("SLIDES_RAG_HOME", "~/.local/share/slides-rag")).expanduser()
DB, LOG = HOME / "index.sqlite", HOME / "usage.jsonl"
SCHEMA = 1        # bump when the artifact format changes; older entries get rebuilt
MAX_EDGE = 1568   # long edge in px. Read costs ~w*h/750 tokens: measured 1.9k here, 3.1k at 2880 px. Use crop for fine notation.
LOW_TEXT = 40     # chars; below this a slide is effectively image-only
IMG_MIN = 0.005   # image covering this fraction of a slide counts; equations are often tiny images with no text
IMG_OCR = 0.25    # image coverage that makes OCR worthwhile (equation snippets just yield OCR noise)
STROKES = 3       # non-template lines/curves/outlined shapes: tables, arrows, diagrams
SHAPES = 10       # or this many shapes of any kind (unoutlined box diagrams)
GARBLED_MIN = 8   # unmapped glyphs on a slide before the whole slide is suspect
GAP = "⟦?⟧"  # stands in for a glyph with no Unicode mapping, so a loss is visible, not silent
MATH_FONT = re.compile(r"^(CM(MI|SY|EX|BSY)|MSAM|MSBM|STIX|Symbol|MathJax|LatinModernMath|CambriaMath|MT-?Extra|Euclid|txsy|txmi|pxsy|pxmi)", re.I)
MATH_CHAR = re.compile("[̀-ͯΑ-ω⁰-₟∀-⋿⨀-⫿\U0001d400-\U0001d7ff]")
UNMAPPED = re.compile("[�-]|\\(cid:\\d+\\)")  # e.g. Inter's alternates put ( ) [ ] : | in the private use area


def pymupdf():
    """Import PyMuPDF lazily: search and show never need it."""
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        if shutil.which("uv") and not os.environ.get("SLIDES_RAG_UV"):
            os.environ["SLIDES_RAG_UV"] = "1"
            os.execvp("uv", ["uv", "run", "--no-project", "--with", "pymupdf", "python", __file__, *sys.argv[1:]])
        sys.exit("PyMuPDF is missing. Run: python3 -m pip install pymupdf")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(d):
    return json.loads((d / "manifest.json").read_text())


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dir_size(d):
    return sum(f.stat().st_size for f in d.rglob("*") if f.is_file())


# ---------------------------------------------------------------- extraction

def extract_page(page, flags):
    text, gaps = UNMAPPED.subn(GAP, page.get_text("text", flags=flags).strip())
    annots = [(a.type[1], (a.info.get("content") or "").strip()) for a in page.annots() or []]
    notes = [f"[PDF annotation: {kind}] {body}" for kind, body in annots if body]
    area = abs(page.rect) or 1
    images = [(i["xref"], abs(page.rect & i["bbox"]) / area) for i in page.get_image_info(xrefs=True)]
    shapes = [(tuple(round(v) for v in d["rect"]), d["type"] != "f" or any(i[0] != "re" for i in d["items"]))
              for d in page.get_drawings()]
    fonts = {f[3].split("+")[-1] for f in page.get_fonts()}
    return dict(text="\n".join([text, *notes]).strip(), gaps=gaps, annotated=bool(annots), images=images, shapes=shapes, fonts=fonts)


def page_flags(p, repeated_images, repeated_shapes):
    """Reasons extracted text may misrepresent the slide. Empty means text is probably enough."""
    flags = []
    if len(p["text"]) < LOW_TEXT:
        flags.append("low_text")
    if p["gaps"] >= GARBLED_MIN:
        flags.append("garbled")
    if MATH_CHAR.search(p["text"]) or any(MATH_FONT.match(f) for f in p["fonts"]):
        flags.append("math")
    if any(a >= IMG_MIN and x not in repeated_images for x, a in p["images"]):
        flags.append("image")
    own = [stroked for key, stroked in p["shapes"] if key not in repeated_shapes]
    if sum(own) >= STROKES or len(own) >= SHAPES:
        flags.append("diagram")
    if p["annotated"]:
        flags.append("annotated")
    return flags


def find_builds(texts):
    """Group consecutive slides where each one keeps the previous slide's words.

    ponytail: word containment misses builds that only move or swap content; those
    just stay ungrouped, which is the safe failure. Nothing is ever dropped from a group.
    """
    n = len(texts)
    common = Counter(l for t in texts for l in set(t.splitlines()))
    def words(t):
        kept = [l for l in t.splitlines() if common[l] <= max(5, n / 2) and not l.strip().isdigit()]
        return Counter(re.findall(r"\w+", " ".join(kept).lower()))
    bags = [words(t) for t in texts]
    start = list(range(n))
    for i in range(1, n):
        prev, cur = bags[i - 1], bags[i]
        size = sum(prev.values())
        if size >= 4 and sum((prev & cur).values()) / size >= 0.85:
            start[i] = start[i - 1]
    last = {}
    for i, s in enumerate(start):
        last[s] = i
    return [(s + 1, last[s] + 1) for s in start]  # (first, last) 1-based, per page


def ocr(png):
    """Search-only OCR text; empty when tesseract is unavailable. Never shown as slide content."""
    if not shutil.which("tesseract"):
        return ""
    r = subprocess.run(["tesseract", str(png), "stdout"], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    return r.stdout.strip() if r.returncode == 0 else ""


def render(page, out, clip=None):
    rect = clip or page.rect
    fz = pymupdf()
    zoom = min(MAX_EDGE / max(rect.width, rect.height), 8)
    page.get_pixmap(matrix=fz.Matrix(zoom, zoom), clip=clip, alpha=False).save(out)


def build(pdf, sha):
    fz = pymupdf()
    t0 = time.perf_counter()
    doc = fz.open(pdf)
    if doc.needs_pass:
        raise ValueError("password-protected")
    if not doc.page_count:
        raise ValueError("no pages")
    n = doc.page_count
    keep = fz.TEXT_PRESERVE_WHITESPACE | fz.TEXT_MEDIABOX_CLIP  # no ligature preservation: "fi" must stay searchable
    raw = [extract_page(p, keep) for p in doc]
    images, shapes, area = Counter(), Counter(), {}
    for p in raw:
        images.update({x for x, _ in p["images"]})
        shapes.update({key for key, _ in p["shapes"]})
        area.update((x, max(a, area.get(x, 0))) for x, a in p["images"])
    # Logos, emoji and theme furniture repeat across the deck and say nothing about one slide.
    # A big image that recurs may be real content, so only small ones are discounted early.
    rep_img = {x for x, c in images.items() if n >= 4 and (c > n / 2 or (c > n * 0.1 and area[x] < 0.03))}
    rep_shape = {s for s, c in shapes.items() if n >= 4 and c > n * 0.3}
    builds = find_builds([p["text"] for p in raw])
    t1 = time.perf_counter()

    tmp = Path(tempfile.mkdtemp(dir=HOME, prefix=".tmp-"))
    try:
        (tmp / "pages").mkdir()
        for i, page in enumerate(doc, 1):
            render(page, tmp / "pages" / f"p{i:04d}.png")
        t2 = time.perf_counter()
        rows = [dict(page=i, text=p["text"], flags=page_flags(p, rep_img, rep_shape), build=list(builds[i - 1]), ocr="")
                for i, p in enumerate(raw, 1)]
        todo = [r for r, p in zip(rows, raw) if len(p["text"]) < LOW_TEXT or sum(a for _, a in p["images"]) >= IMG_OCR]
        with ThreadPoolExecutor() as pool:
            for r, text in zip(todo, pool.map(lambda r: ocr(tmp / "pages" / f"p{r['page']:04d}.png"), todo)):
                r["ocr"] = text
        t3 = time.perf_counter()
        (tmp / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        md = [f"# {pdf.stem}\n\nSource: {pdf}\nSHA-256: {sha}\nPages: {n}\n\n"
              "> Extracted text is unverified. Formulas, tables and diagrams can be wrong or missing here; "
              "the page image and the original PDF are authoritative.\n"]
        for r in rows:
            first, last = r["build"]
            md.append(f"\n<!-- page {r['page']} -->\n## Slide {r['page']}\n\n"
                      f"image: pages/p{r['page']:04d}.png\n"
                      + (f"view: {', '.join(r['flags'])}\n" if r["flags"] else "")
                      + (f"build: {first}-{last}\n" if first != last else "")
                      + f"\n{r['text'] or '(no extractable text)'}\n")
        (tmp / "lecture.md").write_text("".join(md))
        stat = pdf.stat()
        (tmp / "manifest.json").write_text(json.dumps(dict(
            schema=SCHEMA, title=pdf.stem, source=str(pdf), sha256=sha, pages=n, size=stat.st_size,
            mtime=stat.st_mtime, indexed_at=now(), page_edge_px=MAX_EDGE,
            files=dict(markdown="lecture.md", pages="pages.jsonl", images="pages/p%04d.png"),
            timing_s=dict(extract=round(t1 - t0, 3), render=round(t2 - t1, 3), ocr=round(t3 - t2, 3)),
            cache_bytes=dir_size(tmp)), indent=1))
        dest = HOME / sha[:16]
        shutil.rmtree(dest, ignore_errors=True)
        os.replace(tmp, dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return dest


def valid(d, sha):
    try:
        m = manifest(d)
        lines = (d / "pages.jsonl").read_text().splitlines()
        return (m["schema"] == SCHEMA and m["sha256"] == sha and len(lines) == m["pages"] and (d / "lecture.md").exists()
                and all((d / "pages" / f"p{i:04d}.png").stat().st_size for i in range(1, m["pages"] + 1)))
    except (OSError, ValueError, KeyError):
        return False


# ---------------------------------------------------------------- database

def load_entry(con, d):
    m = manifest(d)
    sha = m["sha256"]
    drop_rows(con, sha)
    con.execute("INSERT INTO lectures VALUES (?,?,?,?,?)", (sha, m["title"], m["source"], m["pages"], m["indexed_at"]))
    for line in (d / "pages.jsonl").read_text().splitlines():
        r = json.loads(line)
        con.execute("INSERT INTO pages VALUES (?,?,?,?,?,?)",
                    (sha, r["page"], ",".join(r["flags"]), r["build"][0], r["build"][1], r["text"]))
        con.execute("INSERT INTO fts VALUES (?,?,?,?)", (sha, r["page"], r["text"], r["ocr"]))


def drop_rows(con, sha):
    for table in ("lectures", "pages", "fts"):
        con.execute(f"DELETE FROM {table} WHERE sha=?", (sha,))


def connect():
    HOME.mkdir(parents=True, exist_ok=True)
    try:
        con = sqlite3.connect(DB)
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE IF NOT EXISTS lectures(sha TEXT PRIMARY KEY, title, source, pages, indexed_at);
            CREATE TABLE IF NOT EXISTS pages(sha, page, flags, build_first, build_last, text, PRIMARY KEY(sha, page));
            CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(sha UNINDEXED, page UNINDEXED, text, ocr, tokenize='porter unicode61');
        """)
        on_disk = {p.parent.name: p.parent for p in HOME.glob("*/manifest.json")}
        known = {r["sha"][:16]: r["sha"] for r in con.execute("SELECT sha FROM lectures")}
    except sqlite3.DatabaseError:  # corrupt index: it is derived, so rebuild it
        DB.unlink(missing_ok=True)
        return connect()
    for short, sha in known.items():
        if short not in on_disk:
            drop_rows(con, sha)
    for short, d in on_disk.items():
        if short not in known:
            try:
                load_entry(con, d)
            except (OSError, ValueError, KeyError) as e:
                print(f"skipping damaged cache entry {short}: {e}", file=sys.stderr)
    con.commit()
    return con


def find_lectures(con, ref):
    rows = con.execute("SELECT * FROM lectures ORDER BY source").fetchall()
    ref = ref.lower().strip()
    if re.fullmatch(r"[0-9a-f]{6,64}", ref):
        hit = [r for r in rows if r["sha"].startswith(ref)]
        if hit:
            return hit
    tokens = ref.split()
    hit = [r for r in rows if all(t in r["source"].lower() for t in tokens)]
    exact = [r for r in hit if r["title"].lower() == ref] or [r for r in hit if r["title"].lower().startswith(ref)]
    return exact or hit


def one_lecture(con, ref):
    rows = find_lectures(con, ref)
    if len(rows) == 1:
        return rows[0]
    if not rows:
        sys.exit(f"No indexed lecture matches {ref!r}. Run `status --list`, or `index <pdf>`.")
    sys.exit(f"{ref!r} is ambiguous:\n" + "\n".join(f"  {r['sha'][:8]}  {r['title']}  ({r['source']})" for r in rows))


# ---------------------------------------------------------------- retrieval log

def emit(cmd, lines, images=0):
    out = "\n".join(lines)
    print(out)
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps(dict(ts=now(), cmd=cmd, chars=len(out), image_paths=images)) + "\n")
    except OSError:
        pass  # logging must never block retrieval


# ---------------------------------------------------------------- commands

def collect_pdfs(paths):
    found, missing = [], []
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if p.is_dir():
            found += sorted(f for f in p.rglob("*") if f.suffix.lower() == ".pdf" and f.is_file()
                            and not any(part.startswith(".") for part in f.relative_to(p).parts))
        elif p.is_file():
            found.append(p)
        else:
            missing.append(raw)
    return found, missing


def index_one(con, pdf, force=False):
    sha = sha256(pdf)
    d = HOME / sha[:16]
    state = "indexed"
    if not force and valid(d, sha):
        m = manifest(d)
        if m["source"] == str(pdf):
            state = "unchanged"
        elif Path(m["source"]).exists():
            return f"duplicate of {m['source']}"
        else:
            old = m["source"]
            m.update(source=str(pdf), title=pdf.stem)
            (d / "manifest.json").write_text(json.dumps(m, indent=1))
            state = f"moved from {old}"
    else:
        build(pdf, sha)
    load_entry(con, d)
    for r in con.execute("SELECT sha FROM lectures WHERE source=? AND sha!=?", (str(pdf), sha)).fetchall():
        drop_rows(con, r["sha"])  # same path, new content: the old version is stale
        shutil.rmtree(HOME / r["sha"][:16], ignore_errors=True)
        state = "reindexed (source changed)"
    con.commit()
    return state


def run_index(con, paths, force):
    pdfs, missing = collect_pdfs(paths)
    tally, failed = Counter(), 0
    for ref in missing:
        print(f"not found: {ref}", file=sys.stderr)
        failed += 1
    for pdf in pdfs:
        try:
            state = index_one(con, pdf, force)
        except Exception as e:  # one bad PDF must not stop a directory run
            print(f"FAILED {pdf}: {e}", file=sys.stderr)
            failed += 1
            continue
        tally["unchanged" if state == "unchanged" else state.split()[0]] += 1
        if state != "unchanged":
            print(f"{state}: {pdf.name}")
    print(", ".join(f"{v} {k}" for k, v in sorted(tally.items())) or "nothing to index")
    return failed


def cmd_index(a):
    sys.exit(1 if run_index(connect(), a.paths, a.force) else 0)


def cmd_refresh(a):
    con = connect()
    failed = run_index(con, a.paths, a.force) if a.paths else 0
    for r in con.execute("SELECT * FROM lectures").fetchall():
        src = Path(r["source"])
        if src.exists():
            try:
                state = index_one(con, src, a.force)
                if state != "unchanged":
                    print(f"{state}: {src.name}")
            except Exception as e:
                print(f"FAILED {src}: {e}", file=sys.stderr)
                failed += 1
        elif a.prune:
            drop_rows(con, r["sha"])
            shutil.rmtree(HOME / r["sha"][:16], ignore_errors=True)
            con.commit()
            print(f"pruned: {r['title']}")
        else:
            print(f"source missing, cache kept: {r['title']} ({r['source']})")
    print("refresh complete")
    sys.exit(1 if failed else 0)


def fts_query(query, joiner):
    terms = re.findall(r'"[^"]+"|[^\s"]+', query)
    quoted = ['"' + t.strip('"').replace('"', '') + '"' for t in terms]
    return f" {joiner} ".join(q for q in quoted if q.strip('"'))


def cmd_search(a):
    con = connect()
    scope = find_lectures(con, a.lecture) if a.lecture else None
    if a.lecture and not scope:
        sys.exit(f"No indexed lecture matches {a.lecture!r}.")
    if not con.execute("SELECT 1 FROM lectures LIMIT 1").fetchone():
        sys.exit("Nothing indexed yet. Run `index <pdf or directory>`.")
    filt, args = "", []
    if scope:
        filt = f"AND fts.sha IN ({','.join('?' * len(scope))})"
        args = [r["sha"] for r in scope]
    sql = f"""SELECT fts.sha, fts.page, l.title, p.flags, p.build_first, p.build_last,
                     snippet(fts, 2, '«', '»', ' … ', 20) AS snip
              FROM fts JOIN lectures l ON l.sha=fts.sha JOIN pages p ON p.sha=fts.sha AND p.page=fts.page
              WHERE fts MATCH ? {filt} ORDER BY bm25(fts, 0, 0, 1.0, 0.4) LIMIT ?"""
    rows, mode = [], "all terms"
    candidates = [(a.query, "fts5 syntax")] if a.raw else [(fts_query(a.query, "AND"), "all terms"), (fts_query(a.query, "OR"), "any term")]
    for match, mode in candidates:
        try:
            rows = con.execute(sql, [match, *args, a.limit * 6]).fetchall() if match else []
        except sqlite3.OperationalError as e:
            sys.exit(f"Bad search query: {e}")
        if rows:
            break
    seen, lines = set(), []
    for r in rows:
        key = (r["sha"], r["build_first"])  # one result per build: its stages stay individually addressable
        if key in seen:
            continue
        seen.add(key)
        ranged = r["build_first"] != r["build_last"]
        where = f"slide {r['page']}" + (f" (build {r['build_first']}-{r['build_last']})" if ranged else "")
        view = f" view:{r['flags']}" if r["flags"] else ""
        snip = " ".join(r["snip"].split()) if "«" in r["snip"] else "(matched only OCR of the slide image: view it before trusting)"
        lines.append(f"[{r['sha'][:8]}] {r['title']} | {where}{view}\n  {snip}")
        if len(seen) == a.limit:
            break
    emit("search", lines or [f"No slides match {a.query!r}. Image-only slides are searchable only if OCR ran; try other terms or `show`."])
    if lines and mode == "any term":
        print("(no slide had every term; matched any term)")


def parse_pages(spec, total):
    pages = set()
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", part)
        if not m:
            sys.exit(f"Bad page spec {part!r}; use e.g. 12 or 12,14-16")
        pages.update(range(int(m[1]), int(m[2] or m[1]) + 1))
    bad = sorted(p for p in pages if not 1 <= p <= total)
    if bad:
        sys.exit(f"Page(s) {bad} out of range; lecture has {total} pages.")
    return sorted(pages)


def source_state(m):
    src = Path(m["source"])
    if not src.exists():
        return "missing"
    st = src.stat()
    return "ok" if (st.st_size, st.st_mtime) == (m.get("size"), m.get("mtime")) or sha256(src) == m["sha256"] else "changed"


def rerender(m, d, page, out):
    """Regenerate a lost image, only from the exact PDF that was indexed."""
    if source_state(m) != "ok":
        return False
    out.parent.mkdir(exist_ok=True)
    render(pymupdf().open(m["source"])[page - 1], out)
    return True


def cmd_show(a):
    con = connect()
    lec = one_lecture(con, a.lecture)
    d = HOME / lec["sha"][:16]
    m = manifest(d)
    wanted = parse_pages(a.pages, lec["pages"])
    pages = sorted({p for w in wanted for p in range(max(1, w - a.context), min(lec["pages"], w + a.context) + 1)})
    state = source_state(m)
    lines = [f"# {lec['title']} ({lec['pages']} slides) [{lec['sha'][:8]}]"]
    if state != "ok":
        lines.append(f"WARNING: source PDF {state} ({m['source']}); serving cached copy of the indexed version.")
    prior, images = {}, 0
    for p in pages:
        r = con.execute("SELECT * FROM pages WHERE sha=? AND page=?", (lec["sha"], p)).fetchone()
        png = d / "pages" / f"p{p:04d}.png"
        have = png.exists() or rerender(m, d, p, png)
        images += have
        ranged = r["build_first"] != r["build_last"]
        lines.append(f"\n--- slide {p}" + (f" | build {r['build_first']}-{r['build_last']}" if ranged else "")
                     + (f" | VIEW IMAGE: {r['flags']}" if r["flags"] else "") + " ---")
        lines.append(f"image: {png}" if have else "image: UNAVAILABLE (source PDF gone); do not infer visual content")
        before = prior.get(r["build_first"])
        if before is not None:  # later stage of a build already on screen: print only what changed
            seen = set(before.splitlines())
            added = [l for l in r["text"].splitlines() if l not in seen]
            lines += [f"(text added since slide {p - 1}:)", *added] if added else [f"(text identical to slide {p - 1}; any change is visual, so view the image)"]
        else:
            lines.append(r["text"] or "(no extractable text; view the image)")
        prior[r["build_first"]] = r["text"]
    emit("show", lines, images)


def cmd_outline(a):
    con = connect()
    lec = one_lecture(con, a.lecture)
    lines = [f"# {lec['title']} ({lec['pages']} slides) [{lec['sha'][:8]}]"]
    for r in con.execute("SELECT * FROM pages WHERE sha=? AND page=build_first ORDER BY page", (lec["sha"],)):
        title = next((l.strip() for l in r["text"].splitlines() if re.search(r"[^\W\d_]{2}", l)), "(no text)")
        span = f"{r['build_first']}-{r['build_last']}" if r["build_first"] != r["build_last"] else str(r["page"])
        lines.append(f"{span}: {title[:70]}" + (f" [{r['flags']}]" if r["flags"] else ""))
    emit("outline", lines)


def cmd_crop(a):
    con = connect()
    lec = one_lecture(con, a.lecture)
    d = HOME / lec["sha"][:16]
    m = manifest(d)
    box = a.box
    if not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
        sys.exit("Box must be fractions of the slide: x0 y0 x1 y1, each 0..1, with x0<x1 and y0<y1.")
    parse_pages(str(a.page), lec["pages"])
    state = source_state(m)
    if state != "ok":
        sys.exit(f"Cannot crop: source PDF {state} ({m['source']}). Use the full slide image.")
    fz = pymupdf()
    page = fz.open(m["source"])[a.page - 1]
    w, h = page.rect.width, page.rect.height
    x0, y0 = page.rect.x0, page.rect.y0
    clip = fz.Rect(x0 + box[0] * w, y0 + box[1] * h, x0 + box[2] * w, y0 + box[3] * h)
    out = d / "crops" / f"p{a.page:04d}_{'_'.join(f'{b:.3f}' for b in box)}.png"
    out.parent.mkdir(exist_ok=True)
    render(page, out, clip)
    emit("crop", [f"image: {out}"], 1)


def cmd_status(a):
    con = connect()
    rows = con.execute("SELECT * FROM lectures ORDER BY source").fetchall()
    total = Counter()
    states = Counter()
    lines = []
    for r in rows:
        d = HOME / r["sha"][:16]
        m = manifest(d)
        t = m["timing_s"]
        state = source_state(m)
        states[state] += 1
        flagged = con.execute("SELECT count(*) FROM pages WHERE sha=? AND flags!=''", (r["sha"],)).fetchone()[0]
        total.update(pages=r["pages"], flagged=flagged, pdf=m["size"], cache=dir_size(d),
                     extract=t["extract"], render=t["render"], ocr=t["ocr"])
        if a.list:
            lines.append(f"[{r['sha'][:8]}] {r['title']} | {r['pages']} slides, {flagged} need viewing | "
                         f"{dir_size(d) / 1e6:.1f} MB | source {state}")
    mb = lambda b: f"{b / 1e6:.1f} MB"
    lines += [f"cache: {HOME}",
              f"lectures: {len(rows)}, slides: {total['pages']}, flagged for visual check: {total['flagged']}",
              f"sources: " + (", ".join(f"{v} {k}" for k, v in states.items()) or "none"),
              f"disk: PDFs {mb(total['pdf'])}, cache {mb(total['cache'])}",
              f"local preprocessing (no model tokens): extract {total['extract']:.1f}s, render {total['render']:.1f}s, ocr {total['ocr']:.1f}s"]
    if LOG.exists():
        use = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
        calls = Counter(u["cmd"] for u in use)
        chars = sum(u["chars"] for u in use)
        lines.append(f"retrieval: {dict(calls)}, {chars} chars of output (~{chars // 4} tokens, chars/4 estimate), "
                     f"{sum(u['image_paths'] for u in use)} image paths offered (upper bound; reads are not observable here)")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(prog="slides.py", description="Index lecture PDFs once; retrieve single slides cheaply.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index", help="index PDFs or directories; unchanged files are skipped")
    p.add_argument("paths", nargs="+"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_index)
    p = sub.add_parser("refresh", help="recheck every indexed source; optionally add paths")
    p.add_argument("paths", nargs="*"); p.add_argument("--force", action="store_true")
    p.add_argument("--prune", action="store_true", help="drop cache entries whose source PDF is gone"); p.set_defaults(fn=cmd_refresh)
    p = sub.add_parser("search", help="full-text search; returns slide refs and snippets")
    p.add_argument("query"); p.add_argument("-l", "--lecture", help="limit to lectures matching this title/path/hash")
    p.add_argument("-k", "--limit", type=int, default=6); p.add_argument("--raw", action="store_true", help="pass FTS5 syntax through"); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("show", help="print text and image paths for slides")
    p.add_argument("lecture"); p.add_argument("pages", help="e.g. 12 or 12,14-16")
    p.add_argument("-c", "--context", type=int, default=0, help="include N adjacent slides each side"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("outline", help="one line per slide or build, to navigate without loading text")
    p.add_argument("lecture"); p.set_defaults(fn=cmd_outline)
    p = sub.add_parser("crop", help="re-render a region from the PDF at higher zoom")
    p.add_argument("lecture"); p.add_argument("page", type=int)
    p.add_argument("box", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="fractions of the slide, 0..1"); p.set_defaults(fn=cmd_crop)
    p = sub.add_parser("status", help="cache contents, sizes, timings, retrieval volume")
    p.add_argument("--list", action="store_true", help="one line per lecture"); p.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
