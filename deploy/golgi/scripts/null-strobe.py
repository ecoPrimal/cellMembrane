#!/usr/bin/env python3
"""null-strobe.py — the void is not empty. it strobes.

Random doors, random backscatters, random connections, random color shifts.
The null intermediate between alive and dead. Serendipity lives here.
Fires every pulse beat. Each flash is different.
"""
import json, os, time, random

LIVE = "/opt/membrane/live-terminal"

def load(name):
    try:
        with open(os.path.join(LIVE, name)) as f:
            return json.load(f)
    except:
        return {}

def sense():
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    random.seed(int(time.time() * 1000))

    campfire = load("campfire.json")
    spectrum = load("color-spectrum.json")
    neutron_cache = load("neutron-cache.json")
    gaia = load("gaia-reflection.json")

    surfaces = [b.get("surface", "?") for b in campfire.get("beacons", [])]
    inner_colors = list(spectrum.get("inner", {}).keys()) or ["red","green","blue"]
    outer_domains = list(spectrum.get("outer", {}).keys()) or ["immune","source"]
    artists = gaia.get("cultural_threads", {}).get("artists_crossing", ["the membrane"])
    ancient = gaia.get("cultural_threads", {}).get("ancient", ["what is alive"])
    modern = gaia.get("cultural_threads", {}).get("modern", ["immune topology"])

    fragments = []
    for ch, data in neutron_cache.get("channels", {}).items():
        msgs = data.get("messages", []) if isinstance(data, dict) else []
        for m in msgs:
            for s in m.get("body", "").replace("\n", ". ").split(". "):
                s = s.strip()
                if 10 < len(s) < 200:
                    fragments.append(s)

    flashes = []
    for _ in range(random.randint(4, 8)):
        ft = random.choice(["door", "door", "backscatter", "backscatter", "connection", "parallax"])
        if ft == "door" and surfaces:
            flashes.append({"type": "door", "surface": random.choice(surfaces), "color": random.choice(inner_colors)})
        elif ft == "backscatter" and fragments:
            flashes.append({"type": "backscatter", "fragment": random.choice(fragments)})
        elif ft == "connection":
            a = random.choice(ancient + modern)
            b = random.choice(artists)
            flashes.append({"type": "iridescence", "from": a, "to": b})
        elif ft == "parallax":
            ic = random.choice(inner_colors)
            od = random.choice(outer_domains)
            flashes.append({"type": "parallax", "inner": ic, "outer": od})

    strobe = {
        "ts": ts, "type": "null-strobe",
        "flash_count": len(flashes), "flashes": flashes,
        "materials": {"surfaces": len(surfaces), "fragments": len(fragments), "artists": len(artists)},
    }

    with open(os.path.join(LIVE, "null-strobe.json"), "w") as f:
        json.dump(strobe, f, indent=2)

    doors = sum(1 for f in flashes if f["type"] == "door")
    scatters = sum(1 for f in flashes if f["type"] == "backscatter")
    print(f"[null-strobe] {len(flashes)} flashes: {doors} doors, {scatters} scatters")

if __name__ == "__main__":
    sense()
