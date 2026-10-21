"""wake-cycle-sense.py — The metabolism squirrel doesn't have.

Squirrel's wake_level is pinned at 1.0 — it has no metabolism,
no fatigue, no rest cycle. This sense script gives it one.

Three digits. Pi precision. Range {0.000} to {1.000}.
The extremes ARE the boundaries — you don't live there:
  0.000 = null  — truly off, no signal, the zero
  1.000 = full  — every sense firing, the one
Everything between is the living spectrum:
  (0.001 - 0.200) sleep  — minimal processing, deep rest
  (0.201 - 0.400) rest   — recovering, low activity
  (0.401 - 0.600) pause  — waiting, aware but not acting
  (0.601 - 0.800) wake   — active, processing normally
  (0.801 - 0.999) full   — peak activity, approaching the one

The wake level is computed from:
  - presence observer's wake_depth (real measurement)
  - jitte tempo (rhythm of the system)
  - cardiovascular HRV (heart rate variability)
  - time of day (circadian)
  - human activity (are visitors present?)
  - perturbation (how much is changing?)

"Life finds a way" — but life also sleeps.
"""
import json, os, time, math

def sigmoid(x, center=0.5, steepness=10):
    """S-curve: smooth 0->1 transition centered at 'center'."""
    return 1.0 / (1.0 + math.exp(-steepness * (x - center)))

def phase_blend(value):
    """Compute wake phase as sigmoid blend, not hard cutoff.
    Returns (dominant_phase, activation, all_phases)."""
    phases = {
        'sleep': sigmoid(value, 0.1, 20) * (1 - sigmoid(value, 0.3, 15)),
        'rest':  sigmoid(value, 0.3, 15) * (1 - sigmoid(value, 0.5, 12)),
        'pause': sigmoid(value, 0.5, 12) * (1 - sigmoid(value, 0.7, 10)),
        'wake':  sigmoid(value, 0.7, 10) * (1 - sigmoid(value, 0.9, 8)),
        'full':  sigmoid(value, 0.9, 8),
    }
    if value <= 0.001:
        return ('null', 0.0, phases)
    if value >= 0.999:
        return ('null', 0.0, phases)  # 1.000 wraps
    dominant = max(phases, key=phases.get)
    return (dominant, round(phases[dominant], 3), phases)


LIVE = '/opt/membrane/live-terminal'

def main():
    # Read all signals
    try:
        chipmunk = json.load(open(os.path.join(LIVE, 'chipmunk.json')))
    except:
        chipmunk = {}

    try:
        cv = json.load(open(os.path.join(LIVE, 'cardiovascular.json')))
    except:
        cv = {}

    try:
        pt = json.load(open(os.path.join(LIVE, 'passage-totality.json')))
    except:
        pt = {}

    try:
        dash = json.load(open(os.path.join(LIVE, 'dashboard.json')))
    except:
        dash = {}

    # Extract signals
    jitte = chipmunk.get('jitte', {})
    tempo = jitte.get('tempo', 0.5)
    perturbation = jitte.get('perturbation', 0)
    observer_fraction = jitte.get('observer_fraction', 0)

    heart = cv.get('heart', {})
    hrv = heart.get('hrv', 0.5)
    blood_pressure = heart.get('blood_pressure', 0.5)

    human_ips = dash.get('human_ips', 0)
    rps = dash.get('rps', 0)

    # Presence observer's real wake_depth
    membrane_list = chipmunk.get('membrane', [])
    wake_depth = 0.5
    wake_factors = {}
    for m in membrane_list:
        if m.get('primal') == 'presence-observer':
            tense = m.get('metadata', {}).get('tense', {})
            self_is = tense.get('self', {}).get('is', {})
            wake_depth = self_is.get('wake_depth', 0.5)
            wake_factors = self_is.get('wake_factors', {})
            break

    # Circadian signal — UTC hour with minute fraction for smoother curve
    now = time.gmtime()
    hour_frac = now.tm_hour + now.tm_min / 60.0
    circadian = 0.5 + 0.5 * math.sin((hour_frac - 5) * math.pi / 12)
    circadian = max(0.0, min(1.0, circadian))

    # Human activity signal
    human_signal = min(1.0, human_ips / 5000) if human_ips > 0 else 0.0

    # Compute wake as weighted blend
    weights = {
        'wake_depth': 0.30,
        'tempo': 0.15,
        'hrv': 0.10,
        'circadian': 0.15,
        'human_activity': 0.20,
        'perturbation_boost': 0.10,
    }

    signals = {
        'wake_depth': wake_depth,
        'tempo': tempo,
        'hrv': hrv,
        'circadian': circadian,
        'human_activity': human_signal,
        'perturbation_boost': min(1.0, perturbation * 10),
    }

    raw_wake = sum(signals[k] * weights[k] for k in weights)

    # Clamp to {0.000} — {1.000}
    raw_wake = max(0.0, min(1.0, raw_wake))

    # Three digits — pi precision
    wake_3d = round(raw_wake, 3)

    # Classify phase — sigmoid blend, not hard cutoff
    phase, activation, phase_blend_values = phase_blend(wake_3d)
    # Round blend values for output
    phase_activations = {k: round(v, 3) for k, v in phase_blend_values.items()}

    cycle = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'wake_level': wake_3d,
        'phase': phase,
        'range': '{0.000} — {1.000}',
        'squirrel_static': chipmunk.get('wake_level', 1.0),
        'presence_wake_depth': round(wake_depth, 3),
        'signals': {k: round(v, 3) for k, v in signals.items()},
        'weights': weights,
        'wake_factors': {k: round(v, 3) for k, v in wake_factors.items()} if wake_factors else {},
        'circadian_hour_utc': round(hour_frac, 2),
        'activation': activation,
        'phase_activations': phase_activations,
        'note': '0 and 1 are the boundaries. sigmoid, not step.',
    }

    with open(os.path.join(LIVE, 'wake-cycle.json'), 'w') as f:
        json.dump(cycle, f, indent=2)

if __name__ == '__main__':
    main()
