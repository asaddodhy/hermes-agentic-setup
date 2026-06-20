#!/bin/bash
# Hermes WebUI installation — .env config (contains HERMES_WEBUI_PASSWORD)
# The repo itself can be re-cloned; only the .env is non-reproducible.
set -euo pipefail

[ -f "$HOME/hermes-webui/.env" ] && echo "$HOME/hermes-webui/.env"
