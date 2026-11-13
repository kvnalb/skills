# Skills

Reusable skills for learning, studying, and documenting AI use, in the open [Agent Skills](https://agentskills.io) format. They work with Claude Code, Codex, Cursor and other compatible agents. Each skill is a folder with a `SKILL.md` and any scripts it needs.

| Skill | What it does | Needs |
|---|---|---|
| [AI Disclosure Log](ai-disclosure-log/SKILL.md) | Creates a nested-bullet disclosure summary and interaction log, saved as Markdown and PDF. | Python 3, ReportLab; pypdf for export tests |
| [Concept Graph](concept-graph/SKILL.md) | Turns notes, slides, chapters or papers into an interactive concept map, with typed nodes and click-to-open detail panels. | Python 3, a browser with internet access |
| [Intuition Guide](intuition-guide/SKILL.md) | Builds study guides that read start to finish, showing why each idea matters and how it leads to the next. | Nothing |
| [Slides RAG](slides-rag/README.md) | Indexes lecture PDFs once, then answers from only the relevant slides, with citations. Keeps the slide images for equations and diagrams. | Shell access, Python 3.9+, PyMuPDF or `uv` |

## Install

Install with the [Skills CLI](https://github.com/vercel-labs/skills), replacing the name with the skill you want:

```sh
npx skills add kvnalb/skills --skill slides-rag
```

The installer asks which agent to target and whether to install for the current project or globally. To skip the prompts, name your agent and install globally. For example, with Codex:

```sh
npx skills add kvnalb/skills --skill slides-rag -g -a codex -y
```

To see what's available first:

```sh
npx skills add kvnalb/skills --list
```

## Use

Skills load on their own when a request matches, so you can just ask: "make me a study guide for dynamic programming", "map out how these lectures connect" or "explain the theta join formula from lecture 3".
