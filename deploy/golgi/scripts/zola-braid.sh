#!/bin/bash
# zola-braid.sh — incremental build gate for sporePrint
#
# The braid pattern: only build when the source actually changed.
# Track last-built commit. Skip if HEAD is the same.
# Like epitope classification: 1D (trajectory) not 0D (snapshot).
#
# eastgate + northgate push → forgejo gets commit → cascade pulls →
# braid detects change → zola builds → atomic swap → done.
# No change? No build. 2 minutes saved, 260MB RAM saved.

set -euo pipefail

SITE=/opt/ecoPrimals/sporePrint
STATE=/run/membrane/zola-last-built
LOG=/var/log/membrane/zola-braid.log

cd "$SITE"

# What commit are we at now?
HEAD=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# What did we last build?
LAST=$(cat "$STATE" 2>/dev/null || echo "none")

# Same commit? Skip.
if [ "$HEAD" = "$LAST" ]; then
    echo "[$(date -Is)] braid: HEAD=$HEAD same as last build — SKIP" >> "$LOG"
    exit 0
fi

# What changed between last build and now?
if [ "$LAST" != "none" ] && git cat-file -t "$LAST" >/dev/null 2>&1; then
    CHANGED=$(git diff --name-only "$LAST" "$HEAD" 2>/dev/null || echo "unknown")
    CHANGED_COUNT=$(echo "$CHANGED" | grep -c . || true)
    echo "[$(date -Is)] braid: $CHANGED_COUNT files changed ($LAST → $HEAD)" >> "$LOG"
    echo "$CHANGED" >> "$LOG"
else
    CHANGED_COUNT="all"
    echo "[$(date -Is)] braid: first build or unknown previous state" >> "$LOG"
fi

# Check if ONLY static files changed (no zola rebuild needed)
if [ "$CHANGED_COUNT" != "all" ]; then
    NEEDS_REBUILD=0
    while IFS= read -r f; do
        case "$f" in
            static/*) ;; # static files just get copied, no rebuild needed
            *) NEEDS_REBUILD=1; break ;;
        esac
    done <<< "$CHANGED"

    if [ "$NEEDS_REBUILD" = "0" ] && [ "$CHANGED_COUNT" -gt 0 ]; then
        echo "[$(date -Is)] braid: only static files changed — rsync, skip zola" >> "$LOG"
        rsync -a static/ public/
        echo "$HEAD" > "$STATE"
        exit 0
    fi
fi

# Build needed. Run zola with atomic swap.
echo "[$(date -Is)] braid: BUILDING ($CHANGED_COUNT files changed)" >> "$LOG"

rm -rf public-next
if ZOLA_BRAID_AUTHORIZED=1 timeout 180 zola build -o public-next --force >> "$LOG" 2>&1; then
    # Atomic swap
    mv public public-old 2>/dev/null || true
    mv public-next public
    rm -rf public-old
    echo "$HEAD" > "$STATE"
    echo "[$(date -Is)] braid: BUILD COMPLETE — atomic swap done" >> "$LOG"
else
    echo "[$(date -Is)] braid: BUILD FAILED" >> "$LOG"
    rm -rf public-next 2>/dev/null
    exit 1
fi
