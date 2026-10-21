#!/bin/bash
# hud-pull.sh — pull HUD from Forgejo + deploy
# The HUD is static files — no zola build needed. Just pull.
set -euo pipefail

REPO=/opt/ecoPrimals/hud
STATE=/run/membrane/hud-last-pulled
LOG=/var/log/membrane/hud-pull.log

cd "$REPO"

# Live HUD is often scp'd. Do not clobber a dirty public tree.
DIRTY=$(git status --porcelain -- site/public/ 2>/dev/null | wc -l)
if [ "$DIRTY" -gt 0 ]; then
    echo "[$(date -Is)] hud: SKIP pull — $DIRTY dirty public files (live scp). northGate does not overwrite the glass." >> "$LOG"
    exit 0
fi

git fetch origin 2>>"$LOG" || exit 0

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "unknown")

if [ "$LOCAL" = "$REMOTE" ] || [ "$REMOTE" = "unknown" ]; then
    exit 0
fi

if git merge-base --is-ancestor "$LOCAL" "$REMOTE" 2>/dev/null; then
    echo "[$(date -Is)] hud: pulling ($LOCAL → $REMOTE)" >> "$LOG"
    git merge origin/main --ff-only >> "$LOG" 2>&1 || {
        echo "[$(date -Is)] hud: merge failed" >> "$LOG"
        exit 1
    }
    echo "$REMOTE" > "$STATE"
    echo "[$(date -Is)] hud: DEPLOYED" >> "$LOG"
fi
