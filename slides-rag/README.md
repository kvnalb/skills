# slides-rag

Index lecture PDFs once, then answer questions from single slides. An [Agent Skill](https://agentskills.io) for any compatible agent: ask about your lectures and it loads itself. Originals are never modified.

Install: `npx skills add kvnalb/skills --skill slides-rag`

```text
SKILL.md              instructions the agent follows
scripts/slides.py     CLI (Python stdlib + PyMuPDF)
scripts/test_slides.py  end-to-end check on a generated fixture
~/.local/share/slides-rag/   cache (override with SLIDES_RAG_HOME)
```

Requires Python 3.9+ with FTS5 in sqlite3. PyMuPDF comes from your environment, or `uv` fetches it automatically. Tesseract is optional, and only adds search coverage for image-heavy slides.

## Usage

In your agent, just ask: "index ~/Courses/Data101/Slides", "explain the theta join formula", "quiz me on lecture 3".

Directly:

```bash
alias slides='python3 /path/to/slides-rag/scripts/slides.py'
```

```bash
slides index ~/Courses/Data101/Slides
```

```bash
slides search "theta join" -l "relational" -k 5
```

```bash
slides outline 204de1cd
```

```bash
slides show 204de1cd 34,36-37 -c 1
```

```bash
slides crop 204de1cd 34 0.1 0.2 0.9 0.6
```

```bash
slides status --list
```

```bash
slides refresh --prune
```

## How it stays faithful

- Each page keeps its text, its image, and flags saying why the text may be incomplete: `image`, `diagram`, `math`, `low_text`, `garbled`, `annotated`. Thresholds are constants at the top of `slides.py`.
- Equations embedded as images leave blanks in extraction (`Inputs:` with nothing after it). The `image` flag catches these; on the Data 101 decks 57% of slides are flagged, by design.
- Glyphs with no Unicode mapping become a visible `⟦?⟧`. In these decks, the Inter font loses `( ) [ ] : |` this way.
- Progressive slides are grouped as `build 12-15`, never dropped. `show` prints added text only, and says when a stage differs only visually.
- OCR is search-only, stored apart from slide text, and never shown as content.

Cache entries are keyed by SHA-256, so renames and moves reuse everything, and the SQLite index rebuilds itself from `pages.jsonl` if lost. Entries with a missing source stay usable until `refresh --prune`. Lost images re-render from the indexed PDF. A broken entry is rebuilt on the next `index`.

## Measured results

Data 101 corpus (49 PDFs, 1,511 pages, 41 MB). Local cost, no model tokens: 88 s for a first index (extract 26 s, render 49 s, OCR 13 s), 0.4 s for a no-op re-index, 222 MB of cache.

Model cost, from real API usage in headless Claude Code runs (Sonnet, one run per cell, so treat as indicative). "Added context" is the final context size minus the session's starting size. The direct arm had the skill and shell tools disabled.

| Question | Added context: PDF | Added context: skill | Bill: PDF | Bill: skill |
|---|---:|---:|---:|---:|
| Formal definition of theta join (64 slides; direct read stopped at 40) | 31.2k | 5.7k | $0.100 | $0.065 |
| Recursive CTEs (29 slides, topic absent) | 22.8k | 8.3k | $0.119 | $0.078 |
| Summarize lecture (29 slides) | 22.8k | 6.9k | $0.082 | $0.066 |

Answers were equivalent on the theta join and the summary. On recursive CTEs, the skill also found the topic in two review decks the single-PDF read could not see.

What the table does not say:

- Bill savings (20 to 35%) are smaller than context savings (64 to 82%), because the skill takes more turns (5 to 7 against 3) and each turn re-reads the cached context. Total tokens processed were actually higher with the skill.
- The context saving compounds: PDF pages stay in context for every later turn. A direct read also needs no further retrieval for follow-ups on the same deck.
- Reading a PDF directly costs about 780 tokens per page, apparently at lower resolution. A cached 1568 px slide costs about 1,900. If you need images for more than roughly 40% of a deck, a direct read is cheaper, though less sharp.
- PNG file size has no effect on tokens; pixel dimensions do.
- `status` reports retrieval volume as a chars/4 estimate and cannot see which images were read.

## Test

```bash
python3 /path/to/slides-rag/scripts/test_slides.py
```

## Limits

- Search is keyword-only (with stemming). If a slide says "equi join" and you ask for "matching on equal keys", rephrase. Add embeddings only if that proves a real problem.
- Text inside images is unsearchable below 25% image coverage, unless the slide is nearly textless.
- Build detection uses word containment, so builds that swap content stay ungrouped. Nothing is lost; they just rank as separate hits.
- Flags are heuristics tuned on Google Slides exports. Beamer and PowerPoint decks may need different thresholds.
- Slide numbers are PDF page numbers.
- Token figures above were measured on Claude Code only. Other agents read PDFs and images differently, so their costs will differ.
