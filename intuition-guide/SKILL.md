---
name: intuition-guide
description: |
  Build intuition-first study guides that read start-to-finish without friction.
  Produces a linear chain where nothing is used before it is built, every claim is
  justified by the domain's native unit (derivation / trace / case / argument), and
  redundant concepts are collapsed rather than listed. Works for course material,
  problem sets, papers, unfamiliar technical domains, and job-listing vocabulary gaps.
  Use when asked to "make a study guide", "explain this domain", "help me learn X",
  "I need to understand the vocabulary of Y", "prep me for this role/exam/paper",
  or when the user says reference sheets and summaries aren't making things stick.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - WebSearch
  - WebFetch
---

# Intuition Guide

Produce documents that build understanding rather than index it.

## The one thing to internalise before writing anything

> **Compression is the goal of reference material and the enemy of learning.**

A formula sheet, cheat sheet, or summary is a *retrieval index for structure the reader
already has.* It cannot create that structure, because the connective tissue is the first
thing compression deletes. If the user says "I read the notes and it isn't sticking," they
have been handed reference material for a job that needs a textbook.

**Default to the chain. Produce the compressed artifact last, if at all, as a separate file.**

---

## Step 0 · Classify the domain — this fixes everything downstream

Do this before writing a single line. It determines the **unit of justification** (the
"atom"), the **output shape**, and whether a dependency chain is even legitimate.

| Domain type | Generative structure | The atom | Output shape |
|---|---|---|---|
| Deductive (math, stats, theory CS, logic) | dependency DAG | **derivation** | linear chain |
| Algorithmic / systems (data structures, complexity) | invariants + cost models | **prove the invariant, derive the cost** | linear chain |
| Language / execution (interpreters, PL, semantics) | evaluation models | **trace execution** | linear chain |
| Empirical / applied ML / data science | assumptions + estimators + craft | **derive the estimator; then a worked case + its failure mode** | chain + case gallery |
| Engineering practice (infra, ops) | constraints + tradeoffs | **the failure that motivated the design** | decision map |
| Humanities / social science | argument + contestation | **reconstruct premises → warrant → conclusion, then the strongest objection** | **contestation map, NOT a chain** |
| Vocabulary / orientation in a new field | terminology + open problems | **the problem each term was invented to solve** | glossary-chain + frontier map |
| Pure memorisation (dates, vocab, citations) | none | — | **refuse; recommend spaced repetition** |

**Two hard rules from this table:**

1. **Contested domains must not be forced into a chain.** A linear chain asserts a settled
   structure. In political theory, historiography, or any live debate, that manufactures false
   coherence — which is worse than being unhelpful, because it reads as authoritative. Use a
   contestation map: position → strongest evidence → strongest objection → what would falsify it.
2. **If no dependency structure exists, say so and recommend a different artifact.** A method
   that knows its boundary beats one that always emits something.

---

## Step 1 · Ground in the assessed artifact, never the syllabus

Read what the reader will actually be *judged by or need to produce*:

```
course       problem sets · past exams · the instructor's own scope posts · rubrics
paper        the claims and the experiments, not the abstract
role/job     the listing's priority areas · the papers that org publishes · the proposal format
domain       the benchmark tasks · what practitioners argue about
```

A syllabus lists topics. An assessment reveals *what is actually load-bearing.* Where the two
disagree, the assessment wins. Quote the source's own words when defining scope — an
instructor's "you should be able to fill each cell in yourself" is worth more than any
inference.

**If graded work or past errors are available, use them.** Map each error to a concept and
weight that concept for extra depth and earlier position.

## Step 2 · Build the concept graph

Nodes are exactly two kinds:
```
WHAT IS <x>    a definition, object, or fact
HOW TO <y>     a procedure or move
```
Edges are prerequisites. Root the graph **below the reader's stated floor** — ask what they
already know and start exactly one step under it, not at absolute zero (patronising) and not
at the target (useless).

## Step 3 · Find the collapses ★

**Highest-value step. Skipping it is what makes guides feel like lists.**

Scan for pairs or clusters that are *the same idea in different clothes*, then say so
explicitly in the text.

```
Chebyshev IS Markov applied to the squared deviation
The LLN IS Chebyshev applied to the sample average
closures, objects, and dispatch dictionaries ARE the same construct
all balanced trees ARE one rebalancing idea
```

Most of the apparent *volume* of a subject is redundancy nobody has named. A guide that turns
seven results into two ideas plus consequences is doing the actual work. State each collapse
as a sentence the reader can quote back.

## Step 4 · Linearise — this is an optimisation, not a topological sort

A DAG has many valid orders and they are **not** equally smooth. Choose the order minimising
friction:

```
minimise   Σ distance(where introduced, first use)     ← introduce JUST BEFORE needed
         + variance(new concepts per section)          ← even step size
         + altitude jumps between neighbours           ← constant rigour level
         + dispersion of related nodes                 ← keep clusters adjacent
subject to every prerequisite preceding its dependents  (HARD)
```

The first term matters most and is the least obvious: **introduce a concept as late as
possible while still preceding its first use.** Introducing it early forces the reader to hold
it in working memory with no idea why — a friction event even though no rule was broken.

## Step 5 · Write each node to a fixed shape

```
1  MOTIVATE BY FAILURE   show the question it answers, or watch a simpler idea fail first
2  DERIVE                using the domain's atom. Never "it can be shown."
3  CONCRETE              small numbers / a tiny trace / the canonical case, immediately after
4  TRAP                  the specific way readers get this wrong, named as a warning
```

Step 1 is the one people skip and it carries the most weight. Do not define variance — try
`E[X−μ]` (always zero, useless), try MAD (works, algebraically awful), *then* the definition
arrives as an answer to a question the reader already feels.

**Also required in the prose:**
- **Signpost weight.** Say "this is the most important fact here." Textbooks flatten everything
  to equal emphasis and readers then cannot tell what is load-bearing.
- **Answer "why this definition and not another"** at least once per major concept. That is what
  converts a formula into a concept.
- **Pay every promise.** If §2 says "we will need this," some later section must use it and
  say so. Unresolved promises are friction.

---

## Smoothness is the objective function, not a QA step

The property that makes these documents work is that the reader can **stop monitoring** — no
attention spent on "am I missing something, should I look this up, will this be explained."

**It is a negative property: the absence of friction events.** Each of these is a defect:

```
✗  a term used before it is defined
✗  a step that does not visibly follow
✗  "it can be shown that…"
✗  a forward reference ("as we'll see in §9")
✗  a gap requiring an outside lookup
✗  ambiguity about whether something matters
✗  an optional branch — now the reader must DECIDE, which costs momentum
```

**And it is multiplicative, not additive.** 95% smooth is not 95% as good: one forward
reference teaches the reader that the contract can break, and they resume defensive reading
for the remainder. Near-miss is qualitatively different from hit, so this must be *verified*,
not hoped for.

### Verify before delivering

```
forward_references         MUST be 0                    hard fail
undefined_term_uses        MUST be 0    (against the doc + declared prereqs)
unresolved_promises        MUST be 0
unsourced_novelty_claims   MUST be 0                    hard fail — frontier gate
literature_searched_first  MUST be true (unfamiliar-domain mode)
new_concepts_per_section   low mean, LOW VARIANCE
altitude_delta             bounded between neighbours
section_shape_conformance  high
coverage                   every assessed skill → ≥1 section
```

Cheap check that catches most of it: **walk your own section boundaries and ask "could a reader
with only the stated prereqs plus everything above continue here without looking anything up?"**
Any no is a friction event with a location. Fix it by moving a node earlier or adding one.

---

## Output artifacts

Produce in this order. Never produce a later one without the earlier.

```
1  THE CHAIN        the main document. Linear, complete, self-contained.
                    Problem set ≈ 12 nodes · lecture ≈ 40 · course ≈ 150 (with sub-files)

2  QUESTION BANK    (assessment contexts only) types × 2 VERBATIM questions from the
                    real source, each mapped to the section covering it.
                    Never paraphrase a question — the wording is the data.

3  RE-IGNITION      one entry per big idea, ~120 words, storing GENERATORS not outputs:
                       Question it answers · Generator · The collapse · The move ·
                       The surprise · Regenerate everything from
                    Formulas belong on a reference sheet; this stores the machinery that
                    produces them. Written LAST, derived from the chain.

4  REFERENCE SHEET  compressed lookup. Optional. Only after the chain exists.
                    Ideally the reader writes this themselves — deciding what earns a slot
                    IS the final compression, and it proves they have the structure.
```

## Formatting

- **Plain-text math by default** (`E[X]`, `sigma/sqrt(n)`, `Sum_x`). LaTeX fails to render in
  many clients and a formula the reader can't see is worse than an ugly one. Use LaTeX only
  when the output is confirmed to be a rendered PDF.
- Fenced code blocks for every formula, derivation, and procedure. Prose for the why.
- Tables for comparisons and trap lists.
- ⚠️ for traps, ★ for load-bearing ideas. Used sparingly enough to mean something.
- End with **"the whole thing in one chain"** — the dependency spine on a few lines — plus the
  two or three sentences from which most of the document regenerates.

---

## Mode: unfamiliar or adjacent domain (job listings, papers, new fields)

Here the goal is **not** passing a test. It is **producing credible output** — a proposal, a
conversation, a review. That changes the deliverable:

```
0  SURVEY  ★★      SEARCH THE LITERATURE FIRST, BEFORE GENERATING ANY IDEA.
                   Not to validate a candidate you already like — to build the map you
                   generate FROM. Reversing this order is the worst failure this skill
                   has, because reasoning-from-structure produces ideas that feel novel
                   to someone who hasn't read the field, which is exactly the wrong test.
1  DECODE          the vocabulary, each term introduced by THE PROBLEM IT WAS INVENTED TO SOLVE.
                   A term whose motivating failure you can state is a term you can use.
2  COLLAPSE        which of these are the same idea renamed? (fields accrete synonyms fast,
                   and this is where an outsider's leverage is highest)
3  FRONTIER        what is actually open, contested, or unsolved. Take it from the
                   literature's OWN statements — future-work sections, survey conclusions,
                   explicit "we do not address" caveats — never from armchair inference.
                   You cannot propose research into a settled question.
4  BRIDGE          map the reader's existing expertise onto this domain explicitly. State
                   where their background is a real edge and where it is a liability.
5  ANATOMY         what good output looks like here: structure, length, conventions,
                   what reviewers reward and punish.
```

### The frontier gate — enforce, don't merely intend

```
PRIOR    assume any idea reachable by armchair reasoning HAS been done, most likely in
         an adjacent domain under different vocabulary. Search until you find it or have
         genuinely failed to. "I couldn't think of prior work" is not evidence.

GATE     every claim of the form "X is open / unsolved / nobody has done X" MUST carry
         a citation, or an explicit "unverified — search before relying on this."
         Hard fail. Not a style preference.

SEARCH ADJACENT DOMAINS BY NAME, not just the target one. The same method is routinely
mature in one field and unknown in its neighbour. Minimum sweep:
         quant finance · econometrics · biostatistics · operations research ·
         robotics & control · recsys & ads · epidemiology

THEN CLASSIFY the surviving gap — different barriers, very different implications:
         crowded           strong researchers already there → outsider edge ≈ zero
         politically hard  no prior work because nobody WANTS the finding → often the
                           real opening for someone with no internal turf to protect
         data-gated        impossible outside one org → good fellowship fit
         genuinely open    rare. Demand citations proving it.

A PORT from an adjacent domain is a contribution ONLY IF the target domain breaks the
method. State exactly what breaks. "Same method, new dataset" is a benchmark, not
research — say that plainly instead of dressing it as novelty.
```

**Be honest about difficulty asymmetry.** Some of an unfamiliar field genuinely is "simple
ideas plus scale"; some is genuinely conceptually hard. Say which is which. Flattering the
reader that everything is easy produces confident nonsense in the proposal.

**Never fabricate the frontier.** If you don't know what's currently open in a field, search
for it. Inventing plausible-sounding open problems is the worst possible failure here, because
it is invisible to the reader and fatal in front of an expert.

---

## Anti-patterns

```
✗  a list of topics with definitions              → it's a glossary; find the chain
✗  "it can be shown that…"                        → derive it or cut it
✗  equal emphasis on everything                    → signpost the load-bearing ideas
✗  forward references                              → reorder
✗  compressing before explaining                   → the reference sheet comes LAST
✗  starting at absolute zero                       → start one step below the stated floor
✗  forcing a contested field into a chain          → contestation map
✗  paraphrasing real exam/interview questions      → verbatim; the wording is the data
✗  guessing scope from a syllabus                  → read the assessment
✗  inventing open problems in an unfamiliar field  → search, or say you don't know
```

## Before delivering, ask yourself

1. Could a reader with only the stated prereqs read this top to bottom without stopping?
2. Did I name at least one collapse?
3. Did I motivate each major definition by a failure, rather than asserting it?
4. Is every formula derived?
5. Did I say what matters most?
6. Are the traps named as traps?
7. Is the compressed artifact separate from, and after, the chain?
