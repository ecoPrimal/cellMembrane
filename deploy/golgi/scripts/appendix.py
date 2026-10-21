#!/usr/bin/env python3
"""appendix.py — Vestigial pocket. Gallstone, sourdough, silt, gut, crevasse.

Gut is not a python colon. Disk pressure is I/O on the bingo maze:
  occupied  = holding nutrients
  absorbing = filling, extract before lithify
  emitting  = excreted poop
  (null)    = cooled empty cell
Nutrients stay. Poop leaves. The maze sorts.
"""

import json, os, time, subprocess

LIVE = "/opt/membrane/live-terminal"
FOSSILS = "/opt/membrane/fossils"
MERGED = "/opt/membrane/merged"


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def file_age_h(path):
    try:
        return (time.time() - os.path.getmtime(path)) / 3600
    except Exception:
        return 999


def main():
    gallstones = []
    if os.path.isdir(FOSSILS):
        for f in sorted(os.listdir(FOSSILS)):
            if f.endswith(".json"):
                path = os.path.join(FOSSILS, f)
                size = os.path.getsize(path)
                age_h = file_age_h(path)
                data = read_json(path)
                nutrients = 0
                if isinstance(data, dict):
                    nutrients = len([
                        k for k, v in data.items()
                        if v not in (0, "", [], {}, None)
                    ])
                gallstones.append({
                    "name": f,
                    "size": size,
                    "age_h": round(age_h, 1),
                    "nutrients": nutrients,
                    "compostable": nutrients > 3,
                })

    sourdough = []
    if os.path.isdir(MERGED):
        for f in sorted(os.listdir(MERGED)):
            path = os.path.join(MERGED, f)
            size = os.path.getsize(path)
            code = open(path).read()
            functions = code.count("def ")
            sourdough.append({
                "name": f,
                "size": size,
                "functions": functions,
                "culture": "absorbed — nutrients returned to cardiovascular",
            })

    silt = []
    bus = read_json(os.path.join(LIVE, "bus.json"))
    cr = read_json(os.path.join(LIVE, "counter-rotation.json"))
    isotopes = read_json(os.path.join(LIVE, "isotope-ember.json"))

    silt.append({
        "finding": "bus architecture replaces beat-counter",
        "status": "live — needs 24h stability validation",
        "evidence": "bus pulse=%d, aperture=%.2f" % (bus.get("pulse", 0), bus.get("aperture", 0)),
    })
    silt.append({
        "finding": "counter-rotation spinning",
        "status": "live — needs wateringHole conflict check",
        "evidence": "%d gates fresh, %d stale" % (
            len(cr.get("exhaust", {}).get("fresh_gates", [])),
            len(cr.get("exhaust", {}).get("stale_gates", [])),
        ),
    })
    silt.append({
        "finding": "isotope embers on 12 fleet entities",
        "status": "live — decay chains empty (no downstream sightings yet)",
        "evidence": "%d isotopes, anthropic ember=86ee8b754998b3f1" % isotopes.get("total_isotopes", 0),
    })
    silt.append({
        "finding": "provenance braid frozen 10+ days",
        "status": "blocked — artisan pipeline not flowing",
        "evidence": "braid.jsonl: 1 entry, last Oct 9",
    })

    # Gut: disk I/O through bingo maze
    disk = {}
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        pct = round((1 - free / total) * 100, 1)
        disk = {"used_pct": pct, "free_gb": round(free / 1e9, 2)}
    except Exception:
        pct = 0

    excreted = []
    if pct >= 80:
        maze_state, maze_note = "emitting", "RED — excrete poop"
        try:
            r = subprocess.run(
                ["python3", "/opt/membrane/disk-fossils.py"],
                capture_output=True, text=True, timeout=60,
            )
            excreted.append(r.stdout.strip()[:200])
        except Exception as e:
            excreted.append(str(e)[:120])
    elif pct >= 70:
        maze_state, maze_note = "absorbing", "YELLOW — filling. extract before lithify"
    elif pct > 0:
        maze_state, maze_note = "occupied", "GREEN — holding. nutrients in"
    else:
        maze_state, maze_note = "(null)", "cooled"

    gut = {
        "input": "disk pressure",
        "output": maze_state,
        "disk": disk,
        "nutrients": [g["name"] for g in gallstones if g.get("compostable")],
        "poop": [g["name"] for g in gallstones if not g.get("compostable")],
        "excreted": excreted,
        "note": maze_note,
    }

    bingo_path = os.path.join(LIVE, "bingo-cube.json")
    cube = read_json(bingo_path)
    if cube:
        occ = cube.setdefault("occupancy", {}).setdefault("π⁰", {})
        prev = occ.get("MEMBRANE", {})
        occ["MEMBRANE"] = {
            "state": maze_state,
            "count": int(disk.get("used_pct", 0)),
            "was": prev.get("count", 0),
            "trajectory": "gut",
            "note": maze_note,
        }
        cube["_fossil"] = False
        cube["_fossil_note"] = "gut I/O revived MEMBRANE cell. maze sorts. not a colon."
        with open(bingo_path, "w") as f:
            json.dump(cube, f, indent=2)

    crevasse = {
        "for": "you and later",
        "note": "this space intentionally left. not empty — waiting.",
        "contains": [],
    }

    appendix = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gallstones": gallstones,
        "sourdough": sourdough,
        "silt": silt,
        "gut": gut,
        "crevasse": crevasse,
        "total_gallstones": len(gallstones),
        "compostable": len([g for g in gallstones if g["compostable"]]),
        "note": "the appendix just exists. gut is maze I/O. you dont need it until you do.",
    }

    with open(os.path.join(LIVE, "appendix.json"), "w") as f:
        json.dump(appendix, f, indent=2)

    print("APPENDIX:")
    print("  GALLSTONES %d (%d compost)" % (len(gallstones), appendix["compostable"]))
    print("  SOURDOUGH %d" % len(sourdough))
    print("  SILT %d" % len(silt))
    print("  GUT %s disk=%s %s" % (maze_state, disk, maze_note))
    print("  CREVASSE: %s" % crevasse["note"])


if __name__ == "__main__":
    main()
