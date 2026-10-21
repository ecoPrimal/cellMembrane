#!/usr/bin/env python3
"""campfire-culture.py — sourdough the campfire.

Lock-free async culture. The starter feeds the fire.
Now with fossil dough — the dead mixed into the living.

Sources: dashboard + epitopes + passage-totality + campfire + immune-topology (dough)
Output:  campfire-culture.json (alongside campfire.json, no collision)
"""
import json
import time
import os

LIVE = "/opt/membrane/live-terminal"

def load(name):
    try:
        with open(os.path.join(LIVE, name)) as f:
            return json.load(f)
    except:
        return {}

def sense():
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    dashboard = load("dashboard.json")
    epitope = load("epitope_caddy.json")
    passage = load("passage-totality.json")
    campfire = load("campfire.json")
    topology = load("immune-topology.json")

    human_ips = dashboard.get("human_ips", 0)
    human_sessions = dashboard.get("human_sessions", 0)
    fleet_ips = dashboard.get("fleet_ips", 0)

    epitope_map = epitope.get("map", {})
    epitope_count = len(epitope_map) if isinstance(epitope_map, dict) else 0

    totality = passage.get("totality", 0)
    pi_data = passage.get("pi", {})
    journey_pi = pi_data.get("journey_pi", 0) if isinstance(pi_data, dict) else 0
    obs = passage.get("observers", {})
    irrational_remainder = obs.get("irrational_remainder", 0)

    total_stories = campfire.get("total_stories", 0)
    beacons = len(campfire.get("beacons", []))
    surfaces_alive = campfire.get("totality", {}).get("surfaces_alive", 0)

    # The dough — nutrients from fossils, mixed into the culture
    dough = topology.get("dough", {})
    dough_nutrients = dough.get("nutrient_count", 0)
    fossil_count = dough.get("fossil_count", 0)

    # Topology color counts
    counts = topology.get("counts", {})

    culture = {
        "ts": ts,
        "type": "campfire-culture",
        "description": "sourdough — the starter culture, with fossil dough mixed in",
        "fire": {
            "stories": total_stories,
            "beacons": beacons,
            "surfaces_alive": surfaces_alive,
        },
        "humans": {
            "ips": human_ips,
            "sessions": human_sessions,
            "epitope_shapes": epitope_count,
            "fleet_ips": fleet_ips,
            "human_pct": round(human_ips / max(human_ips + fleet_ips, 1) * 100, 2),
        },
        "totality": {
            "passages": totality,
            "journey_pi": round(journey_pi, 4),
            "irrational_remainder": round(irrational_remainder, 6),
        },
        "topology": {
            "white": counts.get("white", 0),
            "black": counts.get("black", 0),
            "purple": counts.get("purple", 0),
            "greyscale": counts.get("greyscale", 0),
            "null": counts.get("grey", 0),
            "total": counts.get("total", 0),
        },
        "dough": {
            "fossil_count": fossil_count,
            "nutrient_count": dough_nutrients,
            "note": "dead is not null. dead is fossil, mixed into the dough."
        },
        "sourdough": {
            "method": "lock-free async",
            "sources": ["dashboard", "epitope_caddy", "passage-totality", "campfire", "immune-topology"],
            "note": "culture lives alongside the fire. fossils feed the living."
        }
    }

    with open(os.path.join(LIVE, "campfire-culture.json"), "w") as f:
        json.dump(culture, f, indent=2)

    print(f"[campfire-culture] human={human_ips} epitopes={epitope_count} "
          f"totality={totality} pi={journey_pi:.4f} "
          f"dough={fossil_count}fossils/{dough_nutrients}nutrients")

if __name__ == "__main__":
    sense()
