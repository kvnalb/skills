---
name: slides-rag
description: Answer questions from university lecture PDFs without reloading whole decks. Indexes each PDF once into a persistent full-text and slide-image cache, then retrieves only the relevant slides, with lecture and slide citations. Use when the user asks to study, explain, summarize, review, or quiz on lecture slides or course PDFs, or asks what a lecture or slide says, even if they don't name a file. Examples include "explain slide 12", "what did lecture 3 say about joins", "quiz me on normalization", "summarize this lecture", "review the slides for the midterm", and "index these slides".
compatibility: Requires shell access and Python 3.9+ with SQLite FTS5, plus PyMuPDF or uv. Works best with an agent that can view local PNG files. Tesseract is optional.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/slides.py *)
---

# slides-rag

Retrieve lecture content through the cache. Never open a lecture PDF directly, and never load a whole `lecture.md`.

```bash
python3 scripts/slides.py <command>
```

| Command | Use |
|---|---|
| `status [--list]` | What is indexed; hashes, sizes, timings, retrieval volume |
| `index <pdf or dir>... [--force]` | Index once; unchanged files are skipped, so it is always safe to run |
| `refresh [paths] [--prune]` | Recheck all sources, reindex changed ones, note missing ones |
| `search "terms" [-l lecture] [-k N]` | Find slides; returns refs, flags, snippets |
| `outline <lecture>` | One line per slide; the map for summaries, quizzes and image-only decks |
| `show <lecture> 12,14-16 [-c 1]` | Slide text and image paths; `-c 1` adds neighbours |
| `crop <lecture> <page> x0 y0 x1 y1` | Re-render a region from the PDF (fractions 0..1) for tiny notation |

`scripts/slides.py` is relative to this skill's directory; resolve it to an absolute path before running it. Run one command per shell call, because chained commands often need extra permission approval.

`<lecture>` is the 8-character ref from output (preferred), or words from the title or path. `-l` also accepts a course or folder name.

## Answering a question

1. If the user names PDFs or a folder, run `index` on them first. Otherwise go straight to `search`; run `status --list` only if search finds nothing relevant.
2. `search` with 2 to 4 distinctive terms, adding `-l` when the user names a lecture. If output says it matched any term, or the hits look wrong, retry with one or two words and `-l`; slides use the course's own vocabulary. Formula slides have little text, so check the flagged hits and `outline` before reading unflagged slides.
3. `show` only the slides you need. Use `-c 1` when a slide continues an argument.
4. Decide whether to look at the image:
   - **Open the image file** when `show` prints `VIEW IMAGE` and the answer touches that content, or when the question concerns an equation, diagram, table, layout, annotation, or anything visual.
   - **Skip it** when plain text answers the question and the slide is unflagged. Each image costs about 1,900 tokens; text is usually under 100.
   - If the first image leaves notation unclear, use `crop` on that region.
   - If you cannot view local images, answer from the text and state which flagged content you could not check.
5. Answer with citations: `(Relational Model & Algebra, slide 14)`. Slide numbers are PDF page numbers; if the printed number differs, say so.

For summaries and quizzes, start with `outline`, then `show` only slides that carry substance. Skip agenda and repeated outline slides. Don't dump a deck into context.

## Fidelity rules

- Extracted text is a search aid, not the source. The slide image and the original PDF are authoritative.
- Flags name why text may be incomplete: `image` (embedded image, often an equation with no text behind it), `diagram` (table, arrows, shapes), `math`, `low_text`, `garbled`, `annotated`.
- `⟦?⟧` marks a glyph with no Unicode mapping. Never fill one in from context in a quoted formula or code; view the image.
- Never reconstruct a formula from extracted text alone. If you cannot read a symbol even in a crop, say so.
- OCR is used only for search, for image-heavy slides. A hit saying it matched OCR must be confirmed on the image.
- A `build 12-15` range is one slide revealed in stages. Keep the stages distinct: when asked about a diagram's progression, view each stage. `show` prints only added text for later stages, and says when a change is visual only.

## When something is unavailable

- `source PDF missing`: the cached text and images are still valid; answer from them and mention it.
- `source PDF changed`: run `refresh`, then retry.
- Lost images re-render automatically when the indexed PDF exists; `image: UNAVAILABLE` means answer from text and state that the visual could not be checked.
- A moved or renamed PDF needs only `index <new path>`; the hash matches, so nothing is reprocessed.

## Measuring savings

`status` reports local costs and retrieval volume. It estimates text tokens as chars/4 and cannot see which images were read. Don't quote a savings figure from it. Measured numbers are in [README.md](README.md).
