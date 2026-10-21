#!/usr/bin/env python3
"""jitte-sense.py — compute chipmunk jitte from live feeds.
Jitte = the observed timing/information characteristics of the organism.
  tempo: breathing rate normalized to [0,1]
  perturbation: latest proton signal strength
  observer_fraction: humans / total entities seen
  negentropy_bits: log2(active feeds) — information content
  negentropy_per_request: bits per human visitor
  channel_capacity: fraction of feeds that are fresh
"""
import json, math, os, time

LIVE = "/opt/membrane/live-terminal"

def load(name):
    try:
        return json.load(open(os.path.join(LIVE, name)))
    except Exception:
        return {}

def sense():
    neutron = load("neutron.json")
    proton = load("proton-pulse.json")
    topo = load("topology.json")
    campfire = load("campfire.json")
    sss = load("scan_sweep_sort.json")
    chipmunk = load("chipmunk.json")

    # Tempo: rpm normalized. 2min pulse = ~30rpm, breathing organism ~1692rpm
    rpm = neutron.get("breathing", {}).get("rpm", 0)
    tempo_val = min(rpm / 2000.0, 1.0) if rpm else 0

    # Perturbation: latest proton event strength
    pert_val = proton.get("perturbation", 0)

    # Observer fraction: humans from campfire visitors
    rpm_data = campfire.get("rpm", {})
    total_visitors = 0
    total_hits = 0
    if isinstance(rpm_data, dict):
        for site_data in rpm_data.values():
            if isinstance(site_data, dict):
                total_visitors += site_data.get("visitors", 0)
                total_hits += site_data.get("hits", 0)

    entities = topo.get("entities", [])
    total_entities = len(entities)
    # Human fraction: visitors vs total entity count (capped at 1)
    obs_frac = min(total_visitors / max(total_entities, 1), 1.0)

    # Negentropy bits: count active/fresh feeds by age
    feed_files = [f for f in os.listdir(LIVE) if f.endswith(".json")]
    now = time.time()
    fresh = 0
    total_feeds = len(feed_files)
    for fname in feed_files:
        try:
            mtime = os.path.getmtime(os.path.join(LIVE, fname))
            age_min = (now - mtime) / 60
            if age_min < 30:
                fresh += 1
        except:
            pass

    neg_bits = math.log2(fresh) if fresh > 1 else 0
    chan_cap = fresh / total_feeds if total_feeds > 0 else 0

    # Negentropy per request: bits per visitor
    neg_per_req = neg_bits / max(total_visitors, 1)

    jitte = {
        "tempo": round(tempo_val, 4),
        "perturbation": round(pert_val, 4),
        "observer_fraction": round(obs_frac, 4),
        "negentropy_bits": round(neg_bits, 4),
        "negentropy_per_request": round(neg_per_req, 6),
        "channel_capacity": round(chan_cap, 4),
    }

    # Update chipmunk.json jitte section:
    chipmunk["jitte"] = jitte
    chipmunk["jitte_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with open(os.path.join(LIVE, "chipmunk.json"), "w") as f:
        json.dump(chipmunk, f, separators=(",", ":"))

    return jitte

if __name__ == "__main__":
    result = sense()
    print(json.dumps(result, indent=2))
