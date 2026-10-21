#!/bin/bash
# tuebor-pull-build.sh — pull from GitHub + rebuild tuebor Zola site
# Signal: GitHub has articles → pull → build → publish
set -euo pipefail

REPO=/opt/ecoPrimals/tuebor-repo
SITE=$REPO/site
STATE=/run/membrane/tuebor-last-built
LOG=/var/log/membrane/tuebor-build.log

cd "$REPO"

# CANARY: check for dirty tree BEFORE anything else
DIRTY=$(git status --porcelain -- site/public/ 2>/dev/null | wc -l)
if [ "$DIRTY" -gt 0 ]; then
    echo "[$(date -Is)] tuebor: CANARY — $DIRTY dirty files in site/public/, cleaning" >> "$LOG"
    git checkout -- site/public/ 2>/dev/null || true
fi

# northGate owns github. github first, then forgejo.
for REMOTE_NAME in github origin; do
    if git fetch "$REMOTE_NAME" 2>>"$LOG"; then
        LOCAL=$(git rev-parse HEAD)
        REMOTE_HEAD=$(git rev-parse "$REMOTE_NAME/main" 2>/dev/null || echo "unknown")
        
        if [ "$LOCAL" != "$REMOTE_HEAD" ] && [ "$REMOTE_HEAD" != "unknown" ]; then
            if git merge-base --is-ancestor "$LOCAL" "$REMOTE_HEAD" 2>/dev/null; then
                echo "[$(date -Is)] tuebor: new commits on $REMOTE_NAME ($LOCAL → $REMOTE_HEAD)" >> "$LOG"
                git merge "$REMOTE_NAME/main" --ff-only >> "$LOG" 2>&1 || {
                    echo "[$(date -Is)] tuebor: merge from $REMOTE_NAME failed — CANARY ALERT" >> "$LOG"
                    continue
                }
            fi
        fi
    fi
done

# Check if build is needed
cd "$SITE"
HEAD=$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo "unknown")
LAST=$(cat "$STATE" 2>/dev/null || echo "none")

if [ "$HEAD" = "$LAST" ]; then
    exit 0
fi

echo "[$(date -Is)] tuebor: BUILDING ($LAST → $HEAD)" >> "$LOG"

rm -rf public-next
if ZOLA_BRAID_AUTHORIZED=1 timeout 180 /usr/local/bin/zola-real build -o public-next --force >> "$LOG" 2>&1; then
    mv public public-old 2>/dev/null || true
    mv public-next public
    rm -rf public-old
    echo "$HEAD" > "$STATE"
    echo "[$(date -Is)] tuebor: BUILD COMPLETE" >> "$LOG"
    /opt/membrane/pollen-emit.sh "$HEAD" tuebor &
else
    echo "[$(date -Is)] tuebor: BUILD FAILED — CANARY ALERT" >> "$LOG"
    rm -rf public-next 2>/dev/null
    exit 1
fi

# ── PROTON FIRES: notify search engines of new content ──
# This is the pollen burst — content radiates outward
INDEXNOW_KEY="0CB4A351F4F113D99E0E1970B2AA29A6"
SITEMAP_URL="https://tuebor.primals.eco/sitemap.xml"

# Ping Bing IndexNow with sitemap
curl -sf --connect-timeout 5 --max-time 10 \
    "https://www.bing.com/indexnow?url=$SITEMAP_URL&key=$INDEXNOW_KEY&keyLocation=https://tuebor.primals.eco/indexnow-key.txt" \
    >/dev/null 2>&1 && echo "[$(date -Is)] tuebor: PROTON — Bing IndexNow pinged" >> "$LOG" || true

# Update proton-pulse feed
python3 -c "
import json, time
LIVE = /opt/membrane/live-terminal
try:
    p = json.load(open(LIVE + /proton-pulse.json))
except: p = {events: []}
now = time.strftime(%Y-%m-%dT%H:%M:%SZ, time.gmtime())
p[events].append({type: auto_pollen, timestamp: now, source: tuebor-build})
p[perturbation] = 0.05
p[last_event] = auto_pollen: tuebor build  + [:8]
p[last_perturbation] = {event: auto_pollen, ts: now, commit: [:8]}
json.dump(p, open(LIVE + /proton-pulse.json, w), separators=(,, :))
" 2>/dev/null || true
