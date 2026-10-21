#!/bin/bash
# canary.sh — publishing pipeline health monitor
# Detects: dirty git trees, stale locks, HEAD!=built, failed merges
# Writes to /opt/membrane/feeds/canary.json
set -euo pipefail

FEED=/opt/membrane/feeds/canary.json
NOW=$(date -Is)
ALERTS=""
STATUS="green"

mkdir -p /opt/membrane/feeds

add_alert() {
    local site="$1" issue="$2"
    ALERTS="${ALERTS}${ALERTS:+, }{\"site\":\"${site}\",\"issue\":\"${issue}\",\"ts\":\"${NOW}\"}"
    STATUS="red"
}

# --- TUEBOR ---
if [ -d /opt/ecoPrimals/tuebor-repo/.git ]; then
    cd /opt/ecoPrimals/tuebor-repo
    DIRTY=$(git status --porcelain -- site/public/ 2>/dev/null | wc -l || echo 0)
    [ "$DIRTY" -gt 0 ] && add_alert "tuebor" "${DIRTY} dirty files in site/public/"
    
    HEAD=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    BUILT=$(cat /run/membrane/tuebor-last-built 2>/dev/null || echo "none")
    [ "$HEAD" != "$BUILT" ] && add_alert "tuebor" "HEAD ${HEAD:0:8} != built ${BUILT:0:8}"
    
    ORIGIN=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
    [ "$HEAD" != "$ORIGIN" ] && [ "$ORIGIN" != "unknown" ] && add_alert "tuebor" "HEAD ${HEAD:0:8} behind origin ${ORIGIN:0:8}"
fi

# --- DETROIT ---
if [ -d /opt/ecoPrimals/detroit/worktree/.git ]; then
    cd /opt/ecoPrimals/detroit/worktree
    DIRTY=$(git status --porcelain -- site/public/ 2>/dev/null | wc -l || echo 0)
    [ "$DIRTY" -gt 0 ] && add_alert "detroit" "${DIRTY} dirty files in site/public/"
    
    HEAD=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    BUILT=$(cat /run/membrane/detroit-last-built 2>/dev/null || echo "none")
    [ "$HEAD" != "$BUILT" ] && add_alert "detroit" "HEAD ${HEAD:0:8} != built ${BUILT:0:8}"
fi

# --- HUD ---
if [ -d /opt/ecoPrimals/hud/.git ]; then
    cd /opt/ecoPrimals/hud
    HEAD=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    ORIGIN=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
    [ "$HEAD" != "$ORIGIN" ] && [ "$ORIGIN" != "unknown" ] && add_alert "hud" "HEAD ${HEAD:0:8} behind origin ${ORIGIN:0:8}"
fi

# --- STALE LOCKS ---
STALE_LOCKS=0
for lockfile in /tmp/membrane-*.lock /run/membrane/*.lock; do
    [ -f "$lockfile" ] || continue
    AGE=$(( $(date +%s) - $(stat -c %Y "$lockfile" 2>/dev/null || echo "$(date +%s)") ))
    if [ "$AGE" -gt 7200 ]; then
        STALE_LOCKS=$((STALE_LOCKS + 1))
        add_alert "locks" "stale lock: $(basename "$lockfile") age ${AGE}s"
    fi
done

# --- CRON HEALTH ---
CRON_PROCS=$(pgrep -cf "membrane-pulse" 2>/dev/null || true)
CRON_PROCS=${CRON_PROCS:-0}
[ "$CRON_PROCS" -gt 4 ] 2>/dev/null && add_alert "cron" "${CRON_PROCS} membrane-pulse procs"

# --- Gather state ---
T_HEAD=$(cd /opt/ecoPrimals/tuebor-repo 2>/dev/null && git rev-parse --short HEAD 2>/dev/null || echo "na")
T_BUILT=$(head -c 12 /run/membrane/tuebor-last-built 2>/dev/null || echo "na")
D_HEAD=$(cd /opt/ecoPrimals/detroit/worktree 2>/dev/null && git rev-parse --short HEAD 2>/dev/null || echo "na")
D_BUILT=$(head -c 12 /run/membrane/detroit-last-built 2>/dev/null || echo "na")
H_HEAD=$(cd /opt/ecoPrimals/hud 2>/dev/null && git rev-parse --short HEAD 2>/dev/null || echo "na")
ALERT_COUNT=0; [ -n "$ALERTS" ] && ALERT_COUNT=$(echo "$ALERTS" | grep -co issue || true)

# Write feed
cat > "$FEED" << EOF
{
  "type": "canary",
  "status": "$STATUS",
  "ts": "$NOW",
  "alerts": [${ALERTS}],
  "checks": {
    "tuebor_head": "$T_HEAD",
    "tuebor_built": "$T_BUILT",
    "detroit_head": "$D_HEAD",
    "detroit_built": "$D_BUILT",
    "hud_head": "$H_HEAD",
    "stale_locks": $STALE_LOCKS,
    "cron_procs": ${CRON_PROCS:-0}
  }
}
EOF

echo "[$NOW] canary: $STATUS ($ALERT_COUNT alerts)" >> /var/log/membrane/canary.log
[ "$STATUS" = "red" ] && echo "[$NOW] CANARY RED: $ALERTS" >> /var/log/membrane/canary.log
exit 0
