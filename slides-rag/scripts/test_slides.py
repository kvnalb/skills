#!/usr/bin/env python3
"""End-to-end check on a generated fixture. Run: python3 test_slides.py"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import pymupdf

SCRIPT = Path(__file__).with_name("slides.py")
root = Path(tempfile.mkdtemp()).resolve()
env = {**os.environ, "SLIDES_RAG_HOME": str(root / "cache")}


def run(*args, ok=True):
    r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env)
    assert (r.returncode == 0) == ok, (args, r.stdout, r.stderr)
    return r.stdout + r.stderr


def fixture(path):
    doc = pymupdf.open()
    p = doc.new_page(width=720, height=405)
    p.insert_text((40, 60), "Gradient descent update rule for the loss function", fontsize=20)
    p.insert_text((40, 120), "q = q - h L(q)", fontsize=24, fontname="symb")  # Symbol font: theta, eta
    p = doc.new_page(width=720, height=405)
    p.insert_text((40, 60), "Pipeline architecture diagram overview", fontsize=20)
    for x in (60, 260, 460):
        p.draw_rect(pymupdf.Rect(x, 150, x + 140, 230))
        p.draw_line((x + 140, 190), (x + 200, 190))
    p = doc.new_page(width=720, height=405)  # image-only slide
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 225), 0)
    pix.set_rect(pix.irect, (200, 220, 255))
    p.insert_image(p.rect, pixmap=pix)
    for stage in range(1, 4):  # progressive reveal: same words, more each time
        p = doc.new_page(width=720, height=405)
        for i in range(stage):
            p.insert_text((40, 60 + 40 * i), f"Reveal stage {i + 1} of the worked example here", fontsize=18)
    p = doc.new_page(width=720, height=405)  # same text as previous, only the picture changes
    for i in range(3):
        p.insert_text((40, 60 + 40 * i), f"Reveal stage {i + 1} of the worked example here", fontsize=18)
    p.draw_circle((500, 300), 60)
    doc.save(path)


pdfs = root / "lectures"
pdfs.mkdir()
pdf = pdfs / "Lecture 01 - Fixture.pdf"
fixture(pdf)
before = hashlib.sha256(pdf.read_bytes()).hexdigest()

assert "1 indexed" in run("index", pdfs)
entry = next((root / "cache").glob("*/manifest.json"))
m = json.loads(entry.read_text())
assert m["sha256"] == before and m["pages"] == 7 and m["source"] == str(pdf)
assert (entry.parent / "pages" / "p0007.png").stat().st_size
assert "<!-- page 3 -->" in (entry.parent / "lecture.md").read_text()
stamp = entry.stat().st_mtime_ns
assert "1 unchanged" in run("index", pdfs) and entry.stat().st_mtime_ns == stamp, "reindexed unchanged file"

out = run("search", "gradient descent")
assert "slide 1" in out and "Lecture 01 - Fixture" in out and "view:" in out and "math" in out, out
assert "(no slide had every term" in run("search", "gradient zebra")
assert "No slides match" in run("search", "zebra")
run("search", 'unbalanced " AND ( query')  # free text must never reach FTS as syntax

out = run("show", "fixture", "2")
assert "VIEW IMAGE: " in out and "diagram" in out and "p0002.png" in out
out = run("show", "fixture", "3")
assert "low_text" in out and "no extractable text" in out and "image:" in out
out = run("show", "fixture", "1", "-c", "1")
assert "slide 1" in out and "slide 2" in out and "slide 3" not in out

out = run("show", "fixture", "4-7")
assert "build 4-7" in out and "text added since slide 4" in out, out
assert "any change is visual" in out and all(f"--- slide {p}" in out for p in (4, 5, 6, 7)), "build stage dropped"
assert run("search", "reveal stage").count("build 4-7") == 1  # one hit per build
assert "4-7:" in run("outline", "fixture")

assert "image:" in run("crop", "fixture", "1", 0, 0, 0.5, 0.5)
run("crop", "fixture", "1", 0.5, 0, 0.2, 1, ok=False)
run("show", "fixture", "99", ok=False)

# Self-healing: lost index, lost image, truncated artifact.
(root / "cache" / "index.sqlite").unlink()
assert "slide 1" in run("search", "gradient")
(root / "cache" / "index.sqlite").write_bytes(b"not a database")
assert "slide 1" in run("search", "gradient")
png = entry.parent / "pages" / "p0002.png"
png.unlink()
assert str(png) in run("show", "fixture", "2") and png.exists()
(entry.parent / "pages" / "p0003.png").write_bytes(b"")
assert "1 indexed" in run("index", pdf), "invalid cache entry was not rebuilt"

# Moved file: reuse by hash, no reprocessing.
stamp = (entry.parent / "lecture.md").stat().st_mtime_ns
moved = pdfs / "renamed.pdf"
pdf.rename(moved)
assert "source missing" in run("refresh") and "WARNING" in run("show", "fixture", "1")
assert "moved" in run("index", moved)
assert (entry.parent / "lecture.md").stat().st_mtime_ns == stamp and "renamed" in run("search", "gradient")

# Changed file at the same path replaces its old entry.
doc = pymupdf.open(moved)
doc.new_page().insert_text((40, 60), "Appendix on stochastic momentum")
doc.save(root / "x.pdf")
shutil.move(root / "x.pdf", moved)
assert "reindexed" in run("refresh")
assert len(list((root / "cache").glob("*/manifest.json"))) == 1 and "slide 8" in run("search", "momentum")

# Bad inputs and a vanished source.
(pdfs / "broken.pdf").write_bytes(b"%PDF-nonsense")
assert "FAILED" in run("index", pdfs, ok=False)
(pdfs / "broken.pdf").unlink()
moved.unlink()
out = run("show", "renamed", "1")
assert "WARNING" in out and "Gradient" in out
assert "retrieval:" in run("status") and "source missing" not in run("status")
assert "pruned" in run("refresh", "--prune") and "lectures: 0" in run("status")

shutil.rmtree(root)
print("all checks passed")
