---
name: hermes-mcp-remote-bridge
description: "Bridge two Hermes Agent instances over SSH stdio via the MCP protocol — giving the local agent access to 10+ messaging tools on a remote machine."
version: 1.0.0
author: dodhya
models:
  primary: any
  required_models: []
services:
  tailscale:
    required: true
    description: "Userspace Tailscale daemon providing the encrypted control-plane tunnel (Kit 1). Used as the fallback transport when LAN is unavailable."
    setup: "See kits/tailscale-userspace/kit.md — must be installed and authenticated before this kit."
  ssh:
    required: true
    description: "SSH key-based auth to the remote machine (Kit 2). The Hermes MCP server is launched via `ssh user@host <command>`."
    setup: "See kits/ssh-key-auth/kit.md — must have passwordless SSH access to the remote user before this kit."
environment:
  os: [macos]
  homebrew: false
  hermes_version: ">=0.1.0"
src:
  fileManifest: []
  # This kit is configuration-only — it modifies the active Hermes profile's
  # config.yaml to add an MCP server entry. No files are copied.
---

## Goal

Set up an **MCP (Model Context Protocol) server bridge** between two Hermes Agent instances over SSH. Once configured, the local Hermes session can invoke tools — send messages, read conversations, list contacts, and more — on the remote machine as if they were local tools. This is the foundation of a **multi-agent mesh** where one Hermes instance can control another.

## When to Use

- **Multi-machine setup** — you have Hermes on two machines (e.g., a MacBook and an always-on desktop) and want one agent to control the other
- **Remote messaging gateway** — the remote machine runs a messaging platform (Discord, Telegram, Slack, Matrix) and you want to interact with it from your local session
- **Agent delegation** — you're building an orchestrator/worker architecture and need the local Hermes to dispatch work to a remote Hermes
- **After Kit 1 + Kit 2** — this kit is step 3 in the standard sequence; run it after Tailscale userspace and SSH key auth are in place
- **Migrating to a new machine** — re-run this kit on the new machine to connect to the same remote

## Setup

### What you need

| Requirement | Details |
|-------------|---------|
| **Kit 1 — Tailscale** | Userspace Tailscale running on both machines, authenticated to the same tailnet. The remote machine must be routable via its Tailscale IP (`100.x.x.x`) or LAN IP. |
| **Kit 2 — SSH Key Auth** | Passwordless SSH access from local → remote user. Both the LAN IP and Tailscale IP must work for `ssh user@host echo OK`. |
| **Hermes Agent** | Installed on both machines. The **remote** machine must be able to run `hermes mcp serve --accept-hooks` from the command line. |
| **Active Hermes profile** | The profile you want to add the MCP server to (e.g., `team-manager`). The MCP server entry is profile-scoped. |

### What this kit creates / modifies

| Change | Location | Purpose |
|--------|----------|---------|
| MCP server config entry `mb14` | `~/.hermes/profiles/<profile>/config.yaml` → `mcp_servers.mb14` | Defines the SSH stdio transport and remote command for the MCP bridge. |
| MCP server enabled flag | Same config → `mcp_servers.mb14.enabled: true` | Activates the server so it starts on session load. |

No files are copied to disk — everything is a config change.

## Steps

### Step 1: Verify prerequisites

Before starting, confirm both prerequisite kits are working.

**Tailscale connectivity** (Kit 1):

```bash
tailscale --socket ~/.hermes/tailscale.sock status
```

You should see both machines in the output. The remote machine's status must show a green checkmark (connected) — a hyphen `-` means it's online but unreachable via direct connection (Tailscale DERP relay will still work).

**SSH key auth** (Kit 2):

```bash
# Test via LAN IP (fastest)
ssh asadpreuss-dodhy@192.168.1.200 "echo SSH OK from mb14"

# Test via Tailscale IP (fallback)
ssh asadpreuss-dodhy@100.97.232.91 "echo SSH OK via tailscale"
```

Both should print `SSH OK from mb14` / `SSH OK via tailscale` without prompting for a password.

If either fails, go back to Kit 1 or Kit 2 and resolve the issue before proceeding.

---

### Step 2: Check remote Hermes can serve MCP

SSH into the remote machine and verify the Hermes binary exists and can run the MCP serve command:

```bash
ssh asadpreuss-dodhy@192.168.1.200 "/Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes mcp serve --accept-hooks --help"
```

Expected output: the help text for the `mcp serve` subcommand (shows available flags like `--accept-hooks`, `--port`, etc.).

If this fails, check:
- Hermes Agent is installed on the remote machine
- The virtual environment path is correct (may differ on your setup — run `which hermes` or `ls ~/.hermes/hermes-agent/venv/bin/hermes`)
- The remote shell is loading the correct PATH or you're using the absolute path

---

### Step 3: Select or create the target profile

Decide which Hermes profile will contain the MCP server config. The profile must exist.

```bash
# List available profiles
ls ~/.hermes/profiles/
```

For this kit we use `team-manager`. If it doesn't exist, create it:

```bash
mkdir -p ~/.hermes/profiles/team-manager
```

The profile's config file lives at `~/.hermes/profiles/team-manager/config.yaml`. If it doesn't exist yet, Hermes will create it from defaults on first session start with that profile.

---

### Step 4: Add the MCP server configuration

Add the `mcp_servers` entry to the profile config. The exact method depends on whether the file already has an `mcp_servers:` section.

**Option A — Using `hermes config set`** (recommended if the config already exists):

```bash
# Add the SSH stdio MCP server entry
hermes config set mcp_servers.mb14.command ssh
hermes config set mcp_servers.mb14.args '["asadpreuss-dodhy@192.168.1.200", "/Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes", "mcp", "serve", "--accept-hooks"]'
```

Note: If using the Tailscale IP instead of LAN IP, replace `192.168.1.200` with `100.97.232.91`.

**Option B — Edit config.yaml directly**:

Open `~/.hermes/profiles/team-manager/config.yaml` and add or append to the `mcp_servers:` section:

```yaml
mcp_servers:
  mb14:
    command: ssh
    args:
      - asadpreuss-dodhy@192.168.1.200
      - /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes
      - mcp
      - serve
      - --accept-hooks
    enabled: true
```

If the file already has an `mcp_servers:` block (e.g., from a previous attempt), add `mb14:` as a nested entry under it. Be careful with YAML indentation — Hermes config is strict 2-space indentation.

---

### Step 5: Enable the MCP server

```bash
hermes config set mcp_servers.mb14.enabled true
```

Verify the entry was written correctly:

```bash
hermes config get mcp_servers.mb14
```

Expected output (truncated for readability):

```
command: ssh
args:
  - asadpreuss-dodhy@192.168.1.200
  - /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes
  - mcp
  - serve
  - --accept-hooks
enabled: true
```

If the output says `(not set)` or shows errors, re-check Step 4.

---

### Step 6: Reload MCP tools

You can either start a **new Hermes session** (the MCP server is loaded at session start) or, if you're already in a session, reload MCP tools dynamically:

```bash
# Inside a Hermes session:
/reload-mcp
```

This triggers a refresh: Hermes connects to each configured MCP server, negotiates capabilities, and registers the remote tools. For SSH stdio transports, this means an SSH connection is established each time.

To confirm the server connected, look for log output like:

```
[08:45:12] INFO     MCP server 'mb14' connected — 10 tools available
```

If you see `MCP server 'mb14' connection FAILED` or connection refused errors, check:
- The SSH connection works from the local terminal (Step 1)
- The remote Hermes binary path is correct (Step 2)
- The remote machine has Hermes running (it doesn't need to be in an active session, but the binary must be functional)
- Tailscale is still connected if using the Tailscale IP

---

### Step 7: Test the bridge is working

After `/reload-mcp` succeeds, the remote tools are available alongside local tools. Test them with a simple command:

```bash
# List available tools — look for tools prefixed with or sourced from mb14
hermes config get platforms
```

Or, inside a Hermes session, ask the agent to use a remote tool:

> "Check what messaging tools are available from mb14"

Then invoke one:

> "List the current conversations on mb14's messaging platform"

If the tools respond with data from the remote machine, the bridge is operational.

You can also verify the SSH transport is handling the connection by checking the remote machine's SSH logs or running a loopback test:

```bash
# From the local machine, simulate what Hermes does internally:
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ssh asadpreuss-dodhy@192.168.1.200 /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes mcp serve --accept-hooks
```

This sends a JSON-RPC `tools/list` request over SSH stdio. Expected output (truncated):

```json
{"jsonrpc":"2.0","result":{"tools":[{"name":"...","description":"...",...}]},"id":1}
```

If you get JSON back with a `tools` array, the bridge is fully operational at the protocol level.

---

### Step 8: (Optional) Add alternative connection path

For reliability, you can configure both IP addresses as separate MCP server entries:

```bash
# LAN path (mb14-lan)
hermes config set mcp_servers.mb14-lan.command ssh
hermes config set mcp_servers.mb14-lan.args '["asadpreuss-dodhy@192.168.1.200", "/Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes", "mcp", "serve", "--accept-hooks"]'
hermes config set mcp_servers.mb14-lan.enabled false

# Tailscale path (mb14-ts)
hermes config set mcp_servers.mb14-ts.command ssh
hermes config set mcp_servers.mb14-ts.args '["asadpreuss-dodhy@100.97.232.91", "/Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes", "mcp", "serve", "--accept-hooks"]'
hermes config set mcp_servers.mb14-ts.enabled false
```

Leave both disabled by default and enable one at a time when needed. If LAN is unreachable (different network), switch to the Tailscale entry.

## Constraints

- **MCP servers are profile-scoped** — the `mb14` entry only loads when you use the profile it was added to. If you want the bridge in multiple profiles, add the config to each one.
- **SSH stdio transport requires an active SSH session per tool call** — every MCP tool invocation opens a new SSH connection. This adds ~200–500 ms latency per call compared to the HTTP API transport.
- **The `--accept-hooks` flag** auto-approves shell hooks on the remote machine. Without it, the remote Hermes may prompt for approval of shell operations triggered by MCP tools.
- **Remote Hermes must be functional** but does not need to be in an active session or have a gateway running. The MCP server runs as a detached process.
- **The remote Hermes path is absolute** — virtual environment paths differ by setup. Verify the path with `which hermes` on the remote machine.
- **Only one SSH stdio MCP server per SSH user@host** — you cannot have two MCP server entries using the same SSH transport parameters (they'd conflict on the remote end). Use different entries for LAN vs. Tailscale and keep only one enabled.
- **`/reload-mcp` only works inside an active Hermes session** — it is a slash command, not a shell command. If you're not in a session, start a new one.

## Safety Notes

- **Full SSH access** — the SSH key used for this bridge provides complete shell access to the remote user account. Guard the private key (`~/.ssh/id_ed25519` or equivalent) carefully.
- **LAN vs. Tailscale** — the LAN path (`192.168.x.x`) is unencrypted at the network level within your local network. For sensitive operations or when on untrusted networks, use the Tailscale IP (`100.x.x.x`) which is WireGuard-encrypted end-to-end.
- **`--accept-hooks` risk** — this flag causes the remote Hermes to auto-approve all shell hooks. If a malicious tool call reaches the remote, it can execute arbitrary shell commands without approval. Consider running without `--accept-hooks` and relying on remote-side approvals.
- **Command injection via args** — SSH passes arguments as part of the command string. If any MCP argument contained shell metacharacters, it could inject commands on the remote. Hermes sanitizes tool call arguments, but be aware of the risk when forwarding user-provided data.
- **No built-in auth on the MCP transport** — the only authentication is the SSH connection itself. Anyone with the SSH key can connect. There is no additional MCP-level auth.
- **Tool visibility** — once connected, every Hermes tool on the remote machine that the MCP server exposes is visible and callable from the local agent. Review what tools the remote Hermes has enabled before exposing it via MCP.
- **Session restart required for config changes** — `hermes config set` changes to `mcp_servers` only take effect on the next session start (or `/reload-mcp`). They do NOT affect an already-running session until reloaded.

## Failures Overcome

1. **Tilde expansion fails in SSH arguments** — Passing `~/path` in SSH remote commands doesn't expand because the `~` is interpreted by the shell, not by SSH argument splitting. Always use absolute paths (e.g., `/Users/asadpreuss-dodhy/.hermes/...` instead of `~/.hermes/...`).

2. **Virtual environment resolution** — `hermes` is often aliased or in PATH via a virtual environment activation script. When SSH runs a command non-interactively, the PATH may not include the virtual environment. Use the full absolute path to the hermetic binary (`/path/to/venv/bin/hermes`).

3. **`/reload-mcp` fails silently on first attempt** — If the config is malformed (bad YAML, wrong indentation) or the SSH connection times out, `/reload-mcp` reports failure. Check `~/.hermes/logs/` for the MCP connection error details. A common cause is Tailscale having rotated its socket path — verify `tailscale --socket ~/.hermes/tailscale.sock status` works.

4. **MCP server enabled but not loaded** — Setting `enabled: true` in the config is not enough; the session must be restarted or `/reload-mcp` must be called. If you just edited config.yaml, the running session won't pick it up.

5. **SSH host key verification** — The first SSH connection to a new IP address prompts for host key confirmation. Run `ssh -o StrictHostKeyChecking=accept-new asadpreuss-dodhy@192.168.1.200 "echo OK"` once to accept the host key before Hermes tries to connect via MCP (Hermes may not handle the interactive prompt well over stdio).

6. **Tailscale IP vs. LAN IP mismatch** — If the remote machine changes networks, the LAN IP breaks but the Tailscale IP still works. Configure both and switch when needed (Step 8).

## Validation

After completing all steps, this checklist confirms success:

- [ ] `tailscale --socket ~/.hermes/tailscale.sock status` shows both machines connected
- [ ] `ssh asadpreuss-dodhy@192.168.1.200 "echo OK"` returns without password prompt
- [ ] Remote Hermes binary is reachable: `ssh ... /path/to/hermes mcp serve --help` returns help text
- [ ] `hermes config get mcp_servers.mb14.command` returns `ssh`
- [ ] `hermes config get mcp_servers.mb14.enabled` returns `true`
- [ ] MCP server args contain the correct remote user, host/IP, and absolute path to remote Hermes binary
- [ ] `/reload-mcp` (or new session) shows `MCP server 'mb14' connected` in logs
- [ ] The remote machine's tools appear in the local agent's tool list
- [ ] An MCP tool call (e.g., list conversations) returns data from the remote machine
- [ ] JSON-RPC `tools/list` over SSH stdio returns a valid tool list (optional protocol-level verification)
