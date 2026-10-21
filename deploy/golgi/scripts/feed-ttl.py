"""feed-ttl.py — Time as a signal.

Every feed has a TTL (time to live). When TTL expires:
  fresh   (< TTL)     — white, alive
  stale   (TTL-2×TTL) — grey, still valid but aging
  expired (> 2×TTL)   — needs refresh or fossilize
  fossil  (_fossil)   — stone, intentional, feeds the new

Time is not just age — it is prediction and reuse:
  - WHEN should this feed next refresh?
  - HOW LONG until it goes grey?
  - WHAT depends on it being fresh?

This sense runs every pulse and writes feed-health.json.
"""
import json, os, time, math

LIVE = '/opt/membrane/live-terminal'

# TTL table — seconds. Tuned to each feed's natural rhythm.
TTLS = {
    # Every pulse (~2 min)
    'wake-cycle.json':        180,
    'chipmunk.json':          180,
    'bingo-cube.json':        300,
    'family-sourdough.json':   120,
    'bus-cardio.json':         120,
    'journal.json':           180,
    'null-strobe.json':       180,
    'cardiovascular.json':    180,
    'state.json':             180,

    # Every 3rd pulse (~6 min)
    'heartbeat.json':         420,
    'circulatory.json':       420,
    'epitope_caddy.json':     180,

    # Every 5th pulse (~10 min)
    'scan_sweep_sort.json':   720,
    'braid.json':             720,
    'fleet-sort.json':        720,
    'backscatter.json':       720,

    # Every 8th pulse (~16 min)
    'membrane-stack.json':    1200,

    # Slow cycle
    'genome.json':            21600,   # 6 hours
    'natural-sort.json':      21600,
    'dialogue.json':          86400,   # 24 hours (needs question)

    # Event-driven (long TTL — stale = peaceful)
    'talos-notify.json':      86400,
    'signals.json':           3600,
    'membrane-deep.json':     3600,
    'stories.json':           3600,

    # Dashboard + topology — always fresh from skunky
    'dashboard.json':         120,
    'topology.json':          120,
    'campfire.json':          120,
}

# Default TTL for unlisted feeds
DEFAULT_TTL = 1800  # 30 min

def main():
    now = time.time()
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    feeds = {}
    fresh_count = 0
    stale_count = 0
    expired_count = 0
    fossil_count = 0

    for f in sorted(os.listdir(LIVE)):
        if not f.endswith('.json'):
            continue

        path = os.path.join(LIVE, f)
        try:
            mtime = os.path.getmtime(path)
            age_s = now - mtime
            sz = os.path.getsize(path)
        except:
            continue

        # Check if fossil
        try:
            d = json.load(open(path))
            is_fossil = d.get('_fossil', False)
        except:
            is_fossil = False

        ttl = TTLS.get(f, DEFAULT_TTL)

        if is_fossil:
            status = "fossil"
            fossil_count += 1
            color = "black"
            feed_health = 0.0
        else:
            ratio = age_s / max(1, ttl)
            feed_health = round(1.0 / (1.0 + math.exp(3 * (ratio - 1.5))), 3)
            if feed_health > 0.7:
                status = "fresh"
                fresh_count += 1
                color = "white"
            elif feed_health > 0.2:
                status = "stale"
                stale_count += 1
                color = "grey"
            else:
                status = "expired"
                expired_count += 1
                color = "red"

        remaining_s = max(0, ttl - age_s)
        expires_at = time.strftime('%H:%M:%S', time.gmtime(now + remaining_s)) if remaining_s > 0 else 'NOW'

        feeds[f] = {
            'status': status,
            'color': color,
            'age_s': round(age_s),
            'ttl_s': ttl,
            'remaining_s': round(remaining_s),
            'feed_health': feed_health,
            'size_kb': round(sz / 1024, 1),
        }

    health = {
        'timestamp': now_iso,
        'summary': {
            'total': len(feeds),
            'fresh': fresh_count,
            'stale': stale_count,
            'expired': expired_count,
            'fossil': fossil_count,
            'health_pct': round(fresh_count / max(1, len(feeds) - fossil_count) * 100, 1),
        },
        'feeds': feeds,
    }

    with open(os.path.join(LIVE, 'feed-health.json'), 'w') as f:
        json.dump(health, f, indent=2)

if __name__ == '__main__':
    main()
