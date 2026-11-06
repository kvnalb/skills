---
name: concept-graph
description: Turn course notes, lecture slides/PDFs, textbook chapters, papers or docs into an interactive concept graph (knowledge graph / concept map) - typed node shapes (primitive, definition, rule, result, interpretation, misconception), typed and labeled edges, one cluster per lecture or chapter, and click-to-open panels holding every substantive line and worked example from the source. Use this whenever someone wants to see how the ideas in a body of material connect - "map out these lectures", "make a mind map / mermaid graph of my notes", "visualize how these concepts relate", "help me hold a mental model of this course", "everything is derived from a few primitives, show me the links" - and whenever they ask to add new lectures or chapters to a concept graph built earlier, even if they don't say "graph". Not for codebase architecture diagrams, single algorithm flowcharts, or data charts.
compatibility: Requires Python 3. The generated page loads Mermaid from a CDN, so viewing it needs internet access. The optional render check needs headless Chrome.
---

# Concept graph

Build a single, self-contained HTML page that shows a body of material as a graph of concepts and the
relations between them. It is meant for someone who finds the source long and repetitive and wants to
see what each idea is and what it is built from.

The page is generated from a JSON data file by `scripts/build_graph.py`, which also validates the data
and checks that it renders. You write the data; the engine (`assets/template.html`, Mermaid with ELK
layout, loaded from a CDN) does layout, connectors, legend, and the click-to-focus detail panel.

## What makes these graphs good

These lessons came from building one with a real student, including the attempts that failed:

- **A graph, not a cheat sheet.** A first attempt crammed every line onto one dense printable page and
  was rejected as "way too dense, a cheatsheet and not a graph". Node labels stay short: a name plus at most one
  formula or defining line. Everything else (all the substantive lines, caveats, worked examples) goes
  in the node's `details` and `example`, which the reader opens by clicking. The graph shows structure; the panels hold the content.
- **Deduplicate across sources.** Material often previews a concept in one place and treats it fully
  later, or repeats it. Keep one node, put it in the cluster where it is treated most fully, and record
  every place it appears in `tags` (e.g. `L1·L4·L5`). That is how redundant material collapses.
- **Grounded in the source only.** Each statement in a node should trace back to the material. A
  one-line algebra step that connects two things the source states is fine. Outside facts are not. If a
  node comes from somewhere other than the main source (a problem set, say), say so in its tags (`PS4`).
- **No long wires.** Mermaid draws a cross-cluster edge as a wire through every cluster in between, and
  that turned the first version into spaghetti. The engine fixes this automatically: an edge between
  non-adjacent clusters becomes a small connector circle ("① X") inside the target cluster, and clicking
  it jumps to the source. Your job is to give every such source a short connector name in `sym`.
- **Edges read as propositions.** "Simple return —ln→ Log return", "No-arbitrage ⇒(else buy cheap, sell
  dear)⇒ LOOP". The label is the operation or reason, a few words at most.

## Workflow

### 1. Scope and sources

Find out which material is in scope and in what order the clusters should appear. The usual answer is
source order (lecture 1, 2, …), because readers follow the course that way. If a request is ambiguous
(for instance, some files clearly belong to a later unit), make a sensible call and mention it rather than stalling.

Extract the text, e.g. `pdftotext -layout file.pdf out.txt`. Formulas often come out garbled. When they
do, read the PDF pages as images to get the math right. Read **all** the material before writing any
nodes, because deduplication needs the whole picture.

### 2. Inventory concepts and classify them

List the concepts, then give each a node type. Shapes encode the types, and they follow flowchart
conventions where those apply:

| type | shape | use for | test |
|---|---|---|---|
| `prim` | hexagon | primitives / undefined building blocks | everything else is built from it; the source doesn't define it in terms of other things |
| `def` | rectangle | a constructed object or quantity | "X is defined as / computed by …" |
| `conv` | rounded rectangle | a measurement, notation or unit convention | changes how something is expressed, not what it is (log returns, quoting a price as a rate) |
| `rule` | parallelogram | an assumption, axiom, condition or imposed rule | the source *assumes* or *requires* it |
| `res` | stadium | a result or consequence | it follows from other nodes |
| `key` | stadium, thick border | a key result | reserve for the handful of results the rest hinges on (roughly one per cluster) |
| `interp` | flag | what something means, intuition, economic/plain reading | "this means / intuitively / think of it as" |
| `not` | red dashed rectangle | a misconception the source explicitly rules out | only when the source says "X is not Y". Great memory anchors, so collect them all |
| `beyond` | predefined-process box | a forward pointer to later material or another course | place it *inside* the cluster it hangs off, not in a separate cluster |

### 3. Write edges

Each edge is `[from, to, kind, label]`, and its direction follows the derivation: from what something is
built from, toward the consequence. Interpretation and "is NOT" edges point *from* the thing being interpreted
*to* the interpretation, so arrows keep flowing downward.

| kind | arrow | meaning | label |
|---|---|---|---|
| `b` | thin solid | builds / constructs | the operation: `÷ P`, `ln`, `Σ aᵢ`, `price with E[m·1]` |
| `i` | thick solid | implies (⇒) | optional reason: `set Y = 0`, `else buy cheap, sell dear` |
| `e` | thick two-headed | equivalent (⇔) | `same object`, `given π` |
| `m` | dashed | means / interprets / leads to | optional: `means`, `is not`, `formalized as` |
| `x` | red, cross | fails / does not hold | `✗ logs don't add across assets` |

Only add an edge you could justify from the source. One edge per ordered pair: merge the labels if two
relations hold.

### 4. Write the data file

Read `references/schema.md` for the exact JSON format. A small complete example (9 nodes, 2 clusters)
is in `references/example.json`. Skim it to calibrate label length, detail depth and edge style before writing
your own; a full course usually runs to about 100 nodes. Notes that save rework:

- Ids are letters and digits only (`RET`, `LOOP`, `ZP`). No underscores, because the engine parses
  `L_from_to_0` edge ids, and Mermaid keywords such as `end` aren't allowed. Cluster ids follow the same rules.
- Labels are Mermaid HTML strings: `<br/>` starts the second line; `<sub>`, `<sup>`, `<b>`, `<i>` are fine. Write
  a literal `<`/`>` in labels as `#lt;`/`#gt;`, and in details as `&lt;`/`&gt;`. No double quotes in labels.
- `details` is a list of bullets: one substantive statement each, in plain sentences. Put worked
  numbers in `example`.
- `start` fills the sidebar's "Start here" panel. Use it for the spine of the material: the chain of 5–8 ideas
  everything hangs on, plus one or two sentences that tie it together.

Save the data file **next to the HTML** (e.g. `course_graph.json` beside `course_graph.html`). The JSON is
the source of truth. Later additions edit the JSON and rebuild, and if the HTML is ever lost, it can be regenerated.

### 5. Build, check, look

```bash
python scripts/build_graph.py course_graph.json course_graph.html --screenshot /tmp/graph.png
```

The script refuses to build on errors (bad ids, unknown nodes, duplicate edges, raw `<`, nodes in two
clusters) and prints warnings for weak spots: orphan nodes, missing connector names, very long labels,
oversized clusters. Fix the errors, and fix the warnings unless there is a reason not to. `--screenshot` confirms the
page renders (it needs internet for the Mermaid CDN) and saves an image of the whole graph.

**Look at the screenshot**; crop it into tiles if it is tall. Things to fix:
- **Wires running a long way, or nodes stranded far from their neighbours:** move a node to the cluster it
  connects to most, or check whether an edge points the wrong way.
- **An arrow pointing upward inside a cluster:** usually an interpretation edge written backwards.
- **A cluster far wider than the others:** too many siblings hang off one node. Split the cluster, or chain
  some of the siblings.
- **A node whose label wraps to 3+ lines:** shorten it and move the text to `details`.

### 6. Deliver

Give the path to the HTML and the JSON, and explain briefly how to use it:
- click a node for its panel
- neighbours stay lit
- connector circles jump to their source
- zoom is bottom-left
- it needs internet for the CDN

Mention any judgment calls you made about scope, cluster order or placement.

## Adding material later

When the reader brings new lectures or chapters, append clusters, nodes and edges to the existing JSON,
link the new nodes back to the earlier concepts they build on (these cross-links are the point), extend
`start` if the spine grows, and rebuild. Don't hand-edit the generated HTML. If only the HTML survives,
recover the data from the `const G = {...}` literal inside it.
