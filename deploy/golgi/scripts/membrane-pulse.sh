#!/bin/bash
# O* = & ~#  — Klein bottle membrane pulse
# Lightweight flow monitor — runs on the thin surface
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LIVE="/opt/membrane/live-terminal"
mkdir -p "$LIVE"

# Gather membrane vitals
RAM_USED=$(free -m | awk "/Mem/{print \$3}")
RAM_TOTAL=$(free -m | awk "/Mem/{print \$2}")
SWAP_USED=$(free -m | awk "/Swap/{print \$3}")
LOAD=$(uptime | awk -F"load average:" "{print \$2}" | xargs)
CONNS=$(ss -tn state established | tail -n +2 | wc -l)

# Count Caddy requests in last 5 min
REQUESTS=0
if [ -f /var/log/caddy/access.log ]; then
  REQUESTS=$(wc -l < /var/log/caddy/access.log 2>/dev/null || echo 0)
fi

# Service heartbeats
SERVICES_UP=0
for svc in caddy-tls opsonize skunkbat songbird loamspine beardog barracuda squirrel; do
  systemctl is-active $svc >/dev/null 2>&1 && SERVICES_UP=$((SERVICES_UP + 1))
done

# Write pulse
cat > "$LIVE/membrane-pulse.json" << PULSE
{
  "ts": "$TS",
  "topology": "klein-bottle",
  "ram_mb": {"used": $RAM_USED, "total": $RAM_TOTAL},
  "swap_mb": $SWAP_USED,
  "load": "$LOAD",
  "connections": $CONNS,
  "services_up": $SERVICES_UP,
  "surface_ok": true
}
PULSE

echo "$TS pulse: ram=${RAM_USED}/${RAM_TOTAL} swap=${SWAP_USED} load=${LOAD} conns=${CONNS} svcs=${SERVICES_UP}" >> /var/log/membrane-pulse.log
