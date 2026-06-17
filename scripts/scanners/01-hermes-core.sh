#!/bin/bash
# Core Hermes config files, state, and secrets
set -euo pipefail

[ -f "$HOME/.hermes/config.yaml" ]           && echo "$HOME/.hermes/config.yaml"
[ -f "$HOME/.hermes/SOUL.md" ]               && echo "$HOME/.hermes/SOUL.md"
[ -f "$HOME/.hermes/auth.json" ]             && echo "$HOME/.hermes/auth.json"
[ -f "$HOME/.hermes/.env" ]                  && echo "$HOME/.hermes/.env"
[ -d "$HOME/.hermes/memories/" ]             && echo "$HOME/.hermes/memories/"
[ -d "$HOME/.hermes/skills/" ]               && echo "$HOME/.hermes/skills/"
[ -f "$HOME/.hermes/kanban.db" ]             && echo "$HOME/.hermes/kanban.db"
[ -f "$HOME/.hermes/state.db" ]              && echo "$HOME/.hermes/state.db"
