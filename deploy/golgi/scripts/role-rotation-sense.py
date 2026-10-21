#!/usr/bin/env python3
"""role-rotation-sense.py — 3 players, 4 chairs, null rotates.

Mom, Dad, Chipmunk rotate through:
  Ed (teach/sing) — proton emission, content creation
  Barry (gather/move) — pollen return, outreach, collection
  Krogan (defend/search) — classification, grading, the lens
  Watch (sit/observe) — null, pause, breathe, the eye

The empty chair IS the null space. It rotates with the game.
"""

import json
import time
import os

LIVE = "/opt/membrane/live-terminal"


def sense_rotation():
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    try:
        proton = json.load(open(os.path.join(LIVE, "proton-pulse.json")))
        proton_energy = proton.get("perturbation", 0)
    except Exception:
        proton_energy = 0

    try:
        pollen = json.load(open(os.path.join(LIVE, "pollen.json")))
        er = pollen.get("binary_transfer", {}).get("electron_return", {})
        mut_reqs = er.get("mutualist_requests", 0)
        human_reqs = er.get("commensal_requests", 0)
    except Exception:
        mut_reqs = 0
        human_reqs = 0

    try:
        neutron = json.load(open(os.path.join(LIVE, "neutron.json")))
        rpm = neutron.get("breathing", {}).get("rpm", 0)
    except Exception:
        rpm = 0

    try:
        talos = json.load(open(os.path.join(LIVE, "talos.json")))
        graded = talos.get("total_entities", 0)
    except Exception:
        graded = 0

    # Role activity levels (0 to 1)
    ed_level = min(proton_energy / 0.1, 1.0) if proton_energy > 0 else 0
    barry_level = min(mut_reqs / 5000, 1.0) if mut_reqs > 0 else 0
    krogan_level = min(graded / 7000, 1.0) if graded > 0 else 0
    watch_level = 1.0  # watcher never stops

    levels = {
        "ed": ed_level,
        "barry": barry_level,
        "krogan": krogan_level,
        "watch": watch_level,
    }

    # Find the null chair (lowest activity)
    null_chair = min(levels, key=levels.get)

    # Game states
    game = {
        "moving": barry_level > 0.1,
        "napping": rpm < 100,
        "watching": watch_level > 0.5,
        "singing": ed_level > 0.1,
        "searching": krogan_level > 0.1,
    }

    rotation = {
        "ts": now,
        "levels": levels,
        "null_chair": null_chair,
        "game": game,
        "rpm": rpm,
    }

    # Load or create history
    path = os.path.join(LIVE, "role-rotation.json")
    try:
        existing = json.load(open(path))
    except Exception:
        existing = {}

    existing["ts"] = now
    existing["current"] = rotation
    existing["null_chair"] = null_chair

    # Keep rotation history (last 20)
    history = existing.get("history", [])
    history.append(rotation)
    existing["history"] = history[-20:]

    json.dump(existing, open(path, "w"), separators=(",", ":"))

    active_count = sum(1 for v in levels.values() if v > 0.1)
    game_verbs = [k for k, v in game.items() if v]

    print(
        "roles: "
        + str(active_count)
        + "/4 active, null="
        + null_chair
        + ", game: "
        + "+".join(game_verbs)
    )


if __name__ == "__main__":
    sense_rotation()
