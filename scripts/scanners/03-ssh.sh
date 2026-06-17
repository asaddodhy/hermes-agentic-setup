#!/bin/bash
# SSH config and key files
set -euo pipefail

[ -f "$HOME/.ssh/config" ]          && echo "$HOME/.ssh/config"
[ -f "$HOME/.ssh/id_ed25519" ]      && echo "$HOME/.ssh/id_ed25519"
[ -f "$HOME/.ssh/id_ed25519.pub" ]  && echo "$HOME/.ssh/id_ed25519.pub"
[ -f "$HOME/.ssh/known_hosts" ]     && echo "$HOME/.ssh/known_hosts"
