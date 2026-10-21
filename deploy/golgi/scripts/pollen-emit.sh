#!/bin/bash
# pollen-emit.sh — proton fires after build
# Called by tuebor-pull-build.sh / detroit-pull-build.sh after successful zola build
# Notifies search engines via IndexNow (Bing)

COMMIT="${1:-unknown}"
SITE="${2:-tuebor}"
LOG=/var/log/membrane/tuebor-build.log
LIVE=/opt/membrane/live-terminal
INDEXNOW_KEY="0CB4A351F4F113D99E0E1970B2AA29A6"

# Map site to domain
case "$SITE" in
    tuebor)  DOMAIN="tuebor.primals.eco" ;;
    detroit) DOMAIN="detroit.primals.eco" ;;
    hud)     DOMAIN="hud.primals.eco" ;;
    *)       DOMAIN="${SITE}.primals.eco" ;;
esac

# Ping Bing IndexNow (no keyLocation — Bing finds {key}.txt automatically)
curl -sf --connect-timeout 5 --max-time 10 \
    "https://www.bing.com/indexnow?url=https://${DOMAIN}/sitemap.xml&key=$INDEXNOW_KEY" \
    >/dev/null 2>&1 && echo "[$(date -Is)] $SITE: PROTON — Bing IndexNow pinged" >> "$LOG" || true

# Update proton-pulse feed
python3 -c "
import json, time, os
LIVE = os.environ.get(LIVE, /opt/membrane/live-terminal)
try:
    p = json.load(open(LIVE + /proton-pulse.json))
except Exception:
    p = {events: []}
now = time.strftime(%Y-%m-%dT%H:%M:%SZ, time.gmtime())
commit = [:8]
site = 
p[events] = p.get(events, [])[-20:]
p[events].append({type: auto_pollen, timestamp: now, source: site + -build, commit: commit})
p[perturbation] = 0.05
p[last_event] = auto_pollen:  + site +  build  + commit
p[last_perturbation] = {event: auto_pollen, ts: now, commit: commit, site: site}
json.dump(p, open(LIVE + /proton-pulse.json, w), separators=(,, :))
" 2>/dev/null || true
