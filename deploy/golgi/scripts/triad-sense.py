#!/usr/bin/env python3
"""triad-sense.py — full rotation at the HUD/internal rim.

Three vertices lock orientation:
  in   — nucleus (proton / chipmunk looking up)
  out  — HUD glass (windshield)
  edge — the wild one. color bounce. backscatter of the ray.

I/O is the raytrace: out along aqueous, bounce with wavelength, return.
Soap lets organic cross. Mix stays unmixed.
"""

import json, os, time, math

LIVE = "/opt/membrane/live-terminal"


def load(name):
    try:
        with open(os.path.join(LIVE, name)) as f:
            return json.load(f)
    except Exception:
        return {}


def write(name, data):
    path = os.path.join(LIVE, name)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.rename(tmp, path)


def main():
    now = load("now.json")
    bus = load("bus.json")
    amp = load("amphiphile.json")
    bs = load("backscatter.json")
    heart = load("heartbeat.json")
    app = load("appendix.json")
    gut = app.get("gut", {}) if isinstance(app, dict) else {}

    cls = now.get("classification", {})
    flow = now.get("flow", {})
    laws = amp.get("laws", {})
    io = amp.get("io", {})

    total_e = max(cls.get("total", 1) or 1, 1)
    self_n = cls.get("self", 0)
    nonself_n = cls.get("non_self", 0)
    partial_n = cls.get("partial", 0)
    null_n = cls.get("null", 0)
    human = flow.get("human", 0) or heart.get("human_ips", 0)
    bot = flow.get("bot", 0)
    flow_t = max(flow.get("total", 1) or 1, 1)

    cleaned = bs.get("cleaned", 0)
    hostile = bs.get("licensed", 0)
    bs_total = max(bs.get("total", 1) or 1, 1)

    soap_ok = (laws.get("soap") or {}).get("ok", False)
    organic_w = human / flow_t
    self_w = self_n / total_e
    bounce_w = (nonself_n / total_e) + (hostile / bs_total)
    soap_w = 0.12 if soap_ok else 0.0
    partial_w = partial_n / total_e
    null_w = null_n / total_e
    aqueous_w = max(0.0, 1.0 - organic_w - bounce_w - soap_w)

    n_rays = 24
    mix = {
        "self": round(self_w, 4),
        "organic": round(organic_w, 4),
        "soap": round(soap_w, 4),
        "non_self": round(bounce_w, 4),
        "partial": round(partial_w, 4),
        "null": round(null_w, 4),
        "aqueous": round(aqueous_w, 4),
    }

    # allocate integer rays from weights
    kinds = []
    leftover = n_rays
    order = ["soap", "organic", "self", "non_self", "partial", "null", "aqueous"]
    for k in order:
        c = int(round(mix.get(k, 0) * n_rays))
        c = min(c, leftover)
        kinds.extend([k] * c)
        leftover -= c
    kinds.extend(["aqueous"] * leftover)

    triad = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "triad",
        "note": "in + out + edge = full rotation. color bounce = backscatter of the ray.",
        "vertices": {
            "in": {"role": "nucleus", "color": "#ffffff"},
            "out": {"role": "HUD glass", "color": "#8b949e"},
            "edge": {"role": "backscatter", "color": "#58a6ff", "wild": True},
        },
        "laws": {
            "non_miscible": (laws.get("non_miscible") or {}).get("ok"),
            "non_newtonian": (laws.get("non_newtonian") or {}).get("ok"),
            "soap": soap_ok,
            "rotation_locked": True,
        },
        "rheology": {
            "load": bus.get("load"),
            "aperture": bus.get("aperture"),
            "dripping": (bus.get("aperture") or 0) >= 0.10,
        },
        "backscatter": {
            "cleaned": cleaned,
            "cleaning_pct": bs.get("cleaning_pct"),
            "hostile_pct": bs.get("hostile_pct"),
            "licensed": hostile,
        },
        "mix": mix,
        "rays": n_rays,
        "kinds": kinds,
        "io": {
            "input": io.get("input") or {"organic": human, "nutrients": len(gut.get("nutrients") or [])},
            "output": io.get("output") or {"poop": gut.get("poop", [])},
            "through": (io.get("through") or ("soap film" if soap_ok else "bounce")),
        },
        "classification": cls,
        "flow": flow,
    }
    write("triad.json", triad)
    print("TRIAD: locked soap=%s mix organic=%.3f bounce=%.3f cleaned=%s apt=%s through=%s" % (
        soap_ok, mix["organic"], mix["non_self"], cleaned,
        bus.get("aperture"), triad["io"]["through"],
    ))


if __name__ == "__main__":
    main()
