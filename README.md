```

  ╔═══════════════════════════════════╗
  ║           e n g r a m             ║
  ║   persistent memory for agents    ║
  ╚═══════════════════════════════════╝

```

# engram

[![PyPI](https://img.shields.io/pypi/v/engram-wiki)](https://pypi.org/project/engram-wiki/)
[![Python](https://img.shields.io/pypi/pyversions/engram-wiki)](https://pypi.org/project/engram-wiki/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/emipanelliok/engram/actions/workflows/ci.yml/badge.svg)](https://github.com/emipanelliok/engram/actions)

**Persistent memory for AI agents. They learn once, remember forever.**

> Not RAG. Not embeddings. A real wiki — built and maintained by your AI agent.

---

## The problem

Every time your AI agent starts a new session, it forgets everything.
Every time the context window compacts, knowledge disappears.
Every insight, every lesson, every decision — **gone.**

You've seen it: the agent re-discovers the same things, asks the same questions,
makes the same mistakes. Session after session.

**Engram gives your agent a brain that persists.**

## Who is this for?

If you use **Claude Code**, **Cursor**, **Codex**, **Aider**, **Hermes**, **OpenClaw**, or any coding agent and you're frustrated that it loses context between sessions — engram is for you.

If you're building **multi-agent systems** and need agents to share knowledge — engram is for you.

If you read [Karpathy's LLM Wiki concept](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and thought "I want that" — engram is exactly that.

## How it works

```bash
# Session 1: Agent discovers something
engram save "The prod database is on port 5432, staging on 5433"

# Session 2: Agent ingests documentation
engram ingest https://docs.example.com/api-reference

# Session 3: Agent starts fresh, but remembers everything
engram query "what port is staging on?"
# → "The staging database is on port 5433. (see: database-config)"
```

Your agent writes knowledge to a **wiki of plain markdown files**. The wiki grows with every session. Cross-references are created automatically. Old entries get compressed so it never explodes.

## Why not RAG?

|  | Traditional RAG | engram |
|---|---|---|
| Agent sees | Raw document chunks | A synthesized, coherent wiki |
| Knowledge | Lost between sessions | Persists and grows forever |
| Cross-references | Don't exist | Created automatically by the LLM |
| Contradictions | Hidden across chunks | Detected and flagged by `lint` |
| Search | Vector similarity (needs DB) | Simple keyword match on markdown |
| Your data | Locked in a vector database | Plain `.md` files you can read, edit, grep |
| Infrastructure | Embeddings + vector DB + retrieval pipeline | Zero. Just files. |
| Cost | Embeddings on every query | LLM call only on write |

## Quick start

```bash
# Install
pip install engram-wiki

# Initialize — pick your LLM provider
engram init --provider claude    # Needs ANTHROPIC_API_KEY
engram init --provider openai    # Needs OPENAI_API_KEY
engram init --provider ollama    # Free, local, private — needs Ollama running
```

### Core commands

```bash
# Save knowledge (agent memory)
engram save "deploy requires approval in staging first"

# Ingest external sources (URLs, PDFs, files)
engram ingest https://arxiv.org/abs/2401.12345
engram ingest ./meeting-notes.pdf

# Ask questions — answered from the wiki
engram query "what's the deploy process?"

# Health check — find contradictions, stale info, orphans
engram lint

# Compress old entries — automatic, but can be triggered manually
engram compress

# See what the agent knows
engram status
engram topics

# Export the entire wiki
engram export --format markdown
engram export --format json --output wiki.json

# Delete knowledge intentionally
engram forget some-article-slug
```

### Agent-friendly output

Every command supports `--json` for machine-readable output:

```bash
engram --json save "the API rate limit is 100 req/min"
# → {"status": "saved", "article": {"slug": "api-limits", "title": "API Limits"}, "summary": "Created article."}

engram --json query "what's the rate limit?"
# → {"question": "...", "answer": "The API rate limit is 100 req/min. (see: api-limits)"}
```

### Pipe support

```bash
cat meeting-notes.md | engram ingest
git log --oneline -20 | engram save
curl -s https://api.example.com/docs | engram ingest
```

## Use with AI agents

### Claude Code

Add to your project's `CLAUDE.md`:

```markdown
## Memory

Before starting work, check what you already know:
`engram query "summary of this project"`

When you learn something important, save it:
`engram save "description of what you learned"`

When you find useful documentation, ingest it:
`engram ingest <url>`
```

### Cursor / .cursorrules

```
When you discover something important about this codebase, run:
engram save "what you discovered"

Before starting a complex task, check existing knowledge:
engram --json query "relevant topic"
```

### Any agent (Hermes, OpenClaw, Codex, custom scripts)

```bash
# Before starting a task — load context
context=$(engram --json query "what do I know about $TASK")

# After completing a task — save learnings
engram save "Completed $TASK. Key findings: ..."

# Ingest relevant docs
engram ingest $DOC_URL
```

## Per-project wikis

Like `.git`, engram supports local wikis per project:

```bash
cd my-project
engram init --local              # Creates .engram/ in current directory
engram save "this project uses FastAPI + SQLAlchemy"

cd ../other-project
engram init --local --provider ollama
engram save "this project uses Next.js + Prisma"
```

Each project gets its own isolated knowledge base. If no local `.engram/` exists, engram falls back to the global `~/.engram`.

## Architecture

```
~/.engram/                       # (or .engram/ per project)
├── sources/raw/                 # Original ingested content (immutable)
│   ├── 0001_api-docs.md
│   └── 0002_meeting-notes.md
├── wiki/                        # Synthesized articles with cross-references
│   ├── index.md                 # Auto-generated topic index
│   ├── database-config.md
│   └── api-reference.md
├── log.md                       # Append-only chronological log
└── engram.toml                  # Configuration (no secrets)
```

### Automatic compression

Engram auto-compresses when the wiki exceeds configurable thresholds (article count or total size). Articles are grouped by their primary tag and merged into a single summary per topic, using the LLM to preserve key facts while reducing volume.

A backup is always created before compression. Thresholds are configurable in `engram.toml`.

## Providers

| Provider | Cost | Privacy | Speed | Setup |
|---|---|---|---|---|
| **Claude** | ~$0.003/save | Cloud | Fast | `ANTHROPIC_API_KEY` |
| **OpenAI** | ~$0.002/save | Cloud | Fast | `OPENAI_API_KEY` |
| **Ollama** | Free | 100% local | Depends on hardware | [Install Ollama](https://ollama.ai) |

## How is this different from...

| Tool | What it does | How engram differs |
|---|---|---|
| **mem0** | Embeddings + vector DB memory | engram uses a real wiki, not vectors. You can read and edit the files. |
| **MemGPT / Letta** | Full agent framework with memory | engram is a simple CLI tool, not a framework. Works with any agent. |
| **Obsidian / Notion** | Human knowledge management | engram is CLI-first, built for agents, auto-maintained. |
| **RAG pipelines** | Retrieve raw document chunks | engram synthesizes and cross-references. The wiki is the product. |
| **CLAUDE.md / .cursorrules** | Static instruction files | engram is dynamic — it grows with every session. |

## Security

- **No secrets on disk** — API keys come from environment variables only, never stored in config
- **SSRF protection** — Internal/private network URLs are blocked
- **Path traversal prevention** — All file writes are validated against the wiki directory
- **LLM output validation** — Responses are validated with strict Pydantic schemas before acting on them
- **Local-first** — Your knowledge base lives on your filesystem. With Ollama, data never leaves your machine.

## Roadmap

- [ ] **MCP Server** — Expose engram as a Model Context Protocol server (Claude Desktop, Cursor, Cline)
- [ ] **`engram diff`** — Show what changed since last session
- [ ] **`engram watch`** — Auto-ingest new files in a directory
- [ ] **Token cost tracking** — Track cumulative API spend
- [ ] **Plugin system** — Custom source parsers (Notion, Confluence, Slack)
- [ ] **`engram sync`** — Sync wikis between machines via git
- [ ] **Embeddings-enhanced search** — Optional, for large wikis (100+ articles)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git clone https://github.com/emipanelliok/engram.git
cd engram
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

---

*Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and Vannevar Bush's [Memex](https://en.wikipedia.org/wiki/Memex) (1945). The name "engram" comes from neuroscience — a hypothetical unit of memory stored in the brain.*
