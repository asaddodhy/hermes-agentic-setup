---
name: novel-os
description: "Install, restore, and integrate Novel-OS — a multi-agent fiction writing framework — with full novelist Hermes profile integration"
version: 1.1.0
author: dodhya
models:
  primary: deepseek-v4-flash-free via OpenCode Zen
  required_models: []
services:
  novel-os:
    required: true
    description: "Multi-agent fiction writing framework by mrigankad. 5 specialized AI agents (Architect, Scribe, Editor, Guardian, Curator) with persistent StoryState, deterministic continuity engine, and provider-agnostic LLM layer."
    setup: "See Steps below. Clone from github.com/mrigankad/Novel-OS, install deps, configure .env, and copy the novelist profile artifacts."
parameters:
  approvals.mode: smart
environment:
  os: [macos]
  homebrew: false
  python: ">=3.10 (web API), >=3.8 (CLI)"
  hermes_version: ">=0.1.0"
src:
  fileManifest:
    - path: src/SKILL.md
      role: "Hermes skill — Novel-OS integration skill for the novelist profile, covering CLI commands, 5-agent pipeline, Web UI setup, and natural language front-end pattern"
      destination: ~/.hermes/profiles/novelist/skills/novel-os/SKILL.md
    - path: src/SOUL.md
      role: "Novelist profile SOUL — warm editor personality, Novel-OS aware, collaborative literary tone"
      destination: ~/.hermes/profiles/novelist/SOUL.md
    - path: src/AGENTS.md
      role: "Novelist profile AGENTS — profile rules, isolation, and Novel-OS integration guidance"
      destination: ~/.hermes/profiles/novelist/AGENTS.md
    - path: src/references/command-reference.md
      role: "CLI command reference for all Novel-OS orchestrator commands"
      destination: ~/.hermes/profiles/novelist/skills/novel-os/references/command-reference.md
    - path: src/references/api-endpoints.md
      role: "REST API reference for the Novel-OS Web UI backend"
      destination: ~/.hermes/profiles/novelist/skills/novel-os/references/api-endpoints.md
    - path: src/references/opencode-zen-config.md
      role: "OpenCode Zen LLM provider configuration guide for Novel-OS"
      destination: ~/.hermes/profiles/novelist/skills/novel-os/references/opencode-zen-config.md
---

## Goal

Install **Novel-OS** — a production-grade multi-agent fiction writing framework — and integrate it into a dedicated **novelist** Hermes profile with full skill support, SOUL personality, agent pipeline awareness, and a private isolated writing environment.

When this kit has been applied, you can:
- Run the full 5-agent novel writing pipeline (Architect → Scribe → Editor → Guardian → Approve)
- Use any of 13+ LLM providers (auto-detected from env vars)
- Persist StoryState across sessions with character, plot, and continuity tracking
- Access the Web UI (React + FastAPI dashboard)
- Control the entire pipeline through natural language via the Hermes agent

## When to Use

- **First-time Novel-OS setup** — run this kit after creating the novelist Hermes profile
- **After a profile/data loss** — restore the novelist profile's skills, SOUL, and AGENTS from the src/ artifacts
- **Migrating to a new machine** — re-clone Novel-OS and re-apply profile artifacts
- **After a new Hermes install** — rebuild the novelist profile with Novel-OS integration

## Setup

### What you need

- Hermes Agent running with profile management enabled
- Terminal access (commands run via Hermes terminal tool)
- Git (to clone the Novel-OS repo)
- Python 3.8+ (CLI) or Python 3.10+ (Web UI API server)
- At least one LLM API key or provider (Claude Code CLI subscription, Anthropic, OpenAI, Gemini, etc.)
- Node.js + npm (for the Web UI frontend)
- Optional: Homebrew Python 3.12 at `/opt/homebrew/bin/python3.12`

### What this kit installs

| File | Destination | Purpose |
|------|-------------|---------|
| `src/SKILL.md` | `~/.hermes/profiles/novelist/skills/novel-os/SKILL.md` | Full Novel-OS integration skill — 296 lines covering CLI, pipeline, Web UI, LLM providers |
| `src/SOUL.md` | `~/.hermes/profiles/novelist/SOUL.md` | Warm editor personality — collaborative, critique-capable, Novel-OS aware |
| `src/AGENTS.md` | `~/.hermes/profiles/novelist/AGENTS.md` | Profile rules — isolation, Novel-OS pipeline reference, 5-agent structure |
| `src/references/command-reference.md` | `~/.hermes/profiles/novelist/skills/novel-os/references/command-reference.md` | CLI command reference (init, write, edit, validate, etc.) |
| `src/references/api-endpoints.md` | `~/.hermes/profiles/novelist/skills/novel-os/references/api-endpoints.md` | REST API endpoint reference for the Web UI |
| `src/references/opencode-zen-config.md` | `~/.hermes/profiles/novelist/skills/novel-os/references/opencode-zen-config.md` | OpenCode Zen provider config guide |

## Steps

### Step 1: Clone Novel-OS

```bash
git clone https://github.com/mrigankad/Novel-OS.git ~/novel-os
cd ~/novel-os
```

Verify the clone:

```bash
ls -la ~/novel-os/
# Should show: AGENTS.md, README.md, core/, agents/, api/, web/, etc.
```

### Step 2: Create the Python virtual environment and install dependencies

```bash
cd ~/novel-os
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For the Web UI API server (requires Python 3.10+), recreate the venv with a newer Python if needed:

```bash
cd ~/novel-os
rm -rf .venv
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure your LLM provider

**Option A — Interactive wizard (recommended):**

```bash
cd ~/novel-os && source .venv/bin/activate && python core/orchestrator.py setup
```

Auto-detects available providers (Claude Code CLI, any API keys in env, running local servers), offers a numbered menu, and tests the connection before saving.

**Option B — Manual `.env` configuration:**

Copy the example file and edit:

```bash
cd ~/novel-os
cp .env.example .env
```

Edit `.env` with your preferred provider. Example for OpenCode Zen:

```
NOVEL_OS_LLM_PROVIDER=openai_compatible
NOVEL_OS_BASE_URL=https://opencode.ai/zen/v1
NOVEL_OS_API_KEY=sk-...   # Your key from https://opencode.ai/auth
NOVEL_OS_MODEL=deepseek-v4-flash-free
NOVEL_OS_MAX_TOKENS=8192
```

Supported providers: `anthropic`, `openai`, `azure`, `gemini`, `nvidia`, `kimi`, `groq`, `together`, `openrouter`, `deepseek`, `mistral`, `fireworks`, `ollama`, `lmstudio`, `claude_cli`, `openai_compatible` (any OpenAI-compatible endpoint).

**Important:** The `.env` file must contain the actual API key. Novel-OS reads it via `python-dotenv` as a subprocess — it does NOT have access to Hermes-injected environment variables.

### Step 4: Set up the shell alias

Add the `novel-os` alias to your shell config:

```bash
cat >> ~/.zshrc << 'EOF'

# Novel-OS alias — run via Hermes terminal tool
novel-os() {
    cd ~/novel-os && source .venv/bin/activate && python core/orchestrator.py "$@"
}
EOF

source ~/.zshrc
```

### Step 5: Verify the CLI works

```bash
cd ~/novel-os && source .venv/bin/activate && python core/orchestrator.py --help
```

Expected output — shows all available commands: `init`, `character`, `plot`, `plan`, `write`, `edit`, `validate`, `check`, `approve`, `export`, `status`, `setup`.

### Step 6: Initialize a test project

```bash
cd ~/novel-os && source .venv/bin/activate && \
python core/orchestrator.py init --title "Test Project" --genre "Test"
```

Expected output — project created confirmation. Verify:

```bash
python core/orchestrator.py status
```

### Step 7: Install the novelist Hermes profile artifacts

Create the novelist profile (if not already present):

```bash
hermes profile create novelist
```

Copy the skill, SOUL, and AGENTS into the profile:

```bash
# Create the skill directory
mkdir -p ~/.hermes/profiles/novelist/skills/novel-os/references

# Copy skill
cp src/SKILL.md ~/.hermes/profiles/novelist/skills/novel-os/SKILL.md

# Copy profile artifacts
cp src/SOUL.md ~/.hermes/profiles/novelist/SOUL.md
cp src/AGENTS.md ~/.hermes/profiles/novelist/AGENTS.md

# Copy references
cp src/references/command-reference.md ~/.hermes/profiles/novelist/skills/novel-os/references/command-reference.md
cp src/references/api-endpoints.md ~/.hermes/profiles/novelist/skills/novel-os/references/api-endpoints.md
cp src/references/opencode-zen-config.md ~/.hermes/profiles/novelist/skills/novel-os/references/opencode-zen-config.md

# Copy config
cat > ~/.hermes/profiles/novelist/config.yaml << 'CONF'
agent:
  reasoning_effort: low
approvals:
  mode: smart
CONF
```

### Step 8: Verify all artifacts are in place

```bash
# Skill
ls -la ~/.hermes/profiles/novelist/skills/novel-os/SKILL.md

# SOUL
ls -la ~/.hermes/profiles/novelist/SOUL.md

# AGENTS
ls -la ~/.hermes/profiles/novelist/AGENTS.md

# References
ls -la ~/.hermes/profiles/novelist/skills/novel-os/references/

# Config
cat ~/.hermes/profiles/novelist/config.yaml
```

### Step 9: Test the 5-agent pipeline (optional)

```bash
# Start a session with the novelist profile
hermes -p novelist

# In the session, the agent should be Novel-OS aware.
# Try asking: "What's the Novel-OS pipeline?"
# Or run via terminal tool:
novel-os status
novel-os character add --name "Lena" --role protagonist
novel-os plot add --name "Main Plot" --description "The central conflict"
novel-os plan outline --chapters 8 --words 20000
novel-os plan chapter --number 1 --pov "Lena"
novel-os write --chapter 1 --dry-run
```

### Step 10: (Optional) Set up the Web UI

**Prerequisites:**
- Python 3.10+ venv (see Step 2)
- Node.js + npm: `brew install node` if missing
- The same `.env` LLM configuration used by the CLI

**Install frontend dependencies:**

```bash
cd ~/novel-os/web
npm install
```

**Launch (two background processes):**

Terminal 1 — API server:
```bash
cd ~/novel-os && source .venv/bin/activate && \
  NOVEL_OS_PROJECTS_DIR=~/novel-os/projects \
  uvicorn api.main:app --port 8000 --reload
```

Terminal 2 — Vite dev server:
```bash
cd ~/novel-os/web && npm run dev
```

**Verify both are running:**

```bash
curl -s http://localhost:8000/api/health
# → {"status":"ok","version":"0.2.0"}

curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
# → 200
```

Open `http://localhost:5173` in a browser.

## Constraints

- **Novel-OS is NOT the user's own repo** — it's cloned from `github.com/mrigankad/Novel-OS`. Do not push changes upstream unless explicitly directed.
- **CLI and Web UI project directories must align** — both must use the same projects path. Set `NOVEL_OS_PROJECTS_DIR` explicitly when running the API server.
- **Venv Python version matters** — CLI works with Python 3.8+, but the Web API (sqlmodel) requires Python 3.10+. The current venv at `~/novel-os/.venv/` may need recreating with a Homebrew Python.
- **Two background processes for Web UI** — both the API server (uvicorn) and Vite dev server must run simultaneously. Manage as Hermes background processes.
- **No .env = blocked agents** — Write, Edit, and Validate all require an LLM provider. Run `setup` or create `.env` before drafting.
- **Setup is interactive** — the `setup` command prompts for input. For non-interactive config, write `.env` directly.
- **Style Curator agent exists but is NOT wired into the main pipeline yet** — it's available in the codebase but has no orchestrator invocation.
- **Approval gating** — `FAIL` status from Guardian BLOCKS approval. Fix issues and re-validate.
- **Profile isolation** — the novelist profile's memory, history, and skills are isolated from the default tech profile. Before switching away, note any in-progress work.
- **StoryState auto-backup** — backed up to `.json.bak` before each overwrite.

## Safety Notes

- The `.env` file contains LLM API keys — treat it as sensitive. The kit's cross-profile guard prevents accidental reads.
- Novel-OS runs as a subprocess from Hermes — env vars injected by Hermes are NOT visible to it. API keys must be written directly into `.env`.
- `--dry-run` is available on write, edit, and validate commands to inspect prompts without calling the LLM — useful for debugging and testing.
- The Web UI and CLI share the same project directory. Creating a project via CLI from `~/novel-os/` and launching the API from the same directory means the default `./projects` paths align.

## Failures Overcome

1. **Venv Python version mismatch** — `pip install -r requirements.txt` fails on `sqlmodel>=0.38` with Python 3.9. Recreate venv with Python 3.10+ (`/opt/homebrew/bin/python3.12`).
2. **Process environment isolation** — Novel-OS subprocess doesn't inherit Hermes-injected env vars. API keys must be written into `.env` file directly, not passed via Hermes credential pool injection.
3. **Web UI not starting** — requires both API server AND Vite dev server running simultaneously as separate background processes. Verify both with health checks.
4. **Web UI shows empty project list** — the API server's cwd sets the default `NOVEL_OS_PROJECTS_DIR`. If it differs from where CLI ran `init`, projects won't be found. Set `NOVEL_OS_PROJECTS_DIR` explicitly.
5. **`setup` command blocks in non-TTY** — the interactive wizard can't run from scripts. For automated setup, write `.env` variables directly.
6. **Profile artifacts not loading** — the SOUL.md and AGENTS.md files must be owned by the profile directory. Check permissions with `ls -la ~/.hermes/profiles/novelist/`.

## Validation

After completing all steps, this checklist confirms success:

- [ ] `~/novel-os/` exists with cloned repo (AGENTS.md, README.md, core/, api/, web/, etc.)
- [ ] `~/novel-os/.venv/` exists with Python and dependencies installed
- [ ] `~/novel-os/.env` contains a working LLM provider configuration
- [ ] `python core/orchestrator.py --help` shows all commands
- [ ] `python core/orchestrator.py init --title "Test" --genre "Test"` succeeds
- [ ] Shell alias `novel-os()` is defined and functional
- [ ] `~/.hermes/profiles/novelist/skills/novel-os/SKILL.md` exists (13.7KB)
- [ ] `~/.hermes/profiles/novelist/SOUL.md` exists (editing personality)
- [ ] `~/.hermes/profiles/novelist/AGENTS.md` exists (5-agent pipeline reference)
- [ ] All references exist under `skills/novel-os/references/`
- [ ] `~/.hermes/profiles/novelist/config.yaml` is set with `approvals.mode: smart`
- [ ] (Optional) Web UI: `curl http://localhost:8000/api/health` returns `{"status":"ok"}`
- [ ] (Optional) Web UI: `curl http://localhost:5173/` returns HTTP 200
