#!/bin/bash
# Caddy reverse proxy config — used for remote/dashboard access to Hermes
# The Caddyfile contains domain, TLS, and routing rules.
set -euo pipefail

[ -f "$HOME/.hermes/caddy/Caddyfile" ] && echo "$HOME/.hermes/caddy/Caddyfile"
