#!/bin/bash
# cron-lock.sh v2 — membrane-aware flock wrapper
# Usage: cron-lock.sh <lockname> <command...>
#
# - Prevents overlapping runs via flock
# - Auto-cleans stale locks (dead PIDs)
# - Reports lock state to membrane live-terminal
# - Tracks execution timing for membrane health

LOCKNAME=$1; shift
LOCKDIR=/run/membrane
LOCKFILE=${LOCKDIR}/cron-${LOCKNAME}.lock
STATEFILE=${LOCKDIR}/cron-state.json
LOGFILE=/var/log/membrane/cron-skips.log
START_TS=$(date -u +%s)

# Auto-clean stale lock if PID is dead
if [ -f "$LOCKFILE" ]; then
    OLDPID=$(cat "$LOCKFILE" 2>/dev/null | tr -d " \n")
    if [ -n "$OLDPID" ] && ! kill -0 "$OLDPID" 2>/dev/null; then
        rm -f "$LOCKFILE"
        echo "[$(date -Is)] $LOCKNAME: auto-cleaned stale lock (dead pid=$OLDPID)" >> "$LOGFILE"
    fi
fi

# Acquire lock (non-blocking)
exec 200>"$LOCKFILE"
flock -n 200 || {
    echo "[$(date -Is)] $LOCKNAME: skipped (already running)" >> "$LOGFILE"
    exit 0
}
echo $$ >&200

# Run the command
"$@"
EXIT_CODE=$?

# Track timing
END_TS=$(date -u +%s)
ELAPSED=$((END_TS - START_TS))

# Report to membrane (non-blocking, best-effort)
{
    python3 -c "
import json, os, time
from datetime import datetime, timezone
state_file = '${STATEFILE}'
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
try:
    with open(state_file) as f:
        state = json.load(f)
except:
    state = {'jobs': {}, 'last_clean': now}

state['jobs']['${LOCKNAME}'] = {
    'last_run': now,
    'elapsed_s': ${ELAPSED},
    'exit_code': ${EXIT_CODE},
    'pid': $$
}
state['timestamp'] = now
state['total_jobs'] = len(state['jobs'])

with open(state_file + '.tmp', 'w') as f:
    json.dump(state, f, indent=2)
os.rename(state_file + '.tmp', state_file)
" 2>/dev/null
} &

exit $EXIT_CODE
