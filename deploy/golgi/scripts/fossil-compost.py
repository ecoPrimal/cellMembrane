"""fossil-compost.py — Turn fossils into compost.

Dead feeds aren't waste — they're data.
Extract the last useful signal from each fossil, then:
  1. Record what it was (provenance)
  2. Record when it died (time of death)
  3. Record what it knew (last values)
  4. Compute: does anything living still reference it?

Fossils that are still referenced are ghosts.
Fossils that nobody references are compost.
Compost feeds the next generation.
"""
import json, os, time, sys

sys.path.insert(0, '/opt/membrane')

LIVE = '/opt/membrane/live-terminal'
FOSSIL_DIR = '/opt/membrane/fossilRecord'
OUTPUT = os.path.join(LIVE, 'fossil-compost.json')


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default or {}


def find_references(fossil_name, all_feeds):
    """Check if any living feed still references this fossil."""
    refs = []
    base = fossil_name.replace('.json', '')

    for feed_name, feed_data in all_feeds.items():
        if feed_name == fossil_name:
            continue
        feed_str = json.dumps(feed_data)
        if base in feed_str:
            refs.append(feed_name)

    return refs


def extract_last_signal(data):
    """Extract the most recent meaningful values from fossil data."""
    if not isinstance(data, dict):
        return {}

    signal = {}
    skip_keys = {'_fossil', '_fossil_note', '_fossilized_at', 'timestamp', 'ts', 'generated'}

    for key, value in data.items():
        if key in skip_keys or key.startswith('_'):
            continue
        if isinstance(value, (int, float, bool, str)):
            signal[key] = value
        elif isinstance(value, dict) and len(value) <= 5:
            signal[key] = value
        elif isinstance(value, list) and len(value) <= 3:
            signal[key] = value

    return signal


def main():
    now = time.time()
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # Load all living feeds for reference checking
    living_feeds = {}
    for f in os.listdir(LIVE):
        if not f.endswith('.json'):
            continue
        path = os.path.join(LIVE, f)
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        if not data.get('_fossil', False):
            living_feeds[f] = data

    # Find all fossils in live-terminal
    fossils = []
    for f in os.listdir(LIVE):
        if not f.endswith('.json'):
            continue
        path = os.path.join(LIVE, f)
        data = read_json(path)
        if isinstance(data, dict) and data.get('_fossil', False):
            fossils.append((f, path, data))

    # Also check fossilRecord
    if os.path.isdir(FOSSIL_DIR):
        for f in os.listdir(FOSSIL_DIR):
            if not f.endswith('.json'):
                continue
            path = os.path.join(FOSSIL_DIR, f)
            data = read_json(path)
            if f not in [x[0] for x in fossils]:
                fossils.append((f, path, data))

    composted = []
    ghosts = []
    total_data_points = 0

    for name, path, data in fossils:
        # Extract signal
        signal = extract_last_signal(data)
        total_data_points += len(signal)

        # Check references
        refs = find_references(name, living_feeds)
        fossil_time = data.get('_fossilized_at', data.get('timestamp', data.get('ts', '')))

        # Age
        try:
            mtime = os.path.getmtime(path)
            age_days = (now - mtime) / 86400
        except:
            age_days = 0

        entry = {
            'name': name,
            'age_days': round(age_days, 1),
            'fossilized_at': fossil_time,
            'last_signal': signal,
            'signal_keys': len(signal),
            'referenced_by': refs,
        }

        if refs:
            entry['status'] = 'ghost'
            entry['note'] = 'still referenced by %d living feeds — cannot compost' % len(refs)
            ghosts.append(entry)
        else:
            entry['status'] = 'compost'
            entry['note'] = 'unreferenced — safe to compost'
            composted.append(entry)

    result = {
        'timestamp': now_iso,
        'summary': {
            'total_fossils': len(fossils),
            'ghosts': len(ghosts),
            'compost': len(composted),
            'total_data_points_preserved': total_data_points,
        },
        'ghosts': ghosts,
        'compost': composted,
        'note': 'ghosts are referenced by the living. compost feeds the next generation.',
    }

    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    print("fossil compost:")
    print("  %d fossils: %d ghosts, %d compost" % (len(fossils), len(ghosts), len(composted)))
    if ghosts:
        print("  ghosts (still referenced):")
        for g in ghosts[:5]:
            print("    %s — refs: %s" % (g['name'], ', '.join(g['referenced_by'][:3])))
    if composted:
        print("  compost (safe to recycle):")
        for c in composted[:5]:
            print("    %s (%d data points, %.1f days old)" % (c['name'], c['signal_keys'], c['age_days']))


if __name__ == '__main__':
    main()
