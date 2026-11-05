# Skills

Reusable agent skills for learning and studying. Each skill is a folder with a `SKILL.md` and any scripts it needs.

| Skill | What it does | Needs |
|---|---|---|
| [Intuition Guide](intuition-guide/SKILL.md) | Builds study guides that read start to finish, showing why each idea matters and how it leads to the next. | Nothing |
| [Slides RAG](slides-rag/README.md) | Indexes lecture PDFs once, then answers from only the relevant slides, with citations. Keeps the slide images for equations and diagrams. | Claude Code, Python 3.9+, PyMuPDF or `uv` |

## Install

Install with the [Skills CLI](https://github.com/vercel-labs/skills), replacing the name with the skill you want:

```sh
npx skills add kvnalb/skills --skill slides-rag
```

The installer asks which agent to target and whether to install for the current project or globally. To skip the prompts and install globally for Claude Code:

```sh
npx skills add kvnalb/skills --skill slides-rag -g -a claude-code -y
```

To see what's available first:

```sh
npx skills add kvnalb/skills --list
```

## Use

Skills load on their own when a request matches, so you can just ask: "make me a study guide for dynamic programming" or "explain the theta join formula from lecture 3". In Claude Code you can also call one by name, such as `/slides-rag`.
