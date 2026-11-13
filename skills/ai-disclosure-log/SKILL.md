---
name: ai-disclosure-log
description: "Create a two-part AI-use disclosure for any context: a nested-bullet Disclosure Summary followed by a tabular Disclosure Log (Prompt Log). Document prompts, contributions, revisions, and human decisions in matching Markdown and PDF files within a session-specific subdirectory."
---

# AI prompt log and disclosure summary

Produce a self-contained record a recipient can use to understand how AI helped with the work, what changed, and who made the decisions. These guidelines apply to professional, academic, creative, research, coding, and personal work. No course materials or external reference reading are needed.

Use progressive disclosure: a reader should understand the collaboration from the Disclosure Summary alone, while the Disclosure Log preserves each interaction for inspection or handoff. Follow an explicitly supplied disclosure policy or format, but do not assume institutional requirements.

## Session folder

- Use the user's chosen project directory, otherwise the current working directory. Store both files at `ai-disclosure/<session-id>/log.md` and `log.pdf`.
- Use `CODEX_THREAD_ID` if available. Otherwise reuse the folder already identified in this chat; if none exists, create a timestamp plus short task slug and remember that path in the conversation. Treat the identifier as a single safe filename component, never a path. Distinct chats need distinct folders, even for the same task.
- Record creation and update times with the user's timezone and UTC offset. Check the same-session metadata sources below before calling a field unavailable; distinguish uninspected, inaccessible, and absent fields. Do not infer historical values from current config or file modification times.
- Read any existing log before updating. Preserve earlier interactions and recorded decisions, append new numbered interactions, and update the summary. Regenerating a snapshot must not duplicate interactions. If history has been compacted, retain the stored record and mark any remaining gaps.

## Recorded model and timing metadata

Prefer structured metadata supplied by the current session or an explicit user export. For local Codex sessions, use the bundled standard-library helper:

```bash
python3 <skill-directory>/scripts/session_metadata.py --session-id <current-session-id>
```

It finds only that session's JSONL under `$CODEX_HOME/sessions` or `archived_sessions` (default `~/.codex`), verifies the recorded session ID, and returns only allowlisted session/turn metadata. Do not dump raw logs or read other conversations. These internal files are version-dependent; if absent, ambiguous, or unsupported, report that specific limit and use a supplied export instead. No OTel collector is needed when the local metadata is readable.

- Record each turn's reported `model`, `effort`, and timestamp; preserve changes across turns. Call these the recorded model identifier, reported reasoning-effort setting, and turn-record timestamp. They do not prove a backend checkpoint, routing, or actual computation used. Never substitute the default in config.toml for historical per-turn evidence.
- If message times matter, match an already-visible prompt exactly within same-session user message records and retain that record's timestamp. Ignore environment updates and other automatic messages. Label this a recorded message timestamp, not a verified send/receive time. Do not assign turns by list position unless their correspondence is checked.
- Put provenance and any field-specific limitations in the Disclosure Log. Export only necessary fields to a metadata sidecar if useful. Do not expose system/developer instructions, private reasoning, or unrelated payloads while extracting metadata.
- Before reporting a check as passed, run it and describe what it actually checks. Distinguish automated checks from visual inspection. Omit routine disclaimers about human comprehension not being measured; include only limitations material to the task. Correct earlier unsupported claims explicitly rather than silently overwriting history.

## Two-part log.md

Start with a short, task-specific title, then these two sections in order. Do not put session metadata or an audit table before the Disclosure Summary.

### Disclosure Summary

Use the exact heading `## Disclosure Summary`. Write a concise executive memo as a visibly nested bullet outline, aiming for 150-250 words and one PDF page. These are guides, not compression targets: allow more space when the meaning needs it. Use these five bold top-level labels in this order, with substantive child bullets and a third level only where useful:

- Task
- Prompt characteristics
- Revisions
- Human decisions
- Resulting work product

Under Task, explain the goal. Under Prompt characteristics, describe the question, context/evidence, purpose, role, voice, and constraints that mattered. Under Revisions, explain consequential before/after changes and who requested them. Under Human decisions, record the choices and feedback actually observed. Under Resulting work product, identify the concrete outputs and relevant AI contributions. If a field has no substantive content, say so briefly rather than inventing it.

Use two spaces per Markdown nesting level. The PDF should show clearly deeper indentation and distinct filled-circle, hollow-circle, and square markers. Keep related bullets compact, with a little more space between top-level groups. Do not attach a paragraph to a top-level label and call it a nested list.

Keep the five standard labels; omit routine operational detail within them. Avoid chronological narration, repeated disclaimers, internal IDs, long paths, verbatim prompts, and wide tables. Put qualifications beside the claim they affect. Name the actual work and result; avoid generic process prose such as "a persistent work object." Record actual human feedback, decisions, and verification when relevant. Omit routine statements that a newly generated document has not been reviewed or approved; do not add review-status fields or a review checkpoint unless the user explicitly requests a review workflow.

Write for comprehension, not minimum word count. Bullets organize information; they do not make compressed prose clear.

- Say who did what with familiar verbs. Prefer "You chose which sources to use" to "Human source selection authority."
- Unpack strings of nouns and invented labels into explicit relationships. Prefer "checks that the log preserves earlier decisions" to "decision-history preservation checks."
- Keep subjects close to their verbs and modifiers close to what they describe. Split sentences with nested clauses or several qualifications.
- Keep useful connecting words such as "that," "because," and "so." State the relationship instead of relying on slashes, fragments, or omitted words for the reader to reconstruct it.
- Use conventional words and technical terms the reader knows. Explain unfamiliar terms before relying on them. Avoid novel verbs made from nouns and figurative actions by abstract things when a literal account is clearer; familiar expressions need no blanket ban.
- Give each bullet one main point. Read the memo once as its recipient: if understanding requires unpacking a phrase or rereading a sentence, rewrite it even if the result is longer. The Disclosure Log can contain more detail, but should still use clear prose.

### Disclosure Log (Prompt Log)

Use the exact heading `## Disclosure Log`. Start this section on a new PDF page. Include a chronological table with exactly these column headings:

`Context Provided | Prompt | AI Output | Revision | Decision`

Each row represents one substantive user prompt and its AI response. Include follow-up requests, corrections, and rejected approaches. Do not make a separate row for each tool call. Summarize long prompts and responses clearly in the table, identifying summaries as such and linking them to numbered details below; do not present a paraphrase as an exact quotation. Record who requested a revision and distinguish human decisions from AI implementation choices. Do not invent choices or add automatic approval/review-status disclaimers.

After the table, retain necessary session metadata (identifier, dates/timezone, recorded tool/model, and coverage). Add numbered interaction details containing exact visible prompts, response summaries, evidence, and consequential changes when needed for fidelity or agent handoff. Preserve earlier interaction evidence when restructuring a log, but avoid duplicating the whole table in prose. Put artifacts, checks, and material continuation details at the end.

Markdown supports headings, nested `-` bullets, bold, fenced text, and simple pipe tables. Keep table cells brief and escape literal pipes as `\|`.

Describe relevant prompt characteristics: the question/task, supplied evidence or context, purpose, desired voice, role, and constraints. When prompts evolve, explain how clarification, added evidence, or human feedback changed the result. Distinguish AI exploration, drafting, organization, or critique from human selection and judgment. Do not require a particular prompting method or claim supplied material was independently verified when it was only read.

Use only visible conversation, user-provided exports, relevant project artifacts, and the narrowly filtered same-session metadata described above. Exclude system/developer instructions, private reasoning, credentials, and unrelated personal or confidential information. Mark sensitive prompt material as `[redacted: reason]` rather than silently changing a purported quotation. Keep the disclosure suitable for sharing; reference sensitive source material by a safe description when its contents or private path are unnecessary. Do not search other chats or private application databases for a fuller transcript. A reconstructed log must state its coverage limits.

## PDF export and verification

Write/update `log.md` first; it is the source of truth. Use the bundled exporter to make `log.pdf` from that exact file:

```bash
python3 <skill-directory>/scripts/export_pdf.py <session-directory>/log.md
```

The exporter needs ReportLab. Use the available bundled document/PDF Python runtime when system Python lacks it; discover that runtime with `load_workspace_dependencies` when available. Do not promise PDF completion if the dependency or conversion fails. Keep the Markdown and report the specific failure.

Use portrait pages with a readable text width, visible nested-bullet indentation, and bold lead-ins. Start Disclosure Log on a new page so Disclosure Summary can be read or shared on its own. Check both parts and the full interaction history survived export. Render and visually inspect the PDF for memo length, hierarchy, wrapping, and page breaks. Cut repetition before cutting explanatory words; allow a longer memo when needed rather than shrinking the type or obscuring meaning to force one page. Correct defects before returning links to both files and the session directory.

When more work occurs in this chat while the skill remains active, update the same record at substantive completion points and regenerate the PDF. This is a snapshot maintained during execution, not a background recorder; other chats require invoking/selecting the skill there. Do not submit, publish, or send the disclosure unless the user requests it.
