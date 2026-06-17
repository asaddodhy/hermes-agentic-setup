# Tailscale Userspace Mode for Hermes Agent Mesh

Set up Tailscale in userspace (no-root, CLI-only) mode on macOS for secure cross-machine Hermes agent networking.

> **Who this is for:** Hermes Agent users who need to connect instances across multiple machines over an encrypted VPN mesh.
> **What you get:** A running Tailscale daemon in userspace mode with a custom unix socket under `~/.hermes/`, authenticated to your tailnet, ready for SSH, MCP, and API Server traffic between machines.
> **Time to install:** ~10 minutes (including browser authentication)

## Prerequisites

- macOS (Apple Silicon or Intel)
- Homebrew installed
- Hermes Agent (any profile)
- Tailscale account (free tier)

## What's in this kit

```
kits/tailscale-userspace/
├── kit.md                              # This workflow
├── README.md                           # This page
└── src/
    ├── io.tailscale.userspace.plist    # Launchd plist for auto-starting tailscaled
    └── tailscale-helper.sh             # Shell helper aliases for daily use
```

## Quick Start

```bash
# 1. Install Tailscale
brew install tailscale

# 2. Start the daemon in userspace mode
/opt/homebrew/opt/tailscale/bin/tailscaled \
  --tun=userspace-networking \
  --state=$HOME/.hermes/tailscale-state.json \
  --socket=$HOME/.hermes/tailscale.sock

# 3. Authenticate (open the URL in browser)
tailscale --socket $HOME/.hermes/tailscale.sock up

# 4. Verify
tailscale --socket $HOME/.hermes/tailscale.sock status
```

## Kits in this repo

| Kit | Purpose |
|-----|---------|
| **tailscale-userspace** | VPN mesh — Tailscale in userspace mode |
| ssh-key-auth | Passwordless SSH between machines |
| hermes-mcp-bridge | MCP server/client for tool delegation |
| hermes-api-server | OpenAI-compatible API gateway |
| security-hardening | Tirith rules, smart approvals, credential protection |
