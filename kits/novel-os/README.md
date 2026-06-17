# Novel-OS Kit for Hermes Agent

Install, restore, and integrate **Novel-OS** — a production-grade multi-agent fiction writing framework — with a dedicated **novelist** Hermes profile containing full skill support, SOUL personality, agent pipeline awareness, and private isolated writing environment.

> **Who this is for:** Hermes Agent users who want to write novels using an AI-powered multi-agent editorial pipeline.
> **What you get:** Novel-OS CLI + Web UI, 5 specialized AI agents (Architect → Scribe → Editor → Guardian → Approve), persistent StoryState, deterministic continuity engine, 13+ LLM provider support, and a fully configured novelist Hermes profile.
> **Time to install:** ~15 minutes

## Prerequisites

- Hermes Agent (profile management enabled)
- macOS (other OS works but paths may differ)
- Git
- Python 3.8+ (CLI) or Python 3.10+ (Web UI)
- At least one LLM API key or provider
- Node.js + npm (Web UI, optional)
- ~500MB disk space (repo + venv + deps)

## What's in this kit

```
kits/novel-os/
├── kit.md                      # This workflow
├── README.md                   # This page
└── src/
    ├── SKILL.md                # Novel-OS integration skill (296 lines)
    ├── SOUL.md                 # Novelist profile personality (warm editor)
    ├── AGENTS.md               # Profile rules + 5-agent pipeline reference
    └── references/
        ├── command-reference.md     # CLI command reference
        ├── api-endpoints.md         # REST API endpoint reference
        └── opencode-zen-config.md   # OpenCode Zen provider config
```

## Quick Start

```bash
# 1. Clone Novel-OS
git clone https://github.com/mrigankad/Novel-OS.git ~/novel-os

# 2. Create venv and install deps
cd ~/novel-os
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure LLM provider
cp .env.example .env
# Edit .env with your API key and provider

# 4. Test the CLI
python core/orchestrator.py --help

# 5. Install profile artifacts
cp src/SKILL.md ~/.hermes/profiles/novelist/skills/novel-os/SKILL.md
cp src/SOUL.md ~/.hermes/profiles/novelist/SOUL.md
cp src/AGENTS.md ~/.hermes/profiles/novelist/AGENTS.md

# 6. Write!
hermes -p novelist
```

## Key Features

- **5 specialized AI agents** — Architect (plans), Scribe (drafts), Editor (refines), Guardian (validates), Approve (gates)
- **Persistent StoryState** — characters, plot threads, events, foreshadowing tracked across chapters
- **Deterministic continuity engine** — 9 free checks run before the LLM Guardian (dormant threads, unresolved foreshadowing, timeline drift, etc.)
- **13+ LLM providers** — Anthropic, OpenAI, Gemini, Groq, OpenRouter, DeepSeek, Ollama, LM Studio, OpenCode Zen, and any OpenAI-compatible endpoint
- **Web UI** — React 19 + FastAPI dashboard with project management, chapter pipeline, comments, and snapshots
- **Natural language control** — the Hermes agent acts as the front-end, translating user requests to CLI commands

## The 5-Agent Pipeline

```
🏗️ Architect  →  ✍️ Scribe  →  🔍 Editor  →  🛡️ Guardian  →  ✅ Approve
  (plan)         (write)        (edit)        (validate)       (gate)
```

Each agent hands off to the next with full context from the persistent StoryState.

## Restore

To restore Novel-OS and the novelist profile after a data loss or migration:

1. Re-clone Novel-OS (`git clone https://github.com/mrigankad/Novel-OS.git ~/novel-os`)
2. Recreate the venv and install dependencies
3. Reconfigure `.env` with your LLM provider
4. Copy the src/ artifacts to the novelist profile directory
5. Verify with the validation checklist in `kit.md`

## Related Kits

- `kits/hermes-profiles/` — Hermes profile management kit
- `kits/security-hardening/` — Security suite (recommended for any profile)
