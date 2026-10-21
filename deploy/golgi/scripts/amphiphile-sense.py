#!/usr/bin/env python3
"""amphiphile-sense.py — the soap.

Three chemistries, one pore:

  AQUEOUS  (normal)  — salts, load, aperture, fleet RPM. Mixes with itself.
  ORGANIC  (grease)  — humans, notes, sourdough nutrients, living carbon.
                       Does not mix with aqueous. That's miscibility.
  SOAP     (this)    — amphiphile. One head hydrophilic, one tail lipophilic.
                       Binds grease so organic can cross water without
                       the bulk phases emulsifying.

Non-Newtonian: shear (load) thickens the film (aperture narrows).
Non-miscible: self / non-self / null stay separate phases.
Soap: CMC — critical micelle concentration. Below CMC, organic bounces.
      At CMC, micelles form and organic transits. Above CMC, emulsion
      (null_loss) — that's the mixer breaking.

I/O is the reaction, not a side colon:
  input  = organic inbound (humans, neutron notes, gut nutrients)
  output = excreted (poop, scatter, fleet venous)
  through the soap film. Not around it.
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
    circ = load("circulatory.json")
    heart = load("heartbeat.json")
    app = load("appendix.json")
    neutron = load("neutron.json")
    gut = app.get("gut", {}) if isinstance(app, dict) else {}

    cls = now.get("classification", {})
    flow = now.get("flow", {})
    load_n = float(bus.get("load") or 0)
    apt = float(bus.get("aperture") if bus.get("aperture") is not None else 0)

    # --- phases (miscibility) ---
    aqueous = {
        "name": "aqueous",
        "chemistry": "normal",
        "members": ["fleet", "load", "cpu", "rpm"],
        "fleet_requests": circ.get("arterial_total", 0),
        "bot_flow": flow.get("bot", 0),
        "load": load_n,
    }
    organic = {
        "name": "organic",
        "chemistry": "carbon / living",
        "members": ["human", "notes", "sourdough", "nutrients"],
        "humans": heart.get("human_ips", flow.get("human", 0)),
        "human_flow": flow.get("human", 0),
        "nutrients": gut.get("nutrients", []),
        "notes": (neutron.get("channels") or {}).get("notes", {}).get("total", 0),
    }
    null_loss = circ.get("null_loss", 0) or 0
    total_art = circ.get("arterial_total", 1) or 1
    emulsion = round(null_loss / total_art, 4)  # 1 = fully mixed, 0 = clean split

    self_n = cls.get("self", 0)
    nonself_n = cls.get("non_self", 0)
    null_n = cls.get("null", 0)
    total_e = cls.get("total", 0) or 1
    # miscibility holds if self and non-self are both present and neither ate the count
    miscible_ok = self_n > 0 and nonself_n > 0 and total_e > 10 and cls.get("confidence", 0) > 0.2

    # --- non-Newtonian (rheology) ---
    # shear thickening: higher load → lower aperture. Floor means never a brick.
    newtonian_would = max(0.0, min(1.0, 1.0 - load_n))  # linear
    non_newtonian_ok = apt >= 0.10 and apt <= 1.0
    dripping = apt >= 0.10

    # --- soap / CMC ---
    # organic pressure at the pore vs film capacity
    organic_pressure = organic["human_flow"] / max(1, flow.get("total", 1))
    # CMC: enough soap when aperture is open enough to admit organic_pressure
    cmc = round(organic_pressure, 4)
    micelles = apt >= cmc * 0.5  # film can host organic at this shear
    # emulsion above CMC*2 with high null_loss = soap failure
    soap_ok = micelles and emulsion < 0.85 and miscible_ok

    transit = {
        "input": {
            "organic": organic["humans"],
            "nutrients": len(organic["nutrients"]),
            "notes": organic["notes"],
        },
        "output": {
            "poop": gut.get("poop", []),
            "venous": circ.get("venous_total", 0),
            "null_excreted": null_loss,
        },
        "through": "soap film" if soap_ok else "bounce (no micelle)",
    }

    amphiphile = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "amphiphile",
        "note": "soap binds grease. organic crosses water. bulk phases stay unmixed.",
        "chemistries": {
            "aqueous": aqueous,
            "organic": organic,
            "soap": {
                "name": "amphiphile",
                "heads": "hydrophilic (aperture, salts, load)",
                "tails": "lipophilic (human dwell, notes, nutrients)",
                "cmc": cmc,
                "micelles": micelles,
                "emulsion_index": emulsion,
            },
        },
        "laws": {
            "non_miscible": {
                "ok": miscible_ok,
                "self": self_n,
                "non_self": nonself_n,
                "null": null_n,
                "total": total_e,
                "confidence": cls.get("confidence", 0),
                "emulsion": emulsion,
            },
            "non_newtonian": {
                "ok": non_newtonian_ok,
                "load": load_n,
                "aperture": apt,
                "newtonian_would_be": round(newtonian_would, 3),
                "dripping": dripping,
            },
            "soap": {
                "ok": soap_ok,
                "micelles": micelles,
                "through": transit["through"],
            },
        },
        "io": transit,
    }

    write("amphiphile.json", amphiphile)

    # I/O: revive pulse as living aqueous vital sign (was fossil)
    pulse = load("pulse.json")
    pulse.update({
        "utc": amphiphile["timestamp"],
        "ts": time.time(),
        "rate": flow.get("rate", pulse.get("rate", 0)),
        "human": organic["human_flow"],
        "bot": aqueous["bot_flow"],
        "pulse": now.get("pulse", {}).get("value", pulse.get("pulse", 0)),
        "pulse_trend": now.get("pulse", {}).get("trend", "steady"),
        "pulse_rhythm": now.get("pulse", {}).get("rhythm", pulse.get("pulse_rhythm", 0)),
        "_fossil": False,
        "_fossil_note": "revived by amphiphile I/O — living pulse, not a gallstone",
    })
    write("pulse.json", pulse)

    # bingo MEMBRANE cell: soap state
    cube = load("bingo-cube.json")
    if cube:
        occ = cube.setdefault("occupancy", {}).setdefault("π⁰", {})
        occ["MEMBRANE"] = {
            "state": "occupied" if soap_ok else "absorbing",
            "count": int(apt * 100),
            "was": occ.get("MEMBRANE", {}).get("count", 0),
            "trajectory": "amphiphile",
            "note": transit["through"],
        }
        cube["_fossil"] = False
        write("bingo-cube.json", cube)

    print("AMPHIPHILE: soap=%s miscible=%s nN=%s emulsion=%.3f cmc=%.3f through=%s" % (
        soap_ok, miscible_ok, non_newtonian_ok, emulsion, cmc, transit["through"],
    ))


if __name__ == "__main__":
    main()
