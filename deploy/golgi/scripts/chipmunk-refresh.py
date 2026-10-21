"""chipmunk-refresh.py — the sourdough cache for the family.

Squirrel binary writes the base (ts, wake_level, uptime, requests)
only on membrane announcements, which can stall for days.

This sense script is the sourdough starter — it refreshes ALL stale fields
so the family (squirrel, chipmunk, bingo) and the HUD always see NOW:
  - ts (numeric epoch) — the one everything reads
  - timestamp (ISO string) — for humans
  - wake_level — from wake-cycle
  - human_ips / human_flow — from human.json (the real count)
  - heartbeat — from pulse.json
  - uptime_secs — from squirrel process

72 hours stale means the sourdough died. This keeps it alive.
"""
import json, os, time, subprocess

LIVE = "/opt/membrane/live-terminal"

def load(name):
    try:
        return json.load(open(os.path.join(LIVE, name)))
    except:
        return {}

def main():
    path = os.path.join(LIVE, "chipmunk.json")
    try:
        chipmunk = json.load(open(path))
    except:
        return

    now = time.time()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ═══ REFRESH ts — the numeric epoch everything reads ═══
    chipmunk["ts"] = now
    chipmunk["timestamp"] = now_iso

    # ═══ WAKE from wake-cycle ═══
    wake = load("wake-cycle.json")
    if wake:
        chipmunk["wake_level"] = wake.get("wake_level", chipmunk.get("wake_level", 1.0))

    # ═══ HUMAN from human.json — the real count, not window sessions ═══
    human = load("human.json")
    if human:
        chipmunk["human_ips"] = human.get("human_ips", human.get("unique_humans", 0))
        chipmunk["human_flow"] = human.get("human_flow", 0)

    # ═══ HEARTBEAT from pulse.json ═══
    pulse = load("pulse.json")
    if pulse:
        chipmunk["heartbeat"] = pulse.get("heartbeat", {})

    # ═══ UPTIME from squirrel process ═══
    try:
        result = subprocess.run(
            ["ps", "-o", "etimes=", "-p",
             subprocess.check_output(["pgrep", "-f", "squirrel server"],
                                     text=True).strip().split("\\n")[0]],
            capture_output=True, text=True, timeout=5
        )
        chipmunk["uptime_secs"] = int(result.stdout.strip())
    except:
        pass

    with open(path, "w") as f:
        json.dump(chipmunk, f, separators=(",", ":"))

if __name__ == "__main__":
    main()
