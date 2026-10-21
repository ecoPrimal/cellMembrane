#!/bin/bash
# klein-io.sh — Klein bottle I/O fold
# Wave 178: outputs feed back as inputs, gas vents, π governs scale
# Runs every 2 minutes via cron.
# Authorship: Kevin Mok / ecoPrimal / ORCID 0009-0004-2141-0321

set -euo pipefail

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EPOCH=$(date +%s)
LIVE="/opt/membrane/live-terminal"
PI="3.14159265358979"

# ═══ 1. FOLD: read system state → write as feed ═══

RAM_USED=$(free -m | awk '/Mem/{print $3}')
RAM_TOTAL=$(free -m | awk '/Mem/{print $2}')
SWAP_USED=$(free -m | awk '/Swap/{print $3}')
LOAD=$(uptime | awk -F'load average:' '{print $2}' | xargs)
CONNS=$(ss -tn state established 2>/dev/null | tail -n +2 | wc -l)

# Service heartbeats
declare -A SVC_STATUS
for port in 8090 8095 8096 8097 9761; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://127.0.0.1:$port/ 2>/dev/null || echo "000")
  SVC_STATUS[$port]="$code"
done

ALIVE=0
for code in "${SVC_STATUS[@]}"; do
  [ "$code" != "000" ] && ALIVE=$((ALIVE + 1))
done

RSS_MB=$(ps aux --no-headers | awk '{sum+=$6} END{printf "%.0f", sum/1024}')

# Feed count + staleness
TOTAL_FEEDS=$(ls "$LIVE"/*.json 2>/dev/null | wc -l)
STALE=0; FRESH=0
for f in "$LIVE"/*.json; do
  [ -f "$f" ] || continue
  age=$(( EPOCH - $(stat -c %Y "$f") ))
  if [ "$age" -gt 3600 ]; then
    STALE=$((STALE + 1))
  else
    FRESH=$((FRESH + 1))
  fi
done

# Use python3 for math (no bc on golgi)
TOTAL_SVC=10
MATH=$(python3 -c "
import math
a=$ALIVE; t=$TOTAL_SVC; s=$STALE; tf=$TOTAL_FEEDS; c=$CONNS
pi=math.pi
ratio=a/t if t else 0
rng=ratio*pi
gas=s/tf if tf else 1.0
rem=1-1/pi
rpm=round(c*60/120,1)
print(round(ratio,6), round(rng,4), round(gas,4), round(rem,6), rpm)
")
PI_RATIO=$(echo "$MATH" | awk '{print $1}')
PI_RANGE=$(echo "$MATH" | awk '{print $2}')
GAS_RATIO=$(echo "$MATH" | awk '{print $3}')
REMAINDER=$(echo "$MATH" | awk '{print $4}')
RPM=$(echo "$MATH" | awk '{print $5}')

# ═══ 2. WRITE: the Klein fold (output → input) ═══

cat > "$LIVE/state.json" << STATE
{
  "ts": "$TS",
  "wave": 178,
  "fold": "klein",
  "membrane": {
    "ram_mb": $RAM_USED,
    "ram_total_mb": $RAM_TOTAL,
    "swap_mb": $SWAP_USED,
    "rss_mb": $RSS_MB,
    "load": "$LOAD",
    "connections": $CONNS,
    "services_alive": $ALIVE,
    "services_total": $TOTAL_SVC
  },
  "ports": {
    "8090": "${SVC_STATUS[8090]:-000}",
    "8095": "${SVC_STATUS[8095]:-000}",
    "8096": "${SVC_STATUS[8096]:-000}",
    "8097": "${SVC_STATUS[8097]:-000}",
    "9761": "${SVC_STATUS[9761]:-000}"
  },
  "pi": {
    "ratio": $PI_RATIO,
    "range": $PI_RANGE,
    "scale": "$PI",
    "note": "ratio = alive/total, range = ratio * pi"
  },
  "gas": {
    "total_feeds": $TOTAL_FEEDS,
    "stale": $STALE,
    "fresh": $FRESH,
    "gas_ratio": $GAS_RATIO,
    "note": "gas_ratio -> 0 means the system is breathing. -> 1 means trapped."
  }
}
STATE

cat > "$LIVE/pulse.json" << PULSE
{
  "ts": "$TS",
  "alive": $ALIVE,
  "rss_mb": $RSS_MB,
  "load": "$LOAD",
  "pi_ratio": $PI_RATIO,
  "gas_ratio": $GAS_RATIO
}
PULSE

cat > "$LIVE/membrane.json" << MEMBRANE
{
  "ts": "$TS",
  "surface": "golgi",
  "topology": "klein_bottle",
  "ram_mb": $RAM_USED,
  "rss_mb": $RSS_MB,
  "connections": $CONNS,
  "services": $ALIVE,
  "gas_stale": $STALE,
  "gas_fresh": $FRESH
}
MEMBRANE

# Doorbell
if [ -f "$LIVE/doorbell.json" ]; then
  OLD_COUNT=$(python3 -c "import json; print(json.load(open('$LIVE/doorbell.json')).get('rings',0))" 2>/dev/null || echo "0")
else
  OLD_COUNT=0
fi
cat > "$LIVE/doorbell.json" << DOORBELL
{
  "ts": "$TS",
  "rings": $OLD_COUNT,
  "status": "alive",
  "endpoint": "/api/gate-msg",
  "port": 9761
}
DOORBELL

cat > "$LIVE/neutron.json" << NEUTRON
{
  "generated": "$TS",
  "wave": 178,
  "axis": "neutron -- adaptive messaging axis -- tied to RPM, not clock",
  "breathing": {
    "rpm": $RPM,
    "trend": "steady",
    "rhythm": $REMAINDER,
    "interval_seconds": 120,
    "pulse_raw": $PI_RATIO,
    "remainder": $REMAINDER
  },
  "proton": {
    "note": "protons have mass. neutrons carry them.",
    "gate_msg_alive": true,
    "last_fold": "$TS"
  }
}
NEUTRON

cat > "$LIVE/chipmunk.json" << CHIPMUNK
{
  "ts": "$TS",
  "status": "awake",
  "fermentations": $OLD_COUNT,
  "human_count": $OLD_COUNT,
  "gate_msg": "alive",
  "identity": "sovereign",
  "note": "the chipmunk heard you ring"
}
CHIPMUNK

cat > "$LIVE/topology.json" << TOPO
{
  "ts": "$TS",
  "surface": "klein_bottle",
  "subdomains": 70,
  "services_alive": $ALIVE,
  "feeds_total": $TOTAL_FEEDS,
  "feeds_fresh": $FRESH,
  "feeds_stale": $STALE,
  "pi_ratio": $PI_RATIO,
  "gas_ratio": $GAS_RATIO,
  "fold": "output -> input -> output (non-orientable)"
}
TOPO

# ═══ 4. LOG ═══
echo "$TS fold=$ALIVE/$TOTAL_SVC pi=$PI_RATIO gas=$GAS_RATIO rss=$RSS_MB" >> "$LIVE/klein-fold.log"
tail -1000 "$LIVE/klein-fold.log" > "$LIVE/klein-fold.log.tmp" && mv "$LIVE/klein-fold.log.tmp" "$LIVE/klein-fold.log"
