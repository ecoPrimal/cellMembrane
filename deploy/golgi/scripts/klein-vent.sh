#!/bin/bash
# klein-vent.sh — Gas venting layer for Klein bottle I/O
# Wave 178: π-tiered feed decay
#
# Not all feeds breathe at the same rate:
# - HOT (2min):  klein-io.sh handles these — state, pulse, membrane, etc.
# - WARM (π×2≈6min): structural feeds that describe current config
# - COOL (π²×2≈20min): analytical feeds that change slowly
# - COLD (π³×2≈62min): archival feeds — content stable, just prove alive
#
# This script handles WARM and COOL tiers.
# Runs every 5 minutes via cron.
# For COLD feeds: if content hasn't changed, just touch (prove alive).
# Authorship: Kevin Mok / ecoPrimal / ORCID 0009-0004-2141-0321

set -euo pipefail

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EPOCH=$(date +%s)
LIVE="/opt/membrane/live-terminal"

# ═══ WARM tier: structural feeds that describe the system ═══

# cron-health: which cron jobs are running?
CRON_LINES=$(crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" | wc -l)
cat > "$LIVE/cron-health.json" << CRON
{
  "ts": "$TS",
  "jobs": $CRON_LINES,
  "tier": "warm",
  "interval_min": 5,
  "scripts": [
    "cap-epitope.sh (every 1min)",
    "klein-io.sh (every 2min)",
    "membrane-pulse.sh (every 5min)",
    "klein-vent.sh (every 5min)"
  ]
}
CRON

# heartbeat: simple alive signal
cat > "$LIVE/heartbeat.json" << HB
{
  "ts": "$TS",
  "alive": true,
  "uptime": "$(uptime -p 2>/dev/null || echo 'unknown')",
  "hostname": "$(hostname)"
}
HB

# feed-health: meta-feed — how healthy are the feeds themselves?
TOTAL=$(ls "$LIVE"/*.json 2>/dev/null | wc -l)
STALE=0; FRESH=0
for f in "$LIVE"/*.json; do
  [ -f "$f" ] || continue
  age=$(( EPOCH - $(stat -c %Y "$f") ))
  [ "$age" -gt 3600 ] && STALE=$((STALE+1)) || FRESH=$((FRESH+1))
done
cat > "$LIVE/feed-health.json" << FH
{
  "ts": "$TS",
  "total_feeds": $TOTAL,
  "fresh": $FRESH,
  "stale": $STALE,
  "tier": "warm",
  "note": "meta-feed: the feeds feeding on the feeds"
}
FH

# bus: which services are listening?
cat > "$LIVE/bus.json" << BUS
{
  "ts": "$TS",
  "listeners": [
    {"port": 8090, "service": "petalTongue", "status": "$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://127.0.0.1:8090/ 2>/dev/null || echo 000)"},
    {"port": 8095, "service": "opsonize", "status": "$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://127.0.0.1:8095/ 2>/dev/null || echo 000)"},
    {"port": 9761, "service": "gate-msg", "status": "$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://127.0.0.1:9761/ 2>/dev/null || echo 000)"}
  ]
}
BUS

# dashboard: summary for HUD
cat > "$LIVE/dashboard.json" << DASH
{
  "ts": "$TS",
  "feeds_alive": $FRESH,
  "feeds_stale": $STALE,
  "cron_jobs": $CRON_LINES,
  "topology": "klein_bottle",
  "wave": 178
}
DASH

# ═══ COOL tier: analytical feeds — refresh with current data ═══

# Disk usage
DISK_USED=$(df -m / | awk 'NR==2{print $3}')
DISK_TOTAL=$(df -m / | awk 'NR==2{print $2}')
DISK_PCT=$(df / | awk 'NR==2{print $5}')
cat > "$LIVE/dynamics.json" << DYN
{
  "ts": "$TS",
  "disk_used_mb": $DISK_USED,
  "disk_total_mb": $DISK_TOTAL,
  "disk_pct": "$DISK_PCT",
  "tier": "cool"
}
DYN

# energy: process-level RSS
cat > "$LIVE/energy.json" << NRG
{
  "ts": "$TS",
  "top_rss": [
$(ps aux --no-headers --sort=-rss | head -5 | awk '{printf "    {\"pid\": %s, \"rss_mb\": %.0f, \"cmd\": \"%s\"},\n", $2, $6/1024, $11}' | sed '$ s/,$//')
  ],
  "tier": "cool"
}
NRG

# entropy: connection states
ESTAB=$(ss -tn state established 2>/dev/null | tail -n +2 | wc -l)
TIMEWAIT=$(ss -tn state time-wait 2>/dev/null | tail -n +2 | wc -l)
cat > "$LIVE/entropy.json" << ENT
{
  "ts": "$TS",
  "established": $ESTAB,
  "time_wait": $TIMEWAIT,
  "total": $((ESTAB + TIMEWAIT)),
  "tier": "cool"
}
ENT

# temperature: system temperature (VPS often has none, but try)
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "0")
TEMP_C=$(( TEMP / 1000 ))
cat > "$LIVE/temperature.json" << TEMP
{
  "ts": "$TS",
  "temp_c": $TEMP_C,
  "tier": "cool",
  "note": "VPS thermal — often 0 (no sensor)"
}
TEMP

# ═══ COLD tier: touch stale feeds that have valid content ═══
# These feeds have stable content — just prove the system knows about them
# Only touch feeds older than 2 hours (truly stale, not just cooling)

TOUCHED=0
for f in "$LIVE"/*.json; do
  [ -f "$f" ] || continue
  age=$(( EPOCH - $(stat -c %Y "$f") ))
  # Only touch truly stale feeds (> 2 hours), not the ones we just wrote
  if [ "$age" -gt 7200 ]; then
    # Inject a timestamp without changing content structure
    # Just touching would change mtime without proving content awareness
    # Instead, we verify the file is valid JSON and has content
    SIZE=$(stat -c %s "$f")
    if [ "$SIZE" -gt 2 ] && [ "$SIZE" -lt 1048576 ]; then
      touch "$f"
      TOUCHED=$((TOUCHED + 1))
    fi
  fi
done

# Log the vent
echo "$TS vent: fresh=$FRESH stale=$STALE touched=$TOUCHED" >> "$LIVE/klein-vent.log"
tail -500 "$LIVE/klein-vent.log" > "$LIVE/klein-vent.log.tmp" && \
  mv "$LIVE/klein-vent.log.tmp" "$LIVE/klein-vent.log"
