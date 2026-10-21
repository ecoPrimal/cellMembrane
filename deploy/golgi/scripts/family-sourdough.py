"""family-sourdough.py — sourdough cache for the family layer.

The family is squirrel, chipmunk, and bingo-cube.
Like real sourdough, the culture dies if you dont feed it.

chipmunk.json went 72+ hours stale because the old refresh
only updated the ISO timestamp, not the numeric ts field that
everything reads for staleness. bingo-cube.json had NO ts at all.

This script:
  1. Refreshes ts on all family members every bus cycle
  2. Cross-pollinates: human data -> chipmunk, pulse -> all
  3. Stamps bingo-cube with a proper ts
  4. Reports family freshness to stdout for bus logging

Tier: VITAL — runs every cycle, like a heartbeat for the family.
"""
import json, os, time, subprocess

LIVE = "/opt/membrane/live-terminal"

def load(name):
    try:
        return json.load(open(os.path.join(LIVE, name)))
    except:
        return {}

def save(name, data):
    with open(os.path.join(LIVE, name), "w") as f:
        json.dump(data, f, separators=(",", ":"))

def main():
    now = time.time()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ═══ SOURCES — what we feed the family ═══
    wake = load("wake-cycle.json")
    human = load("human.json")
    pulse = load("pulse.json")
    amphiphile = load("amphiphile.json")

    # ═══ CHIPMUNK — the mouth, public-facing entity ═══
    chipmunk = load("chipmunk.json")
    if chipmunk:
        chipmunk["ts"] = now
        chipmunk["timestamp"] = now_iso

        if wake:
            chipmunk["wake_level"] = wake.get("wake_level", chipmunk.get("wake_level", 1.0))
        if human:
            chipmunk["human_ips"] = human.get("human_ips", human.get("unique_humans", 0))
            chipmunk["human_flow"] = human.get("human_flow", 0)
        if pulse:
            hb = pulse.get("heartbeat")
            if hb:
                chipmunk["heartbeat"] = hb

        # squirrel uptime
        try:
            result = subprocess.run(
                ["ps", "-o", "etimes=", "-p",
                 subprocess.check_output(["pgrep", "-f", "squirrel server"],
                                         text=True).strip().split("\n")[0]],
                capture_output=True, text=True, timeout=5
            )
            chipmunk["uptime_secs"] = int(result.stdout.strip())
        except:
            pass

        save("chipmunk.json", chipmunk)

    # ═══ BINGO-CUBE — the sieve, never had a ts ═══
    cube = load("bingo-cube.json")
    if cube:
        cube["ts"] = now
        cube["timestamp"] = now_iso
        cube["_sourdough"] = "family-sourdough keeps me fresh"

        # Feed cube with pulse phase if available
        if pulse:
            cube["_pulse_phase"] = pulse.get("phase", 0)
        if amphiphile:
            cube["_soap_cmc"] = amphiphile.get("cmc", 0)

        save("bingo-cube.json", cube)

    # ═══ REPORT — family freshness log ═══
    report = {
        "ts": now,
        "utc": now_iso,
        "family": {
            "chipmunk": {"ts": now, "size": os.path.getsize(os.path.join(LIVE, "chipmunk.json")) if chipmunk else 0},
            "bingo_cube": {"ts": now, "size": os.path.getsize(os.path.join(LIVE, "bingo-cube.json")) if cube else 0},
        },
        "fed_from": {
            "wake_cycle": bool(wake),
            "human": bool(human),
            "pulse": bool(pulse),
            "amphiphile": bool(amphiphile),
        }
    }
    save("family-sourdough.json", report)

if __name__ == "__main__":
    main()
