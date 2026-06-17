#!/bin/bash
# Tailscale state and socket
set -euo pipefail

[ -f "$HOME/.hermes/tailscale-state.json" ] && echo "$HOME/.hermes/tailscale-state.json"
[ -S "$HOME/.hermes/tailscale.sock" ]       && echo "$HOME/.hermes/tailscale.sock"
