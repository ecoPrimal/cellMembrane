"""entropy-sense.py — Measure what's decaying.

If sigmoid measures growth, entropy measures decay.
Every system has both. The healthy ones balance them.

  entropy_rate = (stale + expired + defections) / total_signals
  negentropy   = 1 - entropy_rate  (what's being maintained)

Shannon entropy across feed diversity — are we relying
on too few signals, or is the information spread healthy?
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
OUTPUT = os.path.join(LIVE, 'entropy.json')


def read_json(name, default=None):
    path = os.path.join(LIVE, name)
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default or {}


def shannon_entropy(distribution):
    """Shannon entropy of a probability distribution.

    Returns bits of information. Higher = more diverse.
    Max = log2(N) where N is number of categories.
    """
    total = sum(distribution.values())
    if total == 0:
        return 0.0

    H = 0.0
    for count in distribution.values():
        if count > 0:
            p = count / total
            H -= p * math.log2(p)
    return round(H, 3)


def max_entropy(n):
    """Maximum possible entropy for n categories."""
    if n <= 1:
        return 0.0
    return round(math.log2(n), 3)


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # === FEED ENTROPY ===
    feed_health = read_json('feed-health.json')
    feeds = feed_health.get('feeds', {})
    summary = feed_health.get('summary', {})

    feed_status_dist = {
        'fresh': summary.get('fresh', 0),
        'stale': summary.get('stale', 0),
        'expired': summary.get('expired', 0),
        'fossil': summary.get('fossil', 0),
    }
    feed_entropy = shannon_entropy(feed_status_dist)
    feed_max = max_entropy(len(feed_status_dist))

    # Feed size distribution (are sizes diverse or concentrated?)
    size_buckets = {'tiny': 0, 'small': 0, 'medium': 0, 'large': 0}
    for name, data in feeds.items():
        sz = data.get('size_kb', 0)
        if sz < 1:
            size_buckets['tiny'] += 1
        elif sz < 10:
            size_buckets['small'] += 1
        elif sz < 100:
            size_buckets['medium'] += 1
        else:
            size_buckets['large'] += 1
    size_entropy = shannon_entropy(size_buckets)

    # === FLEET ENTROPY ===
    sort_data = read_json('scan_sweep_sort.json')
    scan = sort_data.get('scan', {})
    fleet_classes = scan.get('fleet_classes', {})
    fleet_entropy = shannon_entropy(fleet_classes)
    fleet_max = max_entropy(len(fleet_classes))

    # === COOPERATION ENTROPY ===
    coop = read_json('cooperation.json')
    coop_summary = coop.get('summary', {})
    coop_dist = {
        'cooperations': coop_summary.get('cooperations', 0),
        'defections': coop_summary.get('defections', 0),
        'forgiven': coop_summary.get('forgiven', 0),
    }
    coop_entropy = shannon_entropy(coop_dist)

    # === PHASE ENTROPY (from wake cycle) ===
    wake = read_json('wake-cycle.json')
    phase_activations = wake.get('phase_activations', {})
    if phase_activations:
        # Normalize to sum=1
        total_act = sum(phase_activations.values())
        if total_act > 0:
            phase_dist = {k: v / total_act for k, v in phase_activations.items()}
        else:
            phase_dist = phase_activations
        phase_entropy = shannon_entropy(phase_dist)
        phase_max = max_entropy(len(phase_dist))
    else:
        phase_entropy = 0
        phase_max = 0

    # === OVERALL ENTROPY RATE ===
    total_signals = summary.get('total', 1)
    decaying = summary.get('stale', 0) + summary.get('expired', 0) + summary.get('fossil', 0)
    entropy_rate = round(decaying / max(1, total_signals), 3)
    negentropy = round(1.0 - entropy_rate, 3)

    # === INFORMATION DIVERSITY ===
    # How evenly spread is information across feeds?
    if total_signals > 1:
        normalized_feed_entropy = round(feed_entropy / feed_max, 3) if feed_max > 0 else 0
    else:
        normalized_feed_entropy = 0

    # Health: sigmoid of negentropy
    health = round(sigmoid(negentropy, 0.7, 8), 3)

    result = {
        'timestamp': now_iso,
        'entropy_rate': entropy_rate,
        'negentropy': negentropy,
        'health': health,
        'feed_entropy': {
            'shannon': feed_entropy,
            'max': feed_max,
            'normalized': normalized_feed_entropy,
            'status_distribution': feed_status_dist,
            'size_distribution': size_buckets,
            'size_entropy': size_entropy,
        },
        'fleet_entropy': {
            'shannon': fleet_entropy,
            'max': fleet_max,
            'classes': fleet_classes,
        },
        'cooperation_entropy': {
            'shannon': coop_entropy,
            'distribution': coop_dist,
        },
        'phase_entropy': {
            'shannon': phase_entropy,
            'max': phase_max,
            'note': 'higher = more blended phases. 0 = locked in one phase.',
        },
        'note': 'entropy is not the enemy. too little entropy = brittle. too much = chaos. the sigmoid balances.',
    }

    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    print("entropy: rate=%.3f  negentropy=%.3f  health=%.3f" % (entropy_rate, negentropy, health))
    print("  feed:  H=%.3f/%.3f (%.0f%% diverse)" % (feed_entropy, feed_max, normalized_feed_entropy*100))
    print("  fleet: H=%.3f/%.3f" % (fleet_entropy, fleet_max))
    print("  phase: H=%.3f/%.3f" % (phase_entropy, phase_max))
    print("  coop:  H=%.3f" % coop_entropy)


if __name__ == '__main__':
    main()
