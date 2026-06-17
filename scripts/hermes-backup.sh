#!/bin/bash
# Hermes Repo Backup Script
# Invoked by the hermes-repo-backup skill, or standalone.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARBALL_NAME="hermes-backup-${TIMESTAMP}.tar.gz"

# --- Determine backup destination ---
NETWORK_DRIVE="/Volumes/Seagate_Backup_Plus_Drive/NAS/Hermes Backup"
LOCAL_FALLBACK="$HOME/Documents/Hermes Backup"

if [ -d "$NETWORK_DRIVE" ]; then
    DEST="$NETWORK_DRIVE"
    DRIVE_STATUS="connected"
else
    DEST="$LOCAL_FALLBACK"
    DRIVE_STATUS="disconnected"
    mkdir -p "$DEST"
fi

TARBALL_PATH="$DEST/$TARBALL_NAME"

echo "📦 Hermes Repo Backup"
echo "   Timestamp: $TIMESTAMP"
echo "   Repo:      $REPO_DIR"
echo "   Drive:     $DRIVE_STATUS ($DEST)"
echo ""

# --- Step 1: Verify repo structure ---
echo "🔍 Verifying repo structure..."
KIT_COUNT=0
MISSING_KITS=()
for kit_dir in "$REPO_DIR/kits/"*/; do
    kname=$(basename "$kit_dir")
    if [ -f "$kit_dir/kit.md" ]; then
        KIT_COUNT=$((KIT_COUNT + 1))
    else
        MISSING_KITS+=("$kname")
    fi
done

if [ ${#MISSING_KITS[@]} -gt 0 ]; then
    echo "⚠️  Warning: ${#MISSING_KITS[@]} kit(s) missing kit.md:"
    for k in "${MISSING_KITS[@]}"; do echo "     - $k"; done
else
    echo "✅ All $KIT_COUNT kits have kit.md files"
fi

# Check README exists
if [ -f "$REPO_DIR/README.md" ]; then
    echo "✅ README.md present"
else
    echo "⚠️  README.md missing"
fi

# Check MASTER-RESTORATION.md exists
if [ -f "$REPO_DIR/MASTER-RESTORATION.md" ]; then
    echo "✅ MASTER-RESTORATION.md present"
else
    echo "⚠️  MASTER-RESTORATION.md missing"
fi

echo ""

# --- Step 2: Create tarball ---
echo "🗜️  Creating tarball..."

# Files and dirs to backup
BACKUP_PATHS=(
    "$HOME/.hermes/config.yaml"
    "$HOME/.hermes/SOUL.md"
    "$HOME/.hermes/auth.json"
    "$HOME/.hermes/.env"
    "$HOME/.hermes/memories/"
    "$HOME/.hermes/skills/"
    "$HOME/.hermes/kanban.db"
    "$HOME/.hermes/tailscale-state.json"
    "$HOME/.hermes/profiles/"
    "$HOME/.tirith/"
    "$HOME/.ssh/config"
    "$HOME/.ssh/id_ed25519"
    "$HOME/.ssh/id_ed25519.pub"
    "$HOME/novel-os/"
    "$REPO_DIR/"
)

# Filter to existing paths
EXISTING_PATHS=()
for p in "${BACKUP_PATHS[@]}"; do
    # Use eval to handle ~ expansion
    eval expanded="$p"
    if [ -e "$expanded" ]; then
        EXISTING_PATHS+=("$expanded")
    else
        echo "   (skipping missing: $p)"
    fi
done

tar czf "$TARBALL_PATH" "${EXISTING_PATHS[@]}" 2>/dev/null

# Verify tarball
if [ -f "$TARBALL_PATH" ]; then
    SIZE=$(du -sh "$TARBALL_PATH" | cut -f1)
    FILE_COUNT=$(tar tzf "$TARBALL_PATH" 2>/dev/null | wc -l | xargs)
    echo "✅ Created: $TARBALL_PATH"
    echo "   Size:    $SIZE"
    echo "   Files:   $FILE_COUNT"
else
    echo "❌ Failed to create tarball"
    exit 1
fi

echo ""

# --- Step 3: Report ---
echo "📋 Backup Summary"
echo "   Destination:  $DEST"
echo "   Tarball:      $TARBALL_NAME"
echo "   Kit count:    $KIT_COUNT"
if [ "$DRIVE_STATUS" = "disconnected" ]; then
    echo ""
    echo "⚠️  NOTE: Network backup drive was NOT connected."
    echo "   Tarball saved to local fallback: $LOCAL_FALLBACK"
    echo "   Connect your Seagate drive and run this script again to copy to the network location."
fi

echo ""
echo "✅ Backup complete."
