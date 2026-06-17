---
name: hermes-install
description: "Install Hermes Agent from scratch on a new macOS machine — pip, pipx, or Homebrew, with initial config, model provider setup, and health validation."
version: 1.0.0
author: dodhya
models:
  primary: deepseek-v4-flash-free via opencode-zen
  required_models: []
services:
  python3:
    required: true
    description: "Hermes Agent requires Python 3.10–3.12. macOS ships Python 3.x as a stub; install the full runtime via Homebrew (`brew install python@3.11`) or the official Python.org installer."
    setup: "`brew install python@3.11` or download from https://python.org"
  pipx:
    required: false
    description: "Optional — isolated Hermes install via pipx. Recommended over pip for clean dependency isolation."
    setup: "`brew install pipx && pipx ensurepath`"
parameters:
  install.method: pip
  hermes.version: ">=0.16.0"
environment:
  os: [macos]
  homebrew: true
  hermes_version: ">=0.1.0"
src:
  fileManifest: []
  note: "This kit is entirely procedural — no source files to install. Follow the steps in order on a clean macOS machine."
---

## Goal

Install Hermes Agent v0.16.0+ on a fresh macOS machine and perform the initial setup so the agent is ready to receive tasks, connect to a model provider, and load skills. After this kit completes, Hermes will pass `hermes doctor` with no critical failures and be ready for subsequent kits (security hardening, profiles, etc.).

This is the **first kit** in the restoration / setup order — it must run before any profile-specific, skill, plugin, or service kit.

## When to Use

- **Brand new machine** — first-time Hermes setup on a freshly imaged macOS system
- **After OS reinstall** — restore Hermes to a clean macOS installation
- **New team member onboarding** — bring up a new control node for a Hermes agentic network
- **Before any other kit** — all subsequent kits assume a working `hermes` binary and `~/.hermes/` config directory
- **Recovery from corrupted install** — clean reinstall when the existing Hermes home is damaged beyond repair

## Setup

### What you need

| Item | Detail |
|------|--------|
| macOS machine | macOS 14+ (Sonoma/Sequoia) recommended |
| Python 3.10–3.12 | Installed via Homebrew (`brew install python@3.11`) or python.org |
| pip / pipx | Python package manager (comes with Python) |
| Internet connection | First-time setup downloads dependencies and model catalog |
| API key | At least one LLM provider key (OpenAI, Anthropic, Groq, Copilot, etc.) |
| Terminal access | Commands run via macOS Terminal.app or iTerm2 |
| Sudo access | Required if installing Homebrew or system-wide Python packages |

### What this kit produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| Hermes binary | `~/.local/bin/hermes` (pip) or `~/.local/pipx/venvs/hermes-agent/bin/hermes` (pipx) or `/usr/local/bin/hermes` (brew) | The `hermes` CLI entry point |
| Hermes home | `~/.hermes/` | Central directory: config, skills, plugins, sessions, cron, memories, logs |
| Project checkout | `~/.hermes/hermes-agent/` | Full Hermes Agent source tree (installed as editable pip package) |
| Config file | `~/.hermes/config.yaml` | Main configuration: model provider, approvals, toolsets, terminal, skills |
| Environment file | `~/.hermes/.env` | API keys and secrets (created manually or via `hermes setup`) |
| Bootstrap marker | `~/.hermes/hermes-agent/.hermes-bootstrap-complete` | Marker that first-time setup finished |
| Hermes virtualenv | `~/.hermes/hermes-agent/venv/` | Python virtual environment with all dependencies |

### Installation methods at a glance

| Method | Command | Binary location | Isolation | Best for |
|--------|---------|-----------------|-----------|----------|
| **pip** (editable) | `pip3 install hermes-agent` | `~/.local/bin/hermes` | Installs into user site-packages | Development, debugging, quick setup |
| **pipx** | `pipx install hermes-agent` | `~/.local/pipx/venvs/hermes-agent` | Fully isolated venv | Production, clean separation |
| **Homebrew** | `brew install hermes-agent` | `/usr/local/bin/hermes` | Managed by Homebrew | macOS-native feel, easy updates |

This kit documents the **pip install (editable)** path as the default — it's the most commonly used and matches the reference machine (`~/.hermes/hermes-agent/` is both the pip-installed package *and* the project checkout).

## Steps

### Step 1: Install Python 3.11 (if not present)

macOS ships a stub Python 3 that cannot install packages. Install a full Python version via Homebrew:

```bash
# Check if Python is already available
python3 --version

# If missing or not 3.10–3.12, install via Homebrew
brew install python@3.11
```

Verify:

```bash
python3 --version
# Expected: Python 3.11.x (any minor)
which python3
# Expected: /opt/homebrew/bin/python3  (Apple Silicon)
# Expected: /usr/local/bin/python3      (Intel)
```

> **Apple Silicon note**: Homebrew installs into `/opt/homebrew/` on ARM Macs. Ensure `/opt/homebrew/bin` is in your `PATH` (Homebrew's `brew shellenv` does this automatically). If `python3` still points to the system stub, run `export PATH="/opt/homebrew/bin:$PATH"` in your shell config.

---

### Step 2: Install Hermes Agent via pip

Install the `hermes-agent` package. On a fresh system you may need to set up `pip` first:

```bash
# Upgrade pip to the latest version
python3 -m pip install --upgrade pip

# Install Hermes Agent (editable, user-space)
pip3 install hermes-agent
```

This installs Hermes and all its dependencies into the user site-packages directory (`~/.local/lib/python3.11/site-packages/`) and places the `hermes` CLI binary at `~/.local/bin/hermes`.

Expected output (versions may vary):

```
Collecting hermes-agent
  Downloading hermes_agent-0.16.0-py3-none-any.whl (2.4 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.4/2.4 MB 12.3 MB/s eta 0:00:00
Requirement already satisfied: openai in ...
...
Successfully installed hermes-agent-0.16.0
```

Ensure `~/.local/bin` is in your `PATH`:

```bash
# Add to shell config (bash/zsh)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify the binary is found
which hermes
# Expected: /Users/<you>/.local/bin/hermes
```

> **Alternative: pipx install** (recommended for production machines):
>
> ```bash
> brew install pipx
> pipx ensurepath
> pipx install hermes-agent
> which hermes
> # Expected: /Users/<you>/.local/pipx/venvs/hermes-agent/bin/hermes
> ```
>
> pipx keeps Hermes and its dependencies in an isolated virtualenv, avoiding conflicts with other Python projects.

> **Alternative: Homebrew install**:
>
> ```bash
> brew install hermes-agent
> which hermes
> # Expected: /usr/local/bin/hermes
> ```

---

### Step 3: Verify the installation

Check the installed version and that all core dependencies are loadable:

```bash
hermes --version
```

Expected output:

```
Hermes Agent v0.16.0 (2026.6.5) · upstream 33b1d144
Project: /Users/<you>/.hermes/hermes-agent
Python: 3.11.15
OpenAI SDK: 2.24.0
Up to date
```

> ⚠️ **If `hermes --version` fails** with `ModuleNotFoundError`, a dependency may not have installed correctly. Re-run `pip3 install hermes-agent --force-reinstall`. If it fails with `command not found`, check that `~/.local/bin` is in your `PATH` (Step 2) or use the full path `~/.local/bin/hermes --version`.

---

### Step 4: Run initial setup

Hermes needs a config directory and provider configuration before it can operate. The recommended first step is to run `hermes doctor` to identify what's missing, then run `hermes setup` to walk through the interactive initial configuration.

```bash
# Check health first — this will flag missing items
hermes doctor
```

Expected output on a fresh install:

```
╭─ Hermes Doctor ─────────────────────────────────╮
│                                                    │
│  ✔ Python        3.11.15                           │
│  ✔ Hermes home   ~/.hermes/                        │
│  ✘ Config        ~/.hermes/config.yaml — MISSING   │
│  ✘ Provider      Not configured                    │
│  ✘ .env          Not found                         │
│                                                    │
│  Run 'hermes setup' to configure.                  │
╰────────────────────────────────────────────────────╯
```

Now run the interactive setup:

```bash
hermes setup
```

This will walk you through:

1. **Model provider selection** — Choose your LLM backend (see Step 5 for options)
2. **API key entry** — Paste your provider's API key (stored in `~/.hermes/.env`)
3. **Profile name** (optional) — Name your first profile
4. **Toolsets** — Confirm which tool groups to enable (terminal, file, browser, web, etc.)

If you prefer a non-interactive setup, create the config files manually:

**Minimal `~/.hermes/config.yaml`:**

```yaml
model:
  provider: openai
  default: gpt-4o
  api_mode: chat_completions

agent:
  max_turns: 90
  reasoning_effort: medium

terminal:
  backend: local
  timeout: 180

approvals:
  mode: on
  timeout: 60
```

**Minimal `~/.hermes/.env`:**

```env
# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Or Anthropic
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Or Groq
# GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then set restrictive permissions on the `.env` file:

```bash
chmod 600 ~/.hermes/.env
```

---

### Step 5: Set the model provider

After setup, verify or change the active model provider:

```bash
# Check current provider
hermes model

# Set a provider interactively
hermes model set

# Or set directly:
hermes config set model.provider copilot
hermes config set model.default gpt-5-mini
```

Supported providers (non-exhaustive):

| Provider | Config value | Key env var | Notes |
|----------|-------------|-------------|-------|
| OpenAI | `openai` | `OPENAI_API_KEY` | GPT-4o, GPT-4.1, o-series |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | Claude 4 Sonnet, Opus |
| Copilot | `copilot` | `GITHUB_TOKEN` | GitHub Models API (free tier available) |
| Groq | `groq` | `GROQ_API_KEY` | Fast inference, open models |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | Aggregator for 200+ models |
| xAI | `xai` | `XAI_API_KEY` | Grok models |
| Gemini | `gemini` | `GEMINI_API_KEY` | Google Gemini models |
| Bedrock | `bedrock` | (IAM-based) | AWS Bedrock, Claude models |
| Local (Ollama) | `ollama` | (none) | Local LLMs via Ollama |

After changing the provider, verify the connection:

```bash
hermes model test
```

This sends a small test prompt to the configured model and reports back the response time and any errors.

---

### Step 6: Run health check

Confirm everything is operational:

```bash
hermes doctor
```

Expected output on a properly configured system:

```
╭─ Hermes Doctor ─────────────────────────────────╮
│                                                    │
│  ✔ Python        3.11.15                           │
│  ✔ Hermes home   ~/.hermes/                        │
│  ✔ Config        ~/.hermes/config.yaml — OK        │
│  ✔ Provider      copilot — GPT-5-mini              │
│  ✔ .env          Found (permissions OK)            │
│  ✔ Skills dir    ~/.hermes/skills/                 │
│  ✔ Cron dir      ~/.hermes/cron/                   │
│  ✔ Logs dir      ~/.hermes/logs/                   │
│  ✔ State DB      ~/.hermes/state.db — OK           │
│  ✔ Updates       Up to date                        │
│                                                    │
│  All checks passed. Hermes is ready to use.       │
╰────────────────────────────────────────────────────╯
```

> 🔁 **What if checks fail?**
>
> | Symptom | Fix |
> |---------|-----|
> | `Config — MISSING` | Run `hermes setup` or create `config.yaml` manually (Step 4) |
> | `Provider — Not configured` | Run `hermes model set` (Step 5) |
> | `.env — Not found` | Create `~/.hermes/.env` with your API key (Step 4) |
> | `OpenAI SDK` import error | Reinstall: `pip3 install --force-reinstall hermes-agent` |
> | `~/.hermes/` not created | `mkdir -p ~/.hermes/{skills,cron,logs,sessions,memories}` |

---

### Step 7: Start a test conversation

Verify the agent can have a real interactive conversation:

```bash
# One-shot query (non-interactive)
hermes -p "Hello, what version are you and what tools do you have available?"
```

This should connect to your model provider, get a response, and print it. If it succeeds, Hermes is fully operational.

For an interactive session:

```bash
hermes
```

Type a greeting and verify the agent responds. Exit with `Ctrl+C` or `/exit`.

---

### Step 8: Install additional dependencies (optional but recommended)

Several Hermes features require optional dependencies that are not installed by default. Based on the reference machine's installed requirements, these packages are needed for full functionality:

```bash
# Core extras: browser automation, voice, image generation
pip3 install "hermes-agent[all]"

# Or install specific extras individually:
pip3 install "hermes-agent[browser]"   # Browser automation (Playwright)
pip3 install "hermes-agent[voice]"     # Text-to-speech and voice input
pip3 install "hermes-agent[images]"    # Image generation and vision
```

Alternatively, install the known dependency set directly:

```bash
pip3 install openai certifi python-dotenv fire httpx rich tenacity \
  pyyaml ruamel.yaml requests jinja2 pydantic prompt_toolkit \
  croniter packaging Markdown PyJWT urllib3 psutil websockets \
  pathspec fastapi uvicorn Pillow ptyprocess
```

> **Note**: The `hermes-agent` pip package installs all core dependencies automatically (Step 2). The commands above install extras (browser automation, voice) that are not part of the core dependency list. The comprehensive list shown is for reference — you do not need to install them individually after `pip3 install hermes-agent`.

---

### Step 9: Enable Tirith (command scanning)

Tirith is the runtime command scanner that blocks credential leakage. It auto-downloads on the first `terminal()` call in a Hermes session, but you can pre-install it:

```bash
# Trigger the auto-download by running a harmless terminal command
# (e.g., inside a Hermes session: /terminal echo "Tirith download triggered")

# Or download manually:
~/.hermes/bin/tirith --help
# (If not present, it auto-installs on first terminal() use)
```

To verify Tirith is active:

```bash
hermes config get security.tirith_enabled
# Expected: true
```

See the **security-hardening** kit for comprehensive Tirith policy configuration.

---

## Constraints

- **Python version must be 3.10–3.12.** Hermes v0.16.0 does not support Python 3.13+ (some dependencies lack binary wheels). Use `python@3.11` for best compatibility.
- **`~/.local/bin` must be in `PATH`.** The pip user-space install places binaries here, and many macOS shells do not include it by default. Without it, `hermes` will not be found without the full path.
- **`.env` files are for secrets only.** Never put behavioral config (timeouts, feature flags, display preferences) in `.env`. Those belong in `config.yaml`. Putting secrets in `config.yaml` is also unsupported.
- **First `terminal()` call triggers Tirith auto-download.** Tirith does not ship with the pip package; it downloads on first use. Run a harmless command (`echo ok`) on first session if `hermes doctor` shows Tirith as missing.
- **Config changes need a session restart.** `hermes config set` changes do not take effect in an already-running Hermes session. Start a new session (`/reset` or new `hermes` invocation) after changing config.
- **App Store receipt validation (desktop app).** The Hermes desktop GUI app validates receipts on launch. If you are using only the CLI (`hermes` in Terminal), this does not apply.
- **Homebrew formula may lag behind.** The `pip` package is always the most up-to-date. If using Homebrew, check `brew info hermes-agent` for the version before installing.
- **`hermes setup` is interactive.** It requires a terminal with stdin. For fully automated deployments, create `config.yaml` and `.env` manually (Step 4) instead.

## Safety Notes

- **API keys in `.env` must be kept secret.** Set `chmod 600 ~/.hermes/.env` and never commit it to git. The `.env` file is automatically git-ignored if it's inside `~/.hermes/`.
- **Consider a dedicated machine user** for Hermes rather than installing under your personal macOS account if the agent has access to sensitive systems (deployment keys, production databases, infrastructure).
- **pip's editable install** (`pip3 install hermes-agent`) places the package in user site-packages, which means any other Python project on the same user account could potentially import and interact with Hermes internals. For strict isolation, use **pipx** or a **dedicated Python venv**.
- **`hermes doctor` exposes configured provider and model names** — do not share doctor output in public channels if it reveals internal infrastructure details like custom base URLs or model names.
- **The Hermes `~/.hermes/` directory contains session history and cached credentials.** On a shared machine, ensure `~/.hermes/` has permissions `700` and is excluded from backups that sync to untrusted storage.
- **macOS keychain integration** is not automatic. API keys stored in `.env` are protected only by filesystem permissions. For stronger secret storage, configure Bitwarden or use the system keychain (see Hermes Bitwarden plugin documentation).

## Failures Overcome

1. **`~/.local/bin` not in PATH on macOS** — Fresh macOS installations do not include `~/.local/bin` in `$PATH`. The fix is to add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` (or `~/.bash_profile`). After adding, `source ~/.zshrc` or open a new terminal tab.

2. **Apple Silicon Python vs Homebrew Python** — macOS on ARM (M1/M2/M3/M4) ships a stub Python at `/usr/bin/python3` that cannot install packages. Homebrew's `python@3.11` installs to `/opt/homebrew/bin/python3`. If `pip3 install hermes-agent` fails with "externally-managed-environment" or "permission denied," ensure you're using the Homebrew Python (`which python3` → `/opt/homebrew/bin/python3`). The PEP 668 guard blocks `pip install --user` on system Python. Solution: use Homebrew Python or a virtual environment.

3. **PEP 668 / externally-managed-environment error** — macOS 14+ (Sonoma) and Homebrew Python mark the base interpreter as externally managed. Running `pip3 install` without a venv produces `error: externally-managed-environment`. Solutions: (a) install with `pipx` (recommended), (b) create a virtualenv (`python3 -m venv ~/.hermes-venv && source ~/.hermes-venv/bin/activate && pip install hermes-agent`), or (c) override with `pip3 install hermes-agent --break-system-packages` (not recommended for production).

4. **`hermes setup` hangs with no prompt** — If stdin is not a TTY (e.g., piped commands, CI, VS Code terminal), `hermes setup` may appear to hang because it's waiting for interactive input. Use the manual config file creation approach instead (Step 4). Or run in a proper terminal.

5. **Tirith not found on first `hermes doctor`** — Tirith is not bundled with the pip package. It auto-downloads when the `terminal()` tool is first called in a Hermes session. Run `echo ok` in a terminal tool call inside Hermes, then re-check. Alternatively, download it manually from the Hermes GitHub releases page.

6. **`hermes --version` shows wrong or cached version** — If you updated Hermes but `--version` shows the old version, clear the pip cache and reinstall: `pip3 cache purge && pip3 install --force-reinstall hermes-agent`. If using an editable install from a git checkout, run `git pull` in `~/.hermes/hermes-agent/`.

7. **OpenAI SDK import error after install** — Some dependency versions conflict. Fix with: `pip3 install --force-reinstall "openai>=1.0.0" "httpx>=0.27.0" "pydantic>=2.0.0"` then `pip3 install --force-reinstall hermes-agent`.

## Validation

After completing all steps, this checklist confirms Hermes Agent is fully installed and operational:

- [ ] `python3 --version` shows 3.10–3.12
- [ ] `which hermes` returns a path in `~/.local/bin/` or `/usr/local/bin/`
- [ ] `hermes --version` returns `Hermes Agent v0.16.0` (or later)
- [ ] `~/.hermes/config.yaml` exists and is valid YAML
- [ ] `~/.hermes/.env` exists with at least one API key (`chmod 600`)
- [ ] `hermes doctor` passes all checks (Config, Provider, .env)
- [ ] `hermes model test` returns a valid model response (no auth/network errors)
- [ ] `hermes -p "Hello"` returns a conversational response from the agent
- [ ] `hermes config get security.tirith_enabled` is `true`
- [ ] `~/.local/bin` is in `$PATH` (persistent across shell restarts)
- [ ] Required dependencies listed in `pip3 show hermes-agent | grep Requires` are all installed
