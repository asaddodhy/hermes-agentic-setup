#!/bin/bash
# Tailscale Userspace Helper — source this in your shell init (.zshrc / .bashrc)
#
# Provides:
#   ts    — tailscale alias that includes the custom socket path
#   tsd   — tailscaled daemon start function
#   ts-up — authenticate and bring Tailscale up
#   ts-st — status shortcut
#
# Usage:
#   source ~/.hermes/bin/tailscale-helper.sh

export TAILSCALE_SOCKET="${HOME}/.hermes/tailscale.sock"
export TAILSCALE_STATE="${HOME}/.hermes/tailscale-state.json"

ts() {
  /opt/homebrew/bin/tailscale --socket "$TAILSCALE_SOCKET" "$@"
}

ts-up() {
  echo "=== Getting login URL (non-blocking) ==="
  ts status
  echo
  echo "=== Starting 'up' in background — open the URL above ==="
  ts up &
  TS_UP_PID=$!
  echo "(PID $TS_UP_PID — will exit once auth completes)"
}

ts-st() {
  ts status
}

tsd() {
  echo "Starting tailscaled in userspace mode..."
  nohup /opt/homebrew/opt/tailscale/bin/tailscaled \
    --tun=userspace-networking \
    --state="$TAILSCALE_STATE" \
    --socket="$TAILSCALE_SOCKET" \
    > /tmp/tailscaled.log 2>&1 &
  echo "tailscaled started (PID $!)"
  echo "Log: /tmp/tailscaled.log"
}
