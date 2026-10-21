"""sigmoid.py — The S-curve lives here.

Shared sigmoid utilities for the membrane ecosystem.
Every threshold, every transition, every gradient flows through here.

The sigmoid is the shape of growth:
  - slow start (toe)
  - rapid rise (inflection)
  - plateau (shoulder)

Everything alive follows this curve.
"""
import math


def sigmoid(x, center=0.5, steepness=10):
    """Standard sigmoid: smooth 0→1 centered at 'center'.

    x: input value
    center: where the curve hits 0.5
    steepness: how sharp the transition (higher = sharper)
    """
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (x - center)))
    except OverflowError:
        return 0.0 if steepness * (x - center) < 0 else 1.0


def inverse_sigmoid(x, center=0.5, steepness=10):
    """Inverse: smooth 1→0 centered at 'center'.
    Same as sigmoid but flipped — for decay curves."""
    return 1.0 - sigmoid(x, center, steepness)


def phase_blend(value, phases=None):
    """Compute blended phase activations from a 0→1 value.

    Returns (dominant_phase, activation, all_activations).
    Default phases are the wake cycle: sleep, rest, pause, wake, full.
    """
    if phases is None:
        phases = {
            'sleep': (0.1, 20, 0.3, 15),
            'rest':  (0.3, 15, 0.5, 12),
            'pause': (0.5, 12, 0.7, 10),
            'wake':  (0.7, 10, 0.9, 8),
            'full':  (0.9, 8, None, None),
        }

    activations = {}
    for name, params in phases.items():
        on_center, on_steep, off_center, off_steep = params
        act = sigmoid(value, on_center, on_steep)
        if off_center is not None:
            act *= (1.0 - sigmoid(value, off_center, off_steep))
        activations[name] = round(act, 3)

    if value <= 0.001 or value >= 0.999:
        return ('null', 0.0, activations)

    dominant = max(activations, key=activations.get)
    return (dominant, activations[dominant], activations)


def severity(value, threshold, steepness=12):
    """How severe is a condition? 1.0 at 0, 0.0 above threshold.

    Good for: hypotension severity, staleness, decay.
    severity(0.2, 0.4) → 0.917  (bp well below threshold)
    severity(0.4, 0.4) → 0.500  (at threshold)
    severity(0.6, 0.4) → 0.083  (above threshold — healthy)
    """
    return round(inverse_sigmoid(value, threshold, steepness), 3)


def health_decay(age, ttl, steepness=3):
    """Feed/signal health as a function of age vs TTL.

    Returns 0→1 where 1.0 = perfectly fresh, 0.0 = expired.
    Centered at 1.5× TTL (half-life).
    """
    ratio = age / max(1, ttl)
    return round(inverse_sigmoid(ratio, 1.5, steepness), 3)


def confidence(raw, center=0.5, steepness=6):
    """Map raw confidence to sigmoid-smoothed confidence.

    Compresses noise near 0 and 1, spreads resolution near center.
    """
    return round(sigmoid(raw, center, steepness), 3)


def growth_curve(t, midpoint=50, rate=0.1):
    """The S-curve of maturity/adoption.

    t: time or progress metric
    midpoint: when growth is fastest
    rate: how quickly it happens

    Returns 0→1. Use for: species maturity, build progress, coverage.
    """
    return round(sigmoid(t, midpoint, rate), 3)


def blend_two(value, a_name, b_name, crossover=0.5, steepness=10):
    """Blend between two states with sigmoid crossfade.

    Returns {a_name: weight, b_name: weight} where weights sum to ~1.0.
    """
    b_weight = sigmoid(value, crossover, steepness)
    a_weight = 1.0 - b_weight
    return {a_name: round(a_weight, 3), b_name: round(b_weight, 3)}


def maturity_score(metrics):
    """Compute system maturity from multiple metrics.

    metrics: dict of {name: (current, target)} pairs
    Returns: overall maturity 0→1 using product of individual sigmoids.

    This IS the sigmoid. The system's position on the S-curve.
    """
    if not metrics:
        return 0.0

    scores = []
    details = {}
    for name, (current, target) in metrics.items():
        ratio = current / max(1, target)
        score = sigmoid(ratio, 0.7, 8)  # steep around 70% of target
        scores.append(score)
        details[name] = round(score, 3)

    # Geometric mean — all metrics matter
    product = 1.0
    for s in scores:
        product *= max(0.001, s)
    overall = product ** (1.0 / len(scores))

    return round(overall, 3), details


# Self-test
if __name__ == "__main__":
    print("=== SIGMOID MODULE SELF-TEST ===\n")

    print("Basic sigmoid(0.3, center=0.5, steepness=10):", sigmoid(0.3, 0.5, 10))
    print("Inverse sigmoid(0.3, center=0.5, steepness=10):", inverse_sigmoid(0.3, 0.5, 10))

    print("\nPhase blend at 0.600:")
    phase, act, blends = phase_blend(0.600)
    print("  dominant: %s (%.1f%%)" % (phase, act*100))
    for k, v in sorted(blends.items()):
        bar = "#" * int(v * 30)
        print("  %-6s %.3f %s" % (k, v, bar))

    print("\nSeverity of bp=0.222 (threshold 0.4):", severity(0.222, 0.4))
    print("Severity of bp=0.350 (threshold 0.4):", severity(0.350, 0.4))
    print("Severity of bp=0.500 (threshold 0.4):", severity(0.500, 0.4))

    print("\nHealth decay:")
    for age_ratio in [0.5, 1.0, 1.5, 2.0, 3.0]:
        print("  age=%5.1f×TTL  health=%.3f" % (age_ratio, health_decay(age_ratio * 100, 100)))

    print("\n--- SYSTEM MATURITY ---")
    maturity, details = maturity_score({
        'sort_confidence': (53.8, 85.0),
        'feed_health_pct': (100.0, 100.0),
        'journal_entries': (19, 50),
        'crush_ripe': (0, 10),
        'wake_precision': (3, 3),
        'fossil_cleaned': (5, 20),
    })
    print("Overall maturity: %.3f (%.1f%%)" % (maturity, maturity*100))
    for name, score in sorted(details.items(), key=lambda x: x[1]):
        bar = "#" * int(score * 30)
        print("  %-20s %.3f %s" % (name, score, bar))
