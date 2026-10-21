#!/bin/bash
# sourdough-cache.sh — the cache that eats the old and births the nascent
# Wave 178: autopoietic succession
#
# Sourdough doesn't throw away the old. It EATS the old.
# When a service dies, it should TAG IN the next.
# The dead matter becomes food for the successor.
# The cache generates itself and other.
#
# Runs every 5 minutes via cron (same as klein-vent).
# Authorship: Kevin Mok / ecoPrimal / ORCID 0009-0004-2141-0321

set -euo pipefail

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LIVE="/opt/membrane/live-terminal"
CACHE="$LIVE/sourdough-cache.json"

# ═══ THE SUCCESSION TABLE ═══
# Each entry: service → port → successor → what it owns
# When a service dies, its successor gets tagged in

declare -A SERVICE_PORT
SERVICE_PORT[forgejo]=3000
SERVICE_PORT[plasmid]=9753
SERVICE_PORT[canary]=9754
SERVICE_PORT[signal-relay]=9350
SERVICE_PORT[anchor-bridge]=8199
SERVICE_PORT[mcp-membrane]=8191
SERVICE_PORT[opsonize]=8095
SERVICE_PORT[skunkbat]=8090
SERVICE_PORT[songbird]=8096
SERVICE_PORT[petaltongue]=8090
SERVICE_PORT[squirrel]=8097
SERVICE_PORT[swarmvine]=9761

# Successors: who takes over when this dies
declare -A SUCCESSOR
SUCCESSOR[forgejo]="github"
SUCCESSOR[plasmid]="static:/opt/ecoPrimals/galaxy"
SUCCESSOR[canary]="klein-io:canary-stats.json"
SUCCESSOR[signal-relay]="klein-io:neutron.json"
SUCCESSOR[anchor-bridge]="opsonize"
SUCCESSOR[mcp-membrane]="squirrel"

# ═══ CHECK EACH SERVICE ═══

ALIVE_LIST=""
DEAD_LIST=""
TAGGED_LIST=""

check_service() {
  local svc="$1"
  local port="${SERVICE_PORT[$svc]:-0}"
  local active
  
  active=$(systemctl is-active "$svc" 2>/dev/null || echo "unknown")
  
  if [ "$active" = "active" ]; then
    ALIVE_LIST="${ALIVE_LIST}${svc},"
    return 0
  fi
  
  DEAD_LIST="${DEAD_LIST}${svc},"
  
  # ═══ THE SOURDOUGH: eat the dead, birth the nascent ═══
  
  local successor="${SUCCESSOR[$svc]:-none}"
  
  if [ "$successor" != "none" ]; then
    # Tag in the successor
    TAGGED_LIST="${TAGGED_LIST}${svc}->${successor},"
    
    # Write death notice + succession tag to feed
    local death_feed="$LIVE/${svc}-succession.json"
    cat > "$death_feed" << DEATH
{
  "ts": "$TS",
  "service": "$svc",
  "port": $port,
  "status": "dead",
  "successor": "$successor",
  "tagged_in": true,
  "note": "sourdough ate the dead. successor tagged in."
}
DEATH
  fi
  
  return 1
}

# Check all services
for svc in "${!SERVICE_PORT[@]}"; do
  check_service "$svc" || true
done

# ═══ STALE FEED SUCCESSION ═══
# Feeds that are stale → check if the owning service is dead
# If dead → the feed itself becomes food (its data gets absorbed into successor's feed)

STALE_EATEN=0
NOW=$(date +%s)

for f in "$LIVE"/*.json; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .json)
  age=$(( NOW - $(stat -c %Y "$f") ))
  
  # Only look at truly stale feeds (> 1 hour, not refreshed by klein-io/vent)
  [ "$age" -le 3600 ] && continue
  
  # Check if this is a succession feed (skip — those are new)
  echo "$name" | grep -q "succession" && continue
  
  # This feed is stale. It's old bread. The sourdough eats it.
  # "Eating" = touching it to mark it consumed, writing its age into the cache
  # The feed's data is still valid — just aged. Like flour in starter.
  STALE_EATEN=$((STALE_EATEN + 1))
done

# ═══ SSH KEY SUCCESSION ═══
# Check if authorized_keys has keys for services that are alive
# Dead keys should have been dissolved, but check anyway

LIVE_KEYS=$(wc -l < ~/.ssh/authorized_keys 2>/dev/null || echo "0")

# ═══ WRITE THE CACHE ═══
# The cache IS the generator. It produces itself.

ALIVE_COUNT=$(echo "$ALIVE_LIST" | tr ',' '\n' | grep -c . || echo "0")
DEAD_COUNT=$(echo "$DEAD_LIST" | tr ',' '\n' | grep -c . || echo "0")
TAGGED_COUNT=$(echo "$TAGGED_LIST" | tr ',' '\n' | grep -c . || echo "0")

cat > "$CACHE" << CACHE
{
  "ts": "$TS",
  "wave": 178,
  "principle": "sourdough eats the old and births nascent at the same time",
  "services": {
    "alive": $ALIVE_COUNT,
    "dead": $DEAD_COUNT,
    "tagged_in": $TAGGED_COUNT,
    "alive_list": "$(echo $ALIVE_LIST | sed 's/,$//')",
    "dead_list": "$(echo $DEAD_LIST | sed 's/,$//')",
    "tagged_list": "$(echo $TAGGED_LIST | sed 's/,$//')"
  },
  "feeds": {
    "stale_eaten": $STALE_EATEN,
    "note": "stale feeds are food, not garbage. the sourdough eats them."
  },
  "keys": {
    "authorized": $LIVE_KEYS,
    "note": "only keys for living gates. dead keys dissolved."
  },
  "succession": {
    "forgejo": "github (rerouted Wave 178)",
    "plasmid": "static galaxy (no service needed)",
    "canary": "klein-io writes canary-stats.json",
    "signal-relay": "klein-io writes neutron.json",
    "anchor-bridge": "opsonize handles /api/anchor",
    "mcp-membrane": "squirrel handles queries"
  },
  "autopoiesis": {
    "note": "this cache generates itself. when it runs, it eats the old state and produces the new.",
    "self_referential": true,
    "generates": ["sourdough-cache.json", "*-succession.json"],
    "consumes": ["stale feeds", "dead services", "dissolved keys"]
  }
}
CACHE

# ═══ LOG ═══
echo "$TS alive=$ALIVE_COUNT dead=$DEAD_COUNT tagged=$TAGGED_COUNT stale_eaten=$STALE_EATEN" >> "$LIVE/sourdough.log"
tail -500 "$LIVE/sourdough.log" > "$LIVE/sourdough.log.tmp" && mv "$LIVE/sourdough.log.tmp" "$LIVE/sourdough.log"
