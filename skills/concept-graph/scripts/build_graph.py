#!/usr/bin/env python3
"""Validate a concept-graph data file and build the interactive HTML page.

Usage:
  python build_graph.py graph.json out.html            # validate + build
  python build_graph.py graph.json out.html --check    # + confirm it renders in headless Chrome
  python build_graph.py graph.json out.html --check --screenshot shot.png [--width 2600]

Exit code 1 on validation errors (nothing is written) or a failed render check.
"""
import argparse, html, json, os, re, shutil, subprocess, sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
TYPES = {"prim", "def", "conv", "rule", "res", "key", "interp", "not", "beyond"}
KINDS = {"b", "i", "e", "m", "x"}
RESERVED = {"end", "graph", "subgraph", "flowchart", "style", "classdef", "class", "click", "linkstyle", "direction", "default", "call", "href"}
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
# Tags the graph labels and panels are allowed to contain; anything else with < or > breaks Mermaid or the panel HTML.
ALLOWED_TAGS = re.compile(r"</?(br|sub|sup|b|i|em|strong|code|span)(\s[^<>]*)?/?>", re.I)


def validate(g):
    errs, warns = [], []
    nodes, edges, clusters, sym = g.get("nodes", {}), g.get("edges", []), g.get("clusters", []), g.get("sym", {})
    if not g.get("title"): errs.append("missing 'title'")
    if not clusters: errs.append("no clusters")

    def check_id(i, what):
        if not ID_RE.match(i): errs.append(f"{what} id '{i}': letters/digits only, starting with a letter (no _ - or spaces)")
        elif i.lower() in RESERVED: errs.append(f"{what} id '{i}' is a Mermaid keyword; rename it")

    def check_text(s, where, mermaid):
        if not isinstance(s, str): errs.append(f"{where}: expected a string"); return
        stripped = ALLOWED_TAGS.sub("", s)
        if "<" in stripped or ">" in stripped:
            fix = "#lt; / #gt;" if mermaid else "&lt; / &gt;"
            errs.append(f"{where}: raw '<' or '>' (write {fix}): {s[:70]}")
        if mermaid and '"' in s: errs.append(f'{where}: double quote breaks Mermaid; use “ ” or \' : {s[:70]}')
        if mermaid and "`" in s: errs.append(f"{where}: backtick breaks Mermaid labels")

    for n_id, n in nodes.items():
        check_id(n_id, "node")
        if n.get("type") not in TYPES: errs.append(f"node {n_id}: type '{n.get('type')}' not in {sorted(TYPES)}")
        check_text(n.get("label", ""), f"node {n_id} label", True)
        if not n.get("label"): errs.append(f"node {n_id}: empty label")
        for k, d in enumerate(n.get("details", [])): check_text(d, f"node {n_id} details[{k}]", False)
        if n.get("example"): check_text(n["example"], f"node {n_id} example", False)
        for k, pair in enumerate(n.get("symbols", [])):
            if not (isinstance(pair, list) and len(pair) == 2): errs.append(f"node {n_id} symbols[{k}]: must be [symbol, meaning]")
            else:
                for x in pair: check_text(x, f"node {n_id} symbols[{k}]", False)
        if not n.get("details"): warns.append(f"node {n_id}: no details (the click panel will be empty)")

    cluster_of, seen_c = {}, set()
    for k, c in enumerate(clusters):
        check_id(c.get("id", ""), "cluster")
        if c.get("id") in seen_c: errs.append(f"duplicate cluster id {c.get('id')}")
        if c.get("id") in nodes: errs.append(f"cluster id {c.get('id')} collides with a node id")
        seen_c.add(c.get("id"))
        check_text(c.get("title", ""), f"cluster {c.get('id')} title", True)
        for n_id in c.get("nodes", []):
            if n_id not in nodes: errs.append(f"cluster {c['id']} lists unknown node {n_id}")
            elif n_id in cluster_of: errs.append(f"node {n_id} is in two clusters ({clusters[cluster_of[n_id]]['id']}, {c['id']})")
            else: cluster_of[n_id] = k
        if len(c.get("nodes", [])) > 25: warns.append(f"cluster {c['id']} has {len(c['nodes'])} nodes; consider splitting it")
    for n_id in nodes:
        if n_id not in cluster_of: errs.append(f"node {n_id} is not in any cluster")

    pairs, degree = set(), {n: 0 for n in nodes}
    for k, e in enumerate(edges):
        if not (isinstance(e, list) and len(e) in (3, 4)): errs.append(f"edge {k}: expected [from, to, kind, label?]"); continue
        a, b, kind = e[0], e[1], e[2]
        label = e[3] if len(e) == 4 else ""
        for end in (a, b):
            if end not in nodes: errs.append(f"edge {k} {a}->{b}: unknown node {end}")
        if kind not in KINDS: errs.append(f"edge {a}->{b}: kind '{kind}' not in {sorted(KINDS)}")
        if (a, b) in pairs: errs.append(f"duplicate edge {a}->{b} (merge the labels; duplicates break highlighting)")
        if a == b: errs.append(f"self-loop on {a}")
        pairs.add((a, b))
        if label: check_text(label, f"edge {a}->{b} label", True)
        if "|" in label: errs.append(f"edge {a}->{b} label: '|' breaks Mermaid edge syntax")
        if len(ALLOWED_TAGS.sub("", label)) > 45: warns.append(f"edge {a}->{b}: long label ({label[:40]}…); keep labels to a short phrase")
        if a in degree: degree[a] += 1
        if b in degree: degree[b] += 1
        if a in cluster_of and b in cluster_of and abs(cluster_of[a] - cluster_of[b]) > 1 and a not in sym:
            warns.append(f"node {a} feeds a non-adjacent cluster; add sym['{a}'] for a short connector label")
        if a in cluster_of and b in cluster_of and f"{a}to{clusters[cluster_of[b]]['id']}" in nodes:
            errs.append(f"generated connector id {a}to{clusters[cluster_of[b]]['id']} collides with a node id")
    for n_id, d in degree.items():
        if d == 0: warns.append(f"node {n_id} has no edges (orphan)")
    for s_id in sym:
        if s_id not in nodes: warns.append(f"sym entry {s_id} is not a node")
    return list(dict.fromkeys(errs)), list(dict.fromkeys(warns))


def find_chrome():
    for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]:
        if os.path.exists(c): return c
    for c in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]:
        if shutil.which(c): return shutil.which(c)
    return None


def check_render(out, screenshot=None, width=2600):
    chrome = find_chrome()
    if not chrome:
        print("render check skipped: no Chrome/Chromium found"); return True
    url = Path(out).resolve().as_uri()
    base = [chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=20000"]
    dom = subprocess.run(base + ["--window-size=1400,900", "--dump-dom", url], capture_output=True, text=True, timeout=120).stdout
    err = re.search(r'id="err">([^<]*)<', dom)
    m = re.search(r'<svg id="(g[12])"[^>]*viewBox="([^"]+)"', dom)
    if err and err.group(1).strip():
        print("RENDER ERROR:", html.unescape(err.group(1).strip())); return False
    if not m:
        print("RENDER ERROR: no graph SVG produced (offline? Mermaid loads from cdn.jsdelivr.net)"); return False
    w, h = (float(v) for v in m.group(2).split()[2:])
    print(f"rendered with {'ELK' if m.group(1) == 'g1' else 'dagre (ELK unavailable)'} layout; canvas {w:.0f}×{h:.0f}px")
    if screenshot:
        # Size the window so the whole graph is visible at ~100% zoom next to the 380px sidebar.
        win_w = max(width, int(w) + 480)
        subprocess.run(base + [f"--window-size={win_w},{int(h) + 150}", f"--screenshot={Path(screenshot).resolve()}", url],
                       capture_output=True, timeout=180)
        print("screenshot:", screenshot)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--check", action="store_true", help="confirm the page renders in headless Chrome")
    ap.add_argument("--screenshot", help="also save a full-graph screenshot (implies --check)")
    ap.add_argument("--width", type=int, default=2600)
    a = ap.parse_args()

    g = json.loads(Path(a.data).read_text(encoding="utf-8"))
    errs, warns = validate(g)
    for w in warns: print("warning:", w)
    if errs:
        for e in errs: print("ERROR:", e)
        print(f"{len(errs)} error(s); nothing written."); sys.exit(1)

    data = json.dumps(g, ensure_ascii=False).replace("</", "<\\/")  # keep '</script>' inside strings from closing the tag
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__TITLE__", html.escape(re.sub(r"<[^>]+>", "", g["title"]))).replace("/*__GRAPH_DATA__*/null", data)
    Path(a.out).write_text(page, encoding="utf-8")
    print(f"built {a.out}: {len(g['nodes'])} nodes, {len(g['edges'])} edges, {len(g['clusters'])} clusters")
    if (a.check or a.screenshot) and not check_render(a.out, a.screenshot, a.width): sys.exit(1)


if __name__ == "__main__":
    main()
