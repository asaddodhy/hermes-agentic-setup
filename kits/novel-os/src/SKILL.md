---
name: novel-os
description: "Multi-Agent Fiction Writing Framework integration for the novelist Hermes profile"
version: 1.0.0
author: Novel OS (mrigankad) + Hermes integration
platforms: [macos, linux]
metadata:
  hermes:
    tags: [writing, novel, fiction, multi-agent]
---

# Novel-OS Integration for Hermes Novelist Profile

This skill teaches Hermes how to use **Novel-OS** — a multi-agent fiction writing framework with 5 specialized AI agents (Architect, Scribe, Editor, Guardian, Curator), a persistent StoryState, and a deterministic continuity engine.

**The agent IS the front-end.** The user talks to you in natural language; you execute Novel-OS CLI commands behind the scenes. They never need to know flags, file paths, or syntax. Map their requests using the Natural Language Front-End Pattern section below.

## Setup

Novel-OS is installed at `/Users/dodhya/novel-os/` with its own venv at `/Users/dodhya/novel-os/.venv/`.

**Alias:** Use the shell function below or run all commands via the venv Python:

```bash
novel-os() {
    cd /Users/dodhya/novel-os && source .venv/bin/activate && python core/orchestrator.py "$@"
}
```

## Writing Pipeline (per-chapter workflow)

### 1. INIT — Project setup
```
novel-os init --title "Novel Title" --genre "Genre"
```

### 2. CAST — Define characters
```
novel-os character add --name "Character Name" --role protagonist
novel-os character add --name "Antagonist Name" --role antagonist
novel-os plot add --name "Plot Thread" --description "Description"
```

### 3. PLAN — Outline
```
novel-os plan outline --chapters 32 --words 80000
novel-os plan chapter --number 1 --pov "Character Name"
```

### 4. WRITE — Scribe drafts
```
novel-os write --chapter 1
```
The Scribe agent writes prose and outputs a `[SCRIBE_STATE_UPDATE]` block that is parsed and merged into `StoryState`.

### 5. EDIT — Editor refines
```
novel-os edit --chapter 1 --mode line
```
Modes: `line`, `developmental`, `pacing`, `dialogue`, `tension`

### 6. VALIDATE — Continuity check + Guardian
```
novel-os check --chapter 1     # FREE deterministic checks (no LLM call)
novel-os validate --chapter 1  # LLM Guardian validates continuity
```

### 7. APPROVE — Gate check
```
novel-os approve --chapter 1
```
**Blocks** if Guardian reported `FAIL`. Must resolve issues and re-validate.

### 8. EXPORT — Compile manuscript
```
novel-os export --format markdown
```

## Project structure

Each project lives under `outputs/`:
```
outputs/
├── story_state.json          # Central persistent state (StoryState)
├── manuscript/
│   ├── chapter_001_draft.md
│   ├── chapter_001_revised.md
│   └── ...
├── outline.json
├── feedback/
│   └── chapter_001_continuity_report.md
└── prompts_and_responses/
```

## The 5 Agents

| Agent | Command | Role | Output Contract |
|-------|---------|------|-----------------|
| 🏗️ Architect | `plan chapter` | Story planner — 3-act structure, beats | Freeform outline |
| ✍️ Scribe | `write` | Prose drafter — deep POV | `[SCRIBE_STATE_UPDATE]` — chars, events, foreshadowing |
| 🔍 Editor | `edit` | Line surgeon — 5 modes | `[EDITOR_STATE_UPDATE]` — quality scores |
| 🛡️ Guardian | `validate` | Continuity fact-checker | `[CONTINUITY_REPORT]` + `[CONTINUITY_STATE_UPDATE]` |
| 🎨 Curator | (not wired) | Voice stylist | `[STYLE_STATE_UPDATE]` — scores + drift |

## Continuity Engine (free, deterministic)

Runs **before** the LLM Guardian. 9 checks:
- Dormant threads (>3 chapters idle)
- Overdue threads (past target resolution)
- Unresolved foreshadowing
- Absent characters (>5 chapters)
- Dead character re-appearing
- File consistency mismatches

```
novel-os check                  # Full project
novel-os check --chapter 12     # As-of specific chapter
```

## LLM Provider Setup

**You must configure a provider before write/edit/validate will work.** Without it, those commands error out because they need an LLM.

### Interactive wizard
```
novel-os setup
```
Auto-detects available providers (Claude Code CLI, any API keys in env, running local servers) and offers a numbered menu. Tests the connection before saving.

### Direct `.env` configuration
Create `/Users/dodhya/novel-os/.env` with these variables:

| Variable | Required for | Example |
|----------|-------------|---------|
| `NOVEL_OS_LLM_PROVIDER` | All | `openrouter`, `deepseek`, `anthropic`, `openai` |
| `NOVEL_OS_MODEL` | Most providers | `anthropic/claude-sonnet-4`, `deepseek-chat` |
| `NOVEL_OS_API_KEY` | openai_compatible + aliases | `sk-...` |
| `NOVEL_OS_BASE_URL` | openai_compatible only | `https://openrouter.ai/api/v1` |

### Supported providers and their env vars

| Provider | `NOVEL_OS_LLM_PROVIDER` value | Key env var | Notes |
|----------|-------------------------------|-------------|-------|
| Claude Code CLI | `claude_cli` | (none — uses subscription) | Free if subscribed; auto-detected |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | Default model: `claude-sonnet-4-6` |
| OpenAI | `openai` | `OPENAI_API_KEY` | Default model: `gpt-4o` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Default: `gemini-2.0-flash` |
| Azure OpenAI | `azure` | `AZURE_OPENAI_API_KEY` + endpoint | Also needs `AZURE_OPENAI_ENDPOINT` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | Preset base URL included |
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` | Default: `deepseek-chat` |
| Groq | `groq` | `GROQ_API_KEY` | Default: `llama-3.3-70b-versatile` |
| Together | `together` | `TOGETHER_API_KEY` | |
| Mistral | `mistral` | `MISTRAL_API_KEY` | |
| Fireworks | `fireworks` | `FIREWORKS_API_KEY` | |
| Kimi / Moonshot | `kimi` / `moonshot` | `KIMI_API_KEY` / `MOONSHOT_API_KEY` | |
| Ollama (local) | `ollama` | (none usually) | Detected on :11434 |
| LM Studio (local) | `lmstudio` | (none usually) | Detected on :1234 |
| OpenCode Zen | `openai_compatible` | `NOVEL_OS_API_KEY` | Base URL: `https://opencode.ai/zen/v1`. Model: `deepseek-v4-flash-free` (free tier) or any supported model. Key from https://opencode.ai/auth. See `references/opencode-zen-config.md`. Set up via `.env` — do NOT rely on Hermes credential pool injection (the process reading `.env` is a subprocess, not Hermes). |
| OpenCode Go | `openai_compatible` | `NOVEL_OS_API_KEY` | Base URL: `https://opencode.ai/zen/go/v1`. $10/mo subscription. Various open models. |
| Generic OpenAI-compatible | `openai_compatible` | `NOVEL_OS_API_KEY` | Must also set `NOVEL_OS_BASE_URL` + `NOVEL_OS_MODEL` |

### Auto-detection order (when no provider is explicitly set)
1. `NOVEL_OS_LLM_PROVIDER` env var
2. `ANTHROPIC_API_KEY` present → anthropic
3. `OPENAI_API_KEY` present → openai
4. `AZURE_OPENAI_API_KEY` + endpoint → azure
5. `GEMINI_API_KEY` / `GOOGLE_API_KEY` → gemini
6. Any alias key (KIMI, GROQ, etc.) → that alias
7. `NOVEL_OS_API_KEY` + `NOVEL_OS_BASE_URL` → openai_compatible
8. `claude` CLI on PATH → claude_cli
9. If none found → raises LLMError

## Natural Language Front-End Pattern

When the user talks to you (the Hermes agent) instead of typing CLI commands, map their requests like this:

| User says | You run |
|-----------|---------|
| "Start a new [genre] novel called [title]" | `init --title "..." --genre "..."` |
| "Add a character named [name], they're the [role]" | `character add --name "..." --role ...` |
| "Add a plot thread about [topic]" | `plot add --name "..." --description "..."` |
| "Outline the book — [N] chapters, [M] words" | `plan outline --chapters N --words M` |
| "Plan chapter [N] from [character]'s POV" | `plan chapter --number N --pov "Character"` |
| "Write chapter [N]" | `write --chapter N` |
| "Edit chapter [N], focus on [mode]" | `edit --chapter N --mode [mode]` |
| "Check continuity on chapter [N]" | `check --chapter N` |
| "Validate chapter [N]" | `validate --chapter N` |
| "Approve chapter [N]" | `approve --chapter N` |
| "Where are we?" / "What's the status?" | `status` |
| "Export the manuscript" | `export --format markdown` |

**Always use the alias:**
```bash
novel-os() { cd /Users/dodhya/novel-os && source .venv/bin/activate && python core/orchestrator.py "$@"; }
```

When checking flags, consult `references/command-reference.md` in this skill.

## Web UI (React + FastAPI)

Novel-OS ships with a full web interface. It lives in two directories under the novel-os root:

| Directory | What it is | Stack |
|-----------|-----------|-------|
| `web/` | React frontend | Vite + React 19 + TypeScript + Tailwind 4 + CodeMirror |
| `api/` | REST API backend | FastAPI + SQLModel (SQLite) + Uvicorn |

### Prerequisites

- **Node.js + npm** (for the React frontend) — install via `brew install node` if missing.
- **Python 3.10+** — the API server requires `sqlmodel>=0.38` which does not support Python 3.9. The user has Python 3.12 at `/opt/homebrew/bin/python3.12`. The CLI orchestrator (`core/`) works fine with Python 3.9.
- The **same `.env` LLM configuration** used by the CLI — the API server reads `NOVEL_OS_LLM_PROVIDER`, `NOVEL_OS_MODEL`, etc. from the root `.env`.

### Setup

**1. Recreate the venv with Python 3.10+** (if currently using the system's 3.9):
```bash
cd /Users/dodhya/novel-os
rm -rf .venv
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Install frontend dependencies:**
```bash
cd /Users/dodhya/novel-os/web
npm install
```

### Launching

**Via Hermes (background processes)** — start both as separate background terminal processes, then verify:

```bash
# Terminal 1 — API server
cd /Users/dodhya/novel-os && source .venv/bin/activate && \
  NOVEL_OS_PROJECTS_DIR=/Users/dodhya/novel-os/projects \
  uvicorn api.main:app --port 8000 --reload

# Terminal 2 — Frontend dev server
cd /Users/dodhya/novel-os/web && npm run dev

# Verification
curl -s http://localhost:8000/api/health                    # → {"status":"ok","version":"0.2.0"}
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/  # → 200
```

Then open `http://localhost:5173` in a browser.

**Via separate terminals** — open two terminal windows:

**API server** (port 8000):
```bash
cd /Users/dodhya/novel-os
source .venv/bin/activate
NOVEL_OS_PROJECTS_DIR=/Users/dodhya/novel-os/projects uvicorn api.main:app --port 8000 --reload
```

**React dev server** (port 5173):
```bash
cd /Users/dodhya/novel-os/web
npm run dev
```

### Architecture

```
Browser (:5173) ──REST──> API (:8000) ──orchestrator──> core/ (LLM agents)
                                  │
                                  └── SQLite DB (projects, chapters, comments, snapshots)
```

- CORS is configured for `localhost:5173` (Vite dev server).
- `NOVEL_OS_PROJECTS_DIR` (env var) controls where project folders live. Defaults to `./projects`.
- Each project folder contains `outputs/state/story_state.json` — the same `StoryState` file the CLI uses.
- The API writes Final text and comments to an SQLite DB (`novel_os.db`) rather than relying solely on the filesystem, so human edits and snapshots persist independently of the CLI pipeline.
- The orchestrator runs as an async background job via the API's `runPhase` endpoint — the frontend polls job status.

### API Endpoints

Refer to `references/api-endpoints.md` for the full REST surface.

## Pitfalls

- **Dry-run**: All commands accept `--dry-run` to emit prompt without calling LLM
- **Style Curator**: Exists but NOT wired into main pipeline yet
- **Approval gating**: `FAIL` status BLOCKS approval — fix issues and re-validate
- **Backups**: `StoryState` auto-backup to `.json.bak` before overwrite
- **No .env = blocked agents**: Write, Edit, and Validate all require an LLM provider. Run `setup` or create `.env` before trying to draft or edit prose.
- **Outputs directory**: All project files go under `outputs/` in the novel-os root. Check `status` to see the active project and chapter progress.
- **Setup is interactive**: The `setup` command prompts for input. It cannot be run silently from a script without a TTY. For non-interactive config, write `.env` directly.
- **Web API needs Python 3.10+**: The FastAPI backend requires `sqlmodel>=0.38` which only supports Python 3.10+. The user has Python 3.12 at `/opt/homebrew/bin/python3.12`. The CLI orchestrator (`core/`) works fine with Python 3.9, so CLI commands don't need a venv rebuild — only the web API server does. If `pip install -r requirements.txt` fails on `sqlmodel`, recreate the venv with Python 3.12.
- **Venv Python vs system Python**: The current venv at `/Users/dodhya/novel-os/.venv/` may use Python 3.9.6 (macOS system). Before running the API server, verify with `python --version`. If < 3.10, recreate with a Homebrew Python.
- **Two background processes to manage**: The web UI needs both the API server (uvicorn) and the Vite dev server running simultaneously as separate background processes. After starting both, always verify with `curl -s http://localhost:8000/api/health` and `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/`.
- **CLI and web UI project directories must align**: The CLI orchestrator creates projects relative to its cwd by default; the API server reads `NOVEL_OS_PROJECTS_DIR` (default `./projects`). If you create a project via the CLI from `/Users/dodhya/novel-os/` and launch the API from the same directory, the default `./projects` paths match. But if you launch either from a different cwd, set `NOVEL_OS_PROJECTS_DIR` explicitly (e.g. `NOVEL_OS_PROJECTS_DIR=/Users/dodhya/novel-os/projects`) so both interfaces see the same project folders. Otherwise the web UI will show an empty project list while the CLI has projects, or vice versa.
