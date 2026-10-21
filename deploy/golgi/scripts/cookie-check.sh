#!/bin/bash
# cookie-check.sh — a small test meant to be consumed
# Pull this, run it, verify the recipe works, then it goes stale.
# If nobody runs it within 24h, it fossilizes itself.
set -euo pipefail

COOKIE_BAKED="$(date -Is)"
COOKIE_STALE=86400  # 24 hours in seconds

echo "🍪 cookie baked: $COOKIE_BAKED"
echo ''

PASS=0
FAIL=0

check() {
    if $2 >/dev/null 2>&1; then
        echo "  ✅ $1"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $1"
        FAIL=$((FAIL + 1))
    fi
}

echo '=== Recipe Check (13 ingredients) ==='
check 'membrane-pulse.py exists' '[ -f /opt/membrane/membrane-pulse.py ]'
check 'detroit-pull-build.sh exists' '[ -f /opt/membrane/detroit-pull-build.sh ]'
check 'tuebor-pull-build.sh exists' '[ -f /opt/membrane/tuebor-pull-build.sh ]'
check 'circulatory-sense.py exists' '[ -f /opt/membrane/circulatory-sense.py ]'
check 'heartbeat-sense.py exists' '[ -f /opt/membrane/heartbeat-sense.py ]'
check 'scan_sweep_sort.py exists' '[ -f /opt/membrane/scan_sweep_sort.py ]'
check 'neutron-writer.py exists' '[ -f /opt/membrane/neutron-writer.py ]'
check 'cardiovascular-sense.py exists' '[ -f /opt/membrane/cardiovascular-sense.py ]'
check 'sourdough-topology.py exists' '[ -f /opt/membrane/sourdough-topology.py ]'
check 'campfire-culture.py exists' '[ -f /opt/membrane/campfire-culture.py ]'
check 'pollen-sense.py exists' '[ -f /opt/membrane/pollen-sense.py ]'
check 'braid-vcs.sh exists' '[ -f /opt/membrane/braid-vcs.sh ]'
check 'canary.sh exists' '[ -f /opt/membrane/canary.sh ]'

echo ''
echo "=== $PASS/13 ingredients present, $FAIL missing ==="

# Self-fossilize check
if [ -f /opt/membrane/cookie-check.sh ]; then
    AGE=$(( $(date +%s) - $(stat -c%Y /opt/membrane/cookie-check.sh) ))
    if [ $AGE -gt $COOKIE_STALE ]; then
        echo ''
        echo '🪨 cookie went stale — fossilizing'
        mv /opt/membrane/cookie-check.sh /opt/membrane/fossilRecord/cookie-check.sh.fossil_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    else
        HOURS=$(( (COOKIE_STALE - AGE) / 3600 ))
        echo "⏳ cookie fresh for ~${HOURS}h more, then turns to stone"
    fi
fi

echo ''
echo "🍪 eaten. come back for another."
