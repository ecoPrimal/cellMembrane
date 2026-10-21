"""bus-cardio.py — the bus knows its own heartbeat.

Totality BPM averaged over time. Systolic and diastolic from load.
Predicts next pulse from outgoing rhythm.
Catch-and-throw: the interval IS the information.

Systolic  = peak load during recent cycles (contraction)
Diastolic = minimum load between cycles (relaxation)
BPM       = totality beats per minute, exponential moving average
Next      = predicted arrival based on outgoing intervals

Written to /opt/membrane/live-terminal/bus-cardio.json
"""
import json, os, time, math

LIVE = "/opt/membrane/live-terminal"
STATE = "/var/lib/membrane/bus-cardio-state.json"

def load_state():
    try:
        return json.load(open(STATE))
    except:
        return {
            "history": [],        # last N pulse timestamps
            "loads": [],          # last N load readings
            "contractions": [],   # last N cycle durations (start to done)
            "ema_interval": 120,  # exponential moving average of interval (seconds)
            "ema_alpha": 0.15,    # EMA smoothing factor
        }

def save_state(s):
    with open(STATE, "w") as f:
        json.dump(s, f)

def main():
    now = time.time()
    state = load_state()

    # Read current bus state
    try:
        bus = json.load(open(os.path.join(LIVE, "bus.json")))
    except:
        return

    pulse_n = bus.get("pulse", 0)
    load = bus.get("load", 0)
    aperture = bus.get("aperture", 0)

    # Record this pulse
    history = state["history"]
    loads = state["loads"]
    contractions = state["contractions"]

    history.append(now)
    loads.append(load)

    # Keep last 60 data points (2 hours at 2-min intervals)
    MAX_HISTORY = 60
    history = history[-MAX_HISTORY:]
    loads = loads[-MAX_HISTORY:]
    contractions = contractions[-MAX_HISTORY:]

    state["history"] = history
    state["loads"] = loads
    state["contractions"] = contractions

    # ═══ INTERVALS — time between pulses ═══
    intervals = []
    for i in range(1, len(history)):
        intervals.append(history[i] - history[i-1])

    # EMA of interval (the totality BPM)
    ema_interval = state.get("ema_interval", 120)
    alpha = state.get("ema_alpha", 0.15)
    if intervals:
        latest_interval = intervals[-1]
        ema_interval = alpha * latest_interval + (1 - alpha) * ema_interval
    state["ema_interval"] = ema_interval

    bpm = 60.0 / ema_interval if ema_interval > 0 else 0
    bph = bpm * 60  # beats per hour

    # ═══ SYSTOLIC / DIASTOLIC — from load readings ═══
    recent_loads = loads[-20:]  # last ~40 min
    systolic = max(recent_loads) if recent_loads else 0
    diastolic = min(recent_loads) if recent_loads else 0
    # Mean Arterial Pressure: MAP = diastolic + 1/3 * (systolic - diastolic)
    # (same formula as real blood pressure)
    pulse_pressure = systolic - diastolic
    map_pressure = diastolic + pulse_pressure / 3.0

    # ═══ NEXT PULSE PREDICTION ═══
    # Based on EMA interval from last pulse
    last_pulse_ts = history[-1] if history else now
    predicted_next = last_pulse_ts + ema_interval
    eta_seconds = predicted_next - now

    # ═══ CONTRACTION / RELAXATION ═══
    # Read from dispatch state for cycle elapsed time
    try:
        dispatch = json.load(open("/var/lib/membrane/pulse-dispatch.json"))
        # The elapsed time between bus start and bus done IS the contraction
        # We infer from last_pulse timestamp and "bus done" timing
    except:
        dispatch = {}

    # ═══ CONDITION — like a real heart ═══
    if map_pressure < 1.0:
        condition = "hypotension"      # too quiet
    elif map_pressure < 2.0:
        condition = "normal"           # healthy range
    elif map_pressure < 4.0:
        condition = "elevated"         # working hard
    elif map_pressure < 6.0:
        condition = "hypertension-1"   # stressed
    else:
        condition = "hypertension-2"   # critical

    # ═══ RHYTHM QUALITY — regularity of intervals ═══
    if len(intervals) >= 3:
        mean_int = sum(intervals) / len(intervals)
        variance = sum((x - mean_int)**2 for x in intervals) / len(intervals)
        std_int = math.sqrt(variance)
        # HRV = heart rate variability (coefficient of variation)
        hrv = std_int / mean_int if mean_int > 0 else 0
        if hrv < 0.1:
            rhythm = "regular"        # metronomic
        elif hrv < 0.3:
            rhythm = "sinus"          # healthy variation
        elif hrv < 0.6:
            rhythm = "irregular"      # some skips
        else:
            rhythm = "arrhythmic"     # chaotic
    else:
        hrv = 0
        rhythm = "establishing"

    # ═══ OUTPUT ═══
    cardio = {
        "ts": now,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pulse": pulse_n,
        "bpm": round(bpm, 4),
        "bph": round(bph, 1),
        "interval_ema_s": round(ema_interval, 1),
        "systolic": round(systolic, 3),
        "diastolic": round(diastolic, 3),
        "map": round(map_pressure, 3),
        "pulse_pressure": round(pulse_pressure, 3),
        "condition": condition,
        "rhythm": rhythm,
        "hrv": round(hrv, 4),
        "next_pulse_eta_s": round(max(0, eta_seconds), 0),
        "next_pulse_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(predicted_next)),
        "samples": len(history),
        "aperture": round(aperture, 3),
        "_note": "systolic/diastolic = peak/trough CPU load. MAP = diastolic + 1/3 pulse pressure. BPM = bus beats per minute."
    }

    with open(os.path.join(LIVE, "bus-cardio.json"), "w") as f:
        json.dump(cardio, f, indent=2)

    save_state(state)

if __name__ == "__main__":
    main()
