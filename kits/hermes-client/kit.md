---
name: hermes-client
description: "Install lotsoftick/hermes_client web UI and apply the skill-picker patch to expose Hermes skills from the chat input."
version: 1.0.0
author: dodhya
models:
  primary: any
services:
  hermes-client:
    required: true
    description: "React/Node web UI for Hermes — supervisor manages UI (:18888) and API (:18889)"
    setup: "Installed via npm + hermes_client CLI (see Steps below)"
parameters:
  client.ui_port: 18888
  client.api_port: 18889
environment:
  os: [macos, linux]
  hermes_version: ">=0.17.0"
  node_version: ">=22"
dependencies:
  - hermes-install
tags: [web-ui, skills, chat, optional]
src:
  fileManifest:
    - patches/skill-picker.patch
---

# Hermes Client — Web UI + Skill Picker

> **Optional component.** This kit installs `lotsoftick/hermes_client`, a community-built
> React web UI for Hermes, and applies a custom patch that adds a **`/` skill selector** to
> the chat input — mirroring the skill-loading experience from the Hermes desktop app.
>
> ⚠️ **Work in progress.** The skill picker feature is not part of the original upstream repo.
> The patch is community-contributed and may have bugs — in particular, clicking a skill item
> to select it has a known intermittent focus race condition on some browsers. Skill activation
> via keyboard (type `/`, filter, `Enter`) works reliably.

## Goal

After completing this kit you will have:
- A running web UI at `http://localhost:18888` backed by a local Hermes CLI subprocess
- The `/` skill picker dropdown in the chat input, showing all your installed Hermes skills
- A `hermes_client` supervisor command to start/stop the service

## Source Repository

**Original upstream:** https://github.com/lotsoftick/hermes_client

This kit does **not** fork or copy the upstream repo. It:
1. Clones the original repo
2. Installs dependencies
3. Applies the `skill-picker.patch` from this kit's `src/patches/` directory
4. Builds and deploys via the upstream supervisor

All upstream changes (bug fixes, features) can still be pulled with `git pull` — just
re-apply the patch afterwards if there are conflicts.

## Prerequisites

| Requirement | Check |
|---|---|
| Node ≥ 22 | `node --version` |
| npm ≥ 10 | `npm --version` |
| Hermes CLI installed | `hermes --version` |
| Hermes profile(s) configured with a working model | `hermes chat -Q -q "hi"` returns a response |

## Architecture

```
Browser → http://localhost:18888
            ↓  (Vite preview — serves pre-built bundle)
          hermes_client UI (React/MUI)
            ↓  (SSE + REST)
          http://localhost:18889  (Express API)
            ↓  (spawn subprocess)
          hermes chat -Q [-s <skillName>] -q "<message>"
            ↓
          Hermes CLI → LLM provider
```

The skill picker sends `skillName` in the FormData POST body. The API server passes
`-s <skillName>` to `hermes chat` on **new sessions only** (not resumed ones — the skill
persists in the session after the first turn).

## Steps

### 1 — Clone the upstream repo

```bash
git clone https://github.com/lotsoftick/hermes_client.git ~/hermes_client
```

### 2 — Install the hermes_client CLI

The repo ships a global CLI (`hermes_client start/stop`) via npm:

```bash
cd ~/hermes_client && npm install -g .
```

Verify:

```bash
hermes_client --version 2>/dev/null || hermes_client help
```

### 3 — Run the first-time setup

```bash
hermes_client setup
```

This creates `~/.hermes_client/` with the API `.env` (JWT secret, DB path, ports).

### 4 — Apply the skill-picker patch

Copy the patch from this kit's `src/patches/` directory and apply it:

```bash
# From the repo root (adjust path to wherever you cloned hermes-agentic-setup)
cp ~/hermes-agentic-setup/kits/hermes-client/src/patches/skill-picker.patch ~/hermes_client/
cd ~/hermes_client
git apply skill-picker.patch
```

If the patch fails due to upstream changes, apply hunks manually — the changes are small
and documented in the **What the patch does** section below.

Verify the patch applied cleanly:

```bash
git diff --stat
# Expected:
#  api/src/@types/message.ts                           | 1 +
#  api/src/routes/message/controller.ts                | 3 +-
#  api/src/services/hermes/chat.ts                     | 5 +
#  client/src/features/message/send/model/useSendMessage.ts | 6 +-
#  client/src/widgets/chat/model/types.ts              | 2 +-
#  client/src/widgets/chat/ui/ChatInput.tsx            | ~270 lines changed
```

### 5 — Build client and API

```bash
# Build the API (TypeScript → JavaScript)
cd ~/hermes_client/api && npm install && npm run build

# Build the client (Vite bundle)
cd ~/hermes_client/client && npm install && npm run build
```

Both should exit 0 with no TypeScript errors.

### 6 — Deploy builds and start the supervisor

The supervisor serves pre-built bundles — copy them into the deployed location:

```bash
cp -r ~/hermes_client/client/dist/. ~/.hermes_client/client/dist/
cp -r ~/hermes_client/api/build/.   ~/.hermes_client/api/build/
```

Then start:

```bash
hermes_client start
```

Check it's up:

```bash
curl -o /dev/null -w "UI: %{http_code}\n"  http://localhost:18888
curl -o /dev/null -w "API: %{http_code}\n" http://localhost:18889/api/skill
# UI: 200   API: 401 (auth required — expected)
```

### 7 — Create your account

Open `http://localhost:18888` in a browser. The first-run screen lets you register an
account (stored in the local SQLite DB at `~/.hermes_client/data/hermes.sqlite`).

### 8 — Fix the model (important)

The web UI spawns `hermes chat -Q` as a subprocess using the profile's configured model.
**GitHub Copilot's `claude-sonnet-4.6` model ID is not accepted by the Copilot API in
headless subprocesses.** Use a model that works:

```bash
# Option A — GPT-4o via Copilot (reliable)
hermes config set model.default gpt-4o

# Option B — DeepSeek free tier via opencode-zen
hermes config set model.default deepseek-v4-flash-free
hermes config set model.provider opencode-zen
```

Test before opening the UI:

```bash
hermes chat -Q -q "say hi in one word" 2>&1 | tail -2
# Should print a word, not an error
```

## What the patch does

Six files are modified — all changes are additive and backwards-compatible:

| File | Change |
|---|---|
| `api/src/@types/message.ts` | Adds `skillName?: string` to `ChatRequestBody` type |
| `api/src/routes/message/controller.ts` | Reads `skillName` from request body, passes to `streamChat()` |
| `api/src/services/hermes/chat.ts` | Adds `skillName` to `ChatOptions`; `buildArgs()` appends `-s <skillName>` on new sessions |
| `client/src/features/message/send/model/useSendMessage.ts` | `send()` accepts optional `skillName`; appends to FormData |
| `client/src/widgets/chat/model/types.ts` | Updates `ChatState.send` type signature |
| `client/src/widgets/chat/ui/ChatInput.tsx` | Full skill picker UI: `/` trigger, MUI Popper dropdown, skill chip, keyboard nav |

### How the skill picker works

```
User types "/"          → COMMAND_RE matches → showSkillPicker=true
User types "/ascii"     → skillFilter="ascii" → filtered list updates live
User clicks skill       → handleSkillSelect(name) → chip shown, text cleared
User sends message      → skillName appended to FormData
API controller          → passes skillName to streamChat()
chat.ts buildArgs()     → adds "-s <skillName>" to hermes chat -Q args
Hermes CLI              → loads skill into system prompt via native -s flag
```

The `-s` flag is only added on **new sessions** (`!resumeSessionId`). Once loaded, the
skill persists in the Hermes session for all subsequent turns.

## Known Bugs / Limitations

- **Click race condition:** On some browsers, clicking a skill in the dropdown may close
  the picker without selecting the skill. Workaround: type `/` + partial name to filter to
  one result, then press `Enter`, or click more slowly/deliberately.
- **Skill persists per Hermes session, not per conversation turn:** Once a skill is loaded
  via `-s`, it stays active for the entire session. Starting a new conversation creates a
  new session.
- **Skill injection via message body was tested and rejected:** The LLM detects injected
  skill content as a "prompt injection attempt". The `-s` CLI flag is the only reliable
  mechanism — this is why the patch routes through the backend rather than the frontend.
- **Model name must be compatible with headless subprocess calls** — see Step 8 above.

## Updating upstream

```bash
cd ~/hermes_client
git stash          # stash our patch
git pull           # pull upstream changes
git stash pop      # re-apply patch (or: git apply skill-picker.patch)
# Resolve any conflicts manually if upstream changed the same files
cd api && npm run build
cd ../client && npm run build
cp -r dist/. ~/.hermes_client/client/dist/
cp -r ../api/build/. ~/.hermes_client/api/build/
hermes_client stop && hermes_client start
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `HTTP 400: The requested model is not supported` | Model name incompatible with headless subprocess | Run Step 8 — set a compatible model |
| Skill picker doesn't open on `/` | Old build still deployed | Re-run Steps 5–6 (rebuild + redeploy dist) |
| `git apply` fails | Upstream changed the patched files | Apply hunks manually — see **What the patch does** table |
| `hermes_client start` fails | Port conflict or missing build | Check `lsof -i :18888`; ensure Step 5 completed |
| Login returns 401 | Wrong password or no account | Register at first-run screen; or reset via sqlite3 |

## Verification Checklist

```text
[ ] git apply skill-picker.patch — exit 0, no errors
[ ] cd api && npm run build — exit 0
[ ] cd client && npm run build — exit 0
[ ] hermes_client start — "🚀 started" message
[ ] curl http://localhost:18888 — HTTP 200
[ ] hermes chat -Q -q "hi" — returns a response (not HTTP 400)
[ ] Browser: type "/" in chat input — skill dropdown appears
[ ] Browser: select a skill — chip shows above input
[ ] Browser: send message — LLM follows skill instructions
```
