# Graph data schema

One JSON file. `scripts/build_graph.py` validates it and injects it into `assets/template.html`.

```json
{
  "title": "Course so far as a concept graph",
  "subtitle": "Click any node for everything the notes say about it. Its neighbours stay lit.",
  "start": {
    "heading": "The spine",
    "items": ["<b>Time → States → Payoffs → Prices → … → SDF</b>", "One sentence tying it together."]
  },
  "legend": { "interp": "what a result means economically" },
  "tagNote": "Tags such as “L1·L4” show every lecture that repeats a concept; the graph keeps it once.",
  "clusters": [
    { "id": "CORE", "title": "Core objects — primitives (L1)", "nodes": ["T", "X", "P"], "color": "#3b5ea8" }
  ],
  "nodes": {
    "X": {
      "type": "prim",
      "label": "Asset ≡ payoff vector<br/>X = (X<sub>1</sub>, …, X<sub>S</sub>)",
      "tags": "L1·L4",
      "details": ["A contract that trades at t and pays at a future date, contingent on the state.",
                  "Defined by payoffs, not by type."],
      "example": "A short position flips every sign: (−2, 5, 10) becomes (2, −5, −10)."
    }
  },
  "edges": [["T", "X", "b", "pays at t+1"], ["X", "P", "b", "P(·) maps payoff → price"]],
  "sym": { "X": "X" }
}
```

## Fields

| field | required | notes |
|---|---|---|
| `title` | yes | sidebar heading and page `<title>` (tags stripped) |
| `subtitle` | no | the line under the title; there is a sensible default |
| `start` | no | "Start here" panel shown before any click: `heading` (small caption) plus `items` (HTML bullets) |
| `legend` | no | override legend descriptions by key: node types `prim def conv rule res interp not beyond conn`, edge kinds `b i e m x` |
| `tagNote` | no | sentence appended to the cluster list explaining the tags |
| `clusters` | yes | in display order (top → bottom). The engine numbers them ①②…, so don't put numbers in `title`. `color` (hex stroke) is optional; a palette is used otherwise |
| `nodes` | yes | map id → node; every node belongs to exactly one cluster |
| `edges` | no | `[from, to, kind, label?]`, at most one per ordered pair |
| `sym` | no | short connector names for nodes that feed a non-adjacent cluster, e.g. `"RFX": "X<sub>s</sub>=1"`. Without one, the first label line is used, which is often too long |

### Node

| key | notes |
|---|---|
| `type` | one of `prim def conv rule res key interp not beyond` (see the table in SKILL.md) |
| `label` | Mermaid HTML. First line = name (also used in panel links); later lines = formula/definition, shown at the top of the panel |
| `tags` | free text, usually the sources the concept appears in: `L1·L4`, `FI III`, `PS4` |
| `details` | list of HTML strings, one bullet each: every substantive line the source says about the concept |
| `example` | optional HTML string: worked numbers from the source |

## Text rules (the validator enforces these)

- Ids (node and cluster): `^[A-Za-z][A-Za-z0-9]*$`, not a Mermaid keyword (`end`, `graph`, `style`, `class`, `click`, …).
  The engine also creates connector ids of the form `<source>to<clusterId>`, which must not collide with your ids.
- Allowed tags everywhere: `br sub sup b i em strong code span`.
- In `label`, cluster `title` and edge labels: no `"` or backtick; write `<`/`>` as `#lt;`/`#gt;`; no `|` in edge labels.
- In `details`/`example`: write `<`/`>` as `&lt;`/`&gt;`; `&amp;` for `&`.
