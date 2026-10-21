#!/bin/bash
# sensation-ping.sh — receives push notifications, triggers pulls
# Called by: Forgejo post-receive hook (via SSH from eastgate)
# Usage: sensation-ping.sh <repo-name>
REPO="${1:-unknown}"
LOG=/var/log/membrane/sensation.log
TS=$(date -Is)

echo "[$TS] SENSATION: push detected on $REPO" >> "$LOG"

case "$REPO" in
    tuebor|ecoPrimals/tuebor)
        echo "[$TS] → triggering tuebor-pull-build" >> "$LOG"
        /opt/membrane/tuebor-pull-build.sh >> "$LOG" 2>&1 &
        ;;
    detroit|publicRecord/detroit)
        echo "[$TS] → triggering detroit-pull-build" >> "$LOG"
        /opt/membrane/detroit-pull-build.sh >> "$LOG" 2>&1 &
        ;;
    hud|ecoPrimals/hud)
        echo "[$TS] → triggering hud-pull" >> "$LOG"
        /opt/membrane/hud-pull.sh >> "$LOG" 2>&1 &
        ;;
    *)
        echo "[$TS] → no auto-build for $REPO (logged only)" >> "$LOG"
        ;;
esac

# Write to sensation feed
python3 -c "
import json, time
feed_path = \"/opt/membrane/live-terminal/sensation.json\"
try:
    feed = json.load(open(feed_path))
except:
    feed = {\"type\": \"sensation\", \"events\": [], \"total\": 0}

feed[\"events\"] = feed.get(\"events\", [])[-19:]  # keep last 20
feed[\"events\"].append({
    \"ts\": \"$TS\",
    \"repo\": \"$REPO\",
    \"source\": \"forgejo-push\"
})
feed[\"total\"] = feed.get(\"total\", 0) + 1
feed[\"last\"] = \"$TS\"
json.dump(feed, open(feed_path, \"w\"), indent=2)
" 2>>"$LOG"

echo "FELT"
