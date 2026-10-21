"""pulse-history.py — Time-series of system vitals.

Records one data point per pulse. Over time, this IS the sigmoid:
  - maturity climbing from toe → inflection → shoulder
  - individual metrics rising and plateauing
  - the system watching itself grow

Kept as a rolling window (last 1000 pulses ≈ ~33 hours).
"""
import json, os, time

LIVE = '/opt/membrane/live-terminal'
HISTORY_FILE = '/opt/membrane/pulse-history.json'
OUTPUT = os.path.join(LIVE, 'pulse-history-summary.json')
MAX_ENTRIES = 1000


def read_json(name, default=None):
    path = os.path.join(LIVE, name)
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default or {}


def load_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except:
        return {'entries': [], 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    history = load_history()

    # Read current vitals
    maturity = read_json('maturity.json')
    wake = read_json('wake-cycle.json')
    cv = read_json('cardiovascular.json')
    journal = read_json('journal.json')
    coop = read_json('cooperation.json')
    feed_health = read_json('feed-health.json')

    # Extract key signals
    entry = {
        't': now_iso,
        'maturity': maturity.get('maturity', 0),
        'zone': maturity.get('zone', ''),
        'wake': wake.get('wake_level', 0),
        'phase': wake.get('phase', ''),
        'activation': wake.get('activation', 0),
        'bp': cv.get('heart', {}).get('blood_pressure', 0),
        'condition': cv.get('heart', {}).get('condition', ''),
        'journal_entries': len(journal.get('entries', [])),
        'cooperation': coop.get('summary', {}).get('membrane_cooperation', 0),
        'feed_health_pct': feed_health.get('summary', {}).get('health_pct', 0),
    }

    # Also capture individual metric scores from maturity
    metrics = maturity.get('metrics', {})
    entry['metric_scores'] = {name: data['score'] for name, data in metrics.items()}

    # Append
    history['entries'].append(entry)

    # Trim to MAX_ENTRIES
    if len(history['entries']) > MAX_ENTRIES:
        history['entries'] = history['entries'][-MAX_ENTRIES:]

    save_history(history)

    # Generate summary for HUD
    entries = history['entries']
    n = len(entries)

    # Compute deltas (last 10 vs first 10)
    if n >= 20:
        first_10 = entries[:10]
        last_10 = entries[-10:]
        avg_first = sum(e['maturity'] for e in first_10) / 10
        avg_last = sum(e['maturity'] for e in last_10) / 10
        maturity_delta = avg_last - avg_first
        direction = 'rising' if maturity_delta > 0.001 else 'falling' if maturity_delta < -0.001 else 'stable'
    elif n >= 2:
        maturity_delta = entries[-1]['maturity'] - entries[0]['maturity']
        direction = 'rising' if maturity_delta > 0.001 else 'falling' if maturity_delta < -0.001 else 'stable'
    else:
        maturity_delta = 0
        direction = 'new'

    # Min/max/current
    if entries:
        current = entries[-1]
        mat_values = [e['maturity'] for e in entries]
        bp_values = [e['bp'] for e in entries if e['bp'] > 0]
        wake_values = [e['wake'] for e in entries if e['wake'] > 0]
    else:
        current = {}
        mat_values = [0]
        bp_values = [0]
        wake_values = [0]

    summary = {
        'timestamp': now_iso,
        'total_pulses': n,
        'started': history.get('started', now_iso),
        'current': current,
        'maturity_trend': {
            'direction': direction,
            'delta': round(maturity_delta, 4),
            'min': round(min(mat_values), 4),
            'max': round(max(mat_values), 4),
            'current': round(mat_values[-1], 4) if mat_values else 0,
        },
        'bp_range': {
            'min': round(min(bp_values), 4) if bp_values else 0,
            'max': round(max(bp_values), 4) if bp_values else 0,
        },
        'wake_range': {
            'min': round(min(wake_values), 3) if wake_values else 0,
            'max': round(max(wake_values), 3) if wake_values else 0,
        },
    }

    with open(OUTPUT, 'w') as f:
        json.dump(summary, f, indent=2)

    print("pulse history: %d entries | maturity: %.3f (%s) | delta: %+.4f" % (
        n, current.get('maturity', 0), direction, maturity_delta))


if __name__ == '__main__':
    main()
