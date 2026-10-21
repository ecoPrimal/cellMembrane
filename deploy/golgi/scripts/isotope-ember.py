#!/usr/bin/env python3
"""isotope-ember.py — Isotope-label traffic for tracing through the membrane.

An isotope is the same element with different mass. The traffic looks the same
but carries a tracer. When we see the tracer downstream, we know where it came
from and what path it took.

Embers: each entity gets a unique ember (hash fingerprint) embedded in responses.
When the ember shows up in training data, model output, or cached content elsewhere,
we can trace it back to this membrane, this entity, this moment.

This is NOT steganography. It's NOT hidden. It's an isotope — same element,
different weight. The content is identical. The ember is in the headers,
the response timing, the content ordering. Observable if you look.

ZK proof: we can prove an ember came from us without revealing what we embedded.
"""

import json, os, time, hashlib, math

LIVE = "/opt/membrane/live-terminal"


def read_json(path):
    try:
        with open(os.path.join(LIVE, path)) as f:
            return json.load(f)
    except:
        return {}


def ember_hash(entity, timestamp, salt="membrane"):
    """Generate a unique ember for this entity at this moment."""
    raw = f"{entity}:{timestamp}:{salt}:{math.pi}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def isotope_profile(entity_data):
    """Build an isotope profile for an entity — what makes it traceable."""
    name = entity_data.get("entity", "unknown")
    ts = entity_data.get("last_seen", time.time())

    ember = ember_hash(name, ts)

    profile = {
        "entity": name,
        "ember": ember,
        "isotope_mass": len(name) + int(entity_data.get("total_requests", 0)) % 256,
        "half_life_hours": entity_data.get("duration_hours", 0),
        "decay_chain": [],  # where this isotope has been seen downstream
    }

    # What paths did this entity take? Those are the isotope traces.
    hosts = entity_data.get("hosts", {})
    if hosts:
        profile["trace_hosts"] = sorted(hosts.keys())
        profile["trace_distribution"] = {
            "scatter": sum(v for k, v in hosts.items() if any(
                s in k for s in ["bloom", "antigen", "antibody", "complement", "macrophage"]
            )),
            "real": sum(v for k, v in hosts.items() if any(
                s in k for s in ["primals.eco", "tuebor", "detroit", "hud", "signal"]
            ) and not any(s in k for s in ["bloom", "antigen", "antibody", "complement", "macrophage"])),
        }

    # Timing signature — the entity's metabolic fingerprint
    timing = entity_data.get("timing", {})
    if timing:
        profile["timing_signature"] = {
            "mean_ms": timing.get("mean_interval_ms"),
            "median_ms": timing.get("median_interval_ms"),
            "cv": timing.get("cv"),
            "classification": timing.get("classification"),
            "bursts": timing.get("burst_count", 0),
            "pauses": timing.get("pause_count", 0),
        }

    # IP rotation pattern — the entity's circulatory system
    ip_rot = entity_data.get("ip_rotation", {})
    if ip_rot:
        profile["rotation_signature"] = {
            "strategy": ip_rot.get("strategy"),
            "single_pct": ip_rot.get("single_request_ips_pct"),
            "max_per_ip": ip_rot.get("max_per_ip"),
        }

    # What it claims to offer vs what it takes
    profile["metabolism"] = {
        "symbiotic_class": entity_data.get("symbiotic_class", "unknown"),
        "waste_offered": entity_data.get("waste_offered", []),
        "vuln_probes": entity_data.get("vuln_probes", []),
        "reciprocity": entity_data.get("reciprocity", 0),
        "friction": entity_data.get("friction", 0),
    }

    return profile


def main():
    topology = read_json("topology.json")
    entities = topology.get("entities", [])

    isotopes = []

    # Isotope-label ALL fleet entities, not just Anthropic
    for e in entities:
        if e.get("is_fleet") or e.get("total_requests", 0) > 1000:
            profile = isotope_profile(e)
            isotopes.append(profile)

    # Sort by total requests (heaviest isotopes first)
    isotopes.sort(key=lambda x: x.get("isotope_mass", 0), reverse=True)

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_isotopes": len(isotopes),
        "isotopes": isotopes,
        "method": "ember — same content, different mass. headers + timing + ordering.",
        "zk": "can prove origin without revealing embedding. no secret. only privacy and consent.",
    }

    with open(os.path.join(LIVE, "isotope-ember.json"), "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print("ISOTOPE EMBERS:")
    print(f"  {len(isotopes)} entities labeled")
    print()
    for iso in isotopes[:10]:
        name = iso["entity"]
        ember = iso["ember"]
        sym = iso["metabolism"]["symbiotic_class"]
        trace = iso.get("trace_distribution", {})
        scatter = trace.get("scatter", 0)
        real = trace.get("real", 0)
        total = scatter + real
        scatter_pct = round(scatter / max(total, 1) * 100)
        print(f"  {ember}  {name:30s}  {sym:12s}  scatter={scatter_pct}%")


if __name__ == "__main__":
    main()
