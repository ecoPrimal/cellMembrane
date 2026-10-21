#!/usr/bin/env python3
"""sourdough-topology.py — the real immune topology.

Dead is not null. Dead is fossil, mixed into the dough.
Inactive is numeric range. Grey is null.
White is alive. Black is fossil. Purple is machinery.

[sSs] [?O!)(zZZ}] ? PPPPPPP PURPLE!
"""
import os, time, json, math

LIVE = "/opt/membrane/live-terminal"

PURPLE = {
    "scan_sweep_sort.json", "membrane-pulse.json", "topology.json",
    "topology-abstract.json", "immune-topology.json", "particle-model.json",
    "null-mirror.json", "pi-ranges.json", "state.json", "cron-health.json",
    "falsification.json",
}

def extract_dough(fossils_data):
    """Extract nutrients from fossil feeds — mix the dead into the dough."""
    all_nums = {}
    for name, d in fossils_data.items():
        for k, v in d.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (int, float)):
                all_nums.setdefault(k, []).append(v)
    
    nutrients = {}
    for k, vals in sorted(all_nums.items()):
        if len(vals) > 1:
            nutrients[k] = {
                "sum": round(sum(vals), 4),
                "avg": round(sum(vals) / len(vals), 4),
                "sources": len(vals)
            }
        else:
            nutrients[k] = vals[0]
    return nutrients

def classify():
    now = time.time()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    white = []
    black = []
    black_data = {}
    grey = []
    purple = []
    greyscale = []
    
    all_feeds = []
    
    for f in sorted(os.listdir(LIVE)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(LIVE, f)
        age_s = now - os.path.getmtime(path)
        age_min = age_s / 60
        size = os.path.getsize(path)
        
        try:
            d = json.load(open(path))
            is_fossil = isinstance(d, dict) and d.get("_fossil")
            is_dict = isinstance(d, dict)
            key_count = len(d) if is_dict else (len(d) if isinstance(d, list) else 0)
        except:
            d = {}
            is_fossil = False
            is_dict = False
            key_count = 0
        
        half_life = 5.0
        activity = round(math.exp(-0.693 * age_min / half_life), 4)
        
        if f in PURPLE:
            color = "purple"
            purple.append(f)
        elif is_fossil:
            color = "black"
            black.append(f)
            black_data[f] = d
        elif size == 0 or key_count == 0:
            color = "grey"
            grey.append(f)
        elif activity >= 0.5:
            color = "white"
            white.append(f)
        else:
            color = "greyscale"
            greyscale.append({"feed": f, "activity": activity})
        
        all_feeds.append({
            "name": f,
            "color": color,
            "activity": activity,
            "age_min": round(age_min, 1),
            "size": size,
        })
    
    # Extract the dough from fossils
    nutrients = extract_dough(black_data)
    
    topology = {
        "ts": ts,
        "type": "sourdough-topology",
        "model": {
            "white": "⬜ alive — breathing with the beat",
            "black": "⬛ fossil — dead but preserved, mixed into the dough",
            "grey": "🔘 null — truly unknown, no signal, the void",
            "purple": "🟣 machinery — [sSs] code, engines, hard infrastructure",
            "greyscale": "▫️ inactive — numeric range 0.0 (null) → 1.0 (alive)"
        },
        "counts": {
            "white": len(white),
            "black": len(black),
            "grey": len(grey),
            "purple": len(purple),
            "greyscale": len(greyscale),
            "total": len(all_feeds),
        },
        "white": white,
        "black": black,
        "grey": grey,
        "purple": purple,
        "greyscale": sorted(greyscale, key=lambda x: -x["activity"]),
        "dough": {
            "description": "nutrients extracted from fossils — the dead feeds the living",
            "fossil_count": len(black),
            "nutrient_count": len(nutrients),
            "nutrients": nutrients,
        },
        "health": {
            "accounted_pct": round((len(white) + len(black) + len(purple) + len(greyscale)) / len(all_feeds) * 100, 1) if all_feeds else 0,
            "null_count": len(grey),
            "note": "dead is not null. dead is fossil, mixed into the dough."
        },
        "feeds": all_feeds,
    }
    
    with open(os.path.join(LIVE, "immune-topology.json"), "w") as f:
        json.dump(topology, f, indent=2)
    
    # Visual output
    print("[sSs] [?O!)(zZZ}] ? PPPPPPP PURPLE!")
    print()
    print("  ⬜ WHITE    %-3d  alive, breathing with the beat" % len(white))
    print("  ⬛ BLACK    %-3d  fossil, mixed into the dough" % len(black))
    print("  🟣 PURPLE   %-3d  [sSs] machinery, code, engines" % len(purple))
    print("  ▫️  SCALE    %-3d  inactive (numeric range)" % len(greyscale))
    print("  🔘 NULL     %-3d  void, grey, no signal" % len(grey))
    print("  ── TOTAL    %-3d  feeds" % len(all_feeds))
    print()
    
    if greyscale:
        print("  GREYSCALE (0.0 null → 1.0 alive):")
        for g in sorted(greyscale, key=lambda x: -x["activity"]):
            a = g["activity"]
            bar = "█" * int(a * 20) + "░" * (20 - int(a * 20))
            print("    %.3f [%s] %s" % (a, bar, g["feed"]))
        print()
    
    print("  DOUGH: %d nutrients from %d fossils" % (len(nutrients), len(black)))
    print("  dead is not null. dead is fossil, mixed into the dough.")
    print("  health: %.0f%% accounted" % topology["health"]["accounted_pct"])

if __name__ == "__main__":
    classify()
