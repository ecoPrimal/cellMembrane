#!/usr/bin/env python3
"""bus-rotation.py — Counter-rotating flows on the membrane bus.

Like the Coriolis effect: southern hemisphere water spins opposite to northern.
The bus has TWO rotations that run simultaneously:

CLOCKWISE (stator — steady state):
  GATHER → PROCESS → EMIT
  topology → scan-sweep → braid → deploy
  Reads from the world, processes, pushes outward.
  This is what membrane-bus.py already does.

COUNTER-CLOCKWISE (rotor — reflective):
  EMIT → REFLECT → GATHER
  wateringHole → provenance → braid back into topology
  Reads what we EMITTED (AARs, heads, impulses), braids it back in.
  The provenance terrain chews the data and returns nutrients.

The two rotations are like tides:
  - Clockwise pushes data OUT (arterial)
  - Counter-clockwise pulls lessons BACK (venous)
  - The gradient drives both (staleness = pressure)
  - The aperture (CPU) applies to both

This script handles the COUNTER-CLOCKWISE rotation.
It should run on the same bus schedule as membrane-bus.py.
"""

import json, os, time, subprocess

LIVE = "/opt/membrane/live-terminal"
WATERINGHOLE = "/opt/ecoPrimals/infra/wateringHole"
PROVENANCE = "/opt/membrane/provenance"
LOG = "/var/log/membrane/membrane-pulse.log"


def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write("%s %s\n" % (ts, msg))
    except:
        pass


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def file_age(path):
    try:
        return time.time() - os.path.getmtime(path)
    except:
        return 99999


def main():
    log("counter-rotation: starting venous return")

    # ═══ PHASE 1: Pull wateringHole (what we and others emitted) ═══
    wh_age = file_age(os.path.join(WATERINGHOLE, "heads", "sporeGate.toml"))
    if wh_age > 600:  # stale > 10min
        log("  pulling wateringHole (%.0fs stale)" % wh_age)
        try:
            r = subprocess.run(
                "cd %s && git pull --ff-only origin main" % WATERINGHOLE,
                shell=True, capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                log("  wateringHole: %s" % r.stdout.strip().split('\n')[-1])
            else:
                log("  wateringHole pull FAIL: %s" % r.stderr[:200])
        except Exception as e:
            log("  wateringHole pull ERROR: %s" % e)

    # ═══ PHASE 2: Read what was emitted (the exhaust) ═══
    # Collect recent AARs, impulses, head states
    aars = []
    impulses = []
    heads = {}

    aar_dir = os.path.join(WATERINGHOLE, "aars")
    if os.path.isdir(aar_dir):
        for f in os.listdir(aar_dir):
            if f.endswith('.md') and not os.path.isdir(os.path.join(aar_dir, f)):
                path = os.path.join(aar_dir, f)
                age_h = file_age(path) / 3600
                if age_h < 72:  # last 3 days
                    aars.append({"file": f, "age_h": round(age_h, 1)})

    impulse_dir = os.path.join(WATERINGHOLE, "impulses", "active")
    if os.path.isdir(impulse_dir):
        for f in os.listdir(impulse_dir):
            if f.endswith('.toml'):
                path = os.path.join(impulse_dir, f)
                age_h = file_age(path) / 3600
                impulses.append({"file": f, "age_h": round(age_h, 1)})

    heads_dir = os.path.join(WATERINGHOLE, "heads")
    if os.path.isdir(heads_dir):
        for f in os.listdir(heads_dir):
            if f.endswith('.toml'):
                gate = f.replace('.toml', '')
                path = os.path.join(heads_dir, f)
                age_s = file_age(path)
                heads[gate] = {
                    "age_s": round(age_s),
                    "fresh": age_s < 1800,  # fresh = updated in last 30min
                }

    # ═══ PHASE 3: Braid it back (counter-rotation) ═══
    # What the clockwise rotation EMITTED, we now REFLECT on
    # Compare what we know (topology) with what was documented (AARs)

    topology = read_json(os.path.join(LIVE, "topology.json"))
    assumptions = read_json(os.path.join(LIVE, "assumptions.json"))
    backscatter = read_json(os.path.join(LIVE, "edge-scatter.json"))

    # Count active gates from heads
    fresh_gates = [g for g, h in heads.items() if h.get("fresh")]
    stale_gates = [g for g, h in heads.items() if not h.get("fresh")]

    # Build the counter-rotation output
    counter = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rotation": "counter-clockwise",
        "phase": "venous return",

        # What we found in the exhaust
        "exhaust": {
            "recent_aars": len(aars),
            "active_impulses": len(impulses),
            "gates_reporting": len(heads),
            "fresh_gates": fresh_gates,
            "stale_gates": stale_gates,
            "impulse_files": [i["file"] for i in impulses],
        },

        # What we braided back
        "braided": {
            "topology_entities": topology.get("total_entities", 0),
            "assumptions_tested": assumptions.get("summary", {}).get("total", 0),
            "backscatter_emissions": len(backscatter.get("emissions", {})),
        },

        # Health of the counter-rotation
        "health": {
            "wateringhole_age_s": round(wh_age),
            "provenance_braid_age_s": round(file_age(os.path.join(PROVENANCE, "braid.jsonl"))),
            "freshness": "flowing" if wh_age < 1800 else "stale" if wh_age < 7200 else "blocked",
        },

        # Coriolis: both rotations must spin
        "coriolis": {
            "clockwise": "gather→process→emit (arterial, membrane-bus.py)",
            "counter_clockwise": "emit→reflect→gather (venous, bus-rotation.py)",
            "stator": "topology + scan + braid (steady state)",
            "rotor": "wateringHole + provenance + reflection (reflective)",
        },
    }

    with open(os.path.join(LIVE, "counter-rotation.json"), "w") as f:
        json.dump(counter, f, indent=2)

    log("counter-rotation: done — %d AARs, %d impulses, %d gates (%d fresh, %d stale)" % (
        len(aars), len(impulses), len(heads), len(fresh_gates), len(stale_gates)))

    # Also publish golgi's head to wateringHole
    golgi_head_path = os.path.join(WATERINGHOLE, "heads", "golgiBody.toml")
    try:
        # Read current golgi state
        cv = read_json(os.path.join(LIVE, "cardiovascular.json"))
        bus = read_json(os.path.join(LIVE, "bus.json"))
        maturity = read_json(os.path.join(LIVE, "maturity.json"))

        head_content = """# Auto-published by membrane bus counter-rotation
# This file is owned exclusively by this gate. No other gate writes here.
# Gate: golgiBody | Updated: %s

[meta]
gate = "golgiBody"
updated = "%s"

[health]
blood_pressure = %s
aperture = %s
maturity = %s
bus_pulse = %s
condition = "%s"

[heads]
membrane = "%s"
""" % (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            cv.get("heart", {}).get("blood_pressure", 0),
            bus.get("aperture", 0),
            maturity.get("maturity", 0),
            bus.get("pulse", 0),
            cv.get("", {}).get("condition", "unknown"),
            subprocess.run("cd /opt/membrane && git rev-parse HEAD",
                           shell=True, capture_output=True, text=True, timeout=5
                           ).stdout.strip()[:12],
        )

        with open(golgi_head_path, "w") as f:
            f.write(head_content)

        # Commit and push golgi's head
        subprocess.run(
            "cd %s && git add heads/golgiBody.toml && "
            "git diff --cached --quiet || "
            "git commit -m 'heads/golgiBody: auto-publish by golgiBody' && "
            "git push origin main" % WATERINGHOLE,
            shell=True, capture_output=True, text=True, timeout=30
        )
        log("  golgiBody head published to wateringHole")
    except Exception as e:
        log("  golgiBody head publish ERROR: %s" % e)


if __name__ == "__main__":
    main()
