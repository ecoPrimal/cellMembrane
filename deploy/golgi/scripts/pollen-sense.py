#!/usr/bin/env python3
"""pollen-sense.py — closes the sensation loop.

The binary transfer:
  proton emits (publish/IndexNow/SEO) -> signal radiates outward
  electron receives (search engine/social) -> crawls back -> appears in access logs
  neutron stores (topology.json) -> classifier identifies the mutualist
  pollen-sense reads the neutron -> measures the RETURN -> writes pollen feed

This is the "hey you its me" -> response -> bidirectional pause.

Null:  nothing (no publish)
Black: proton fires (content pushed, IndexNow pinged)
White: electron responds (Google crawls, Apple visits, Meta loads card)
Null:  pollen feed records the receipt -> system breathes -> pause

The lossy system: not all pollen returns. Parasites eat without responding.
The mutualists are the closed part -- they hear AND respond.
"""

import json
import time
import os

LIVE = "/opt/membrane/live-terminal"


def sense():
    try:
        topo = json.load(open(os.path.join(LIVE, "topology.json")))
    except Exception:
        return None

    entities = topo.get("entities", [])

    mutualists = []
    commensals = []
    parasites = []
    pathogens = []
    null_class = []

    total_in = 0
    total_returned = 0

    for e in entities:
        name = e.get("entity", "?")
        label = e.get("label", name)
        reqs = e.get("total_requests", 0)
        cls = e.get("symbiotic_class", "null")
        honest = e.get("is_honest", False)
        hosts = e.get("hosts", {})
        vitality = e.get("vitality", 0)

        total_in += reqs

        top_surf = {}
        if isinstance(hosts, dict):
            top_surf = dict(
                sorted(
                    hosts.items(),
                    key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                    reverse=True,
                )[:3]
            )

        entry = {
            "name": name,
            "label": label,
            "requests": reqs,
            "honest": honest,
            "vitality": vitality,
            "top_surfaces": top_surf,
        }

        if cls == "mutualist":
            mutualists.append(entry)
            total_returned += reqs
        elif cls == "commensal":
            commensals.append(entry)
            total_returned += reqs
        elif cls == "parasite":
            parasites.append(entry)
        elif cls == "pathogen":
            pathogens.append(entry)
        else:
            null_class.append(entry)

    parasite_consumed = sum(e["requests"] for e in parasites)
    pathogen_consumed = sum(e["requests"] for e in pathogens)
    null_consumed = sum(e["requests"] for e in null_class)
    lost = parasite_consumed + pathogen_consumed + null_consumed

    if total_in > 0:
        return_ratio = total_returned / total_in
        loss_ratio = lost / total_in
    else:
        return_ratio = 0
        loss_ratio = 0

    # Proton last emission
    try:
        proton = json.load(open(os.path.join(LIVE, "proton-pulse.json")))
        last_proton = proton.get("last_perturbation", {}).get("event", "unknown")
        proton_energy = proton.get("perturbation", 0)
    except Exception:
        last_proton = "unknown"
        proton_energy = 0

    # Neutron breathing rate
    try:
        neutron = json.load(open(os.path.join(LIVE, "neutron.json")))
        rpm = neutron.get("breathing", {}).get("rpm", 0)
        radiating = neutron.get("radiating", [])
        stuck = neutron.get("stuck", [])
        crossings = neutron.get("total_crossings", 0)
    except Exception:
        rpm = 0
        radiating = []
        stuck = []
        crossings = 0

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    mut_reqs = sum(e["requests"] for e in mutualists)
    com_reqs = sum(e["requests"] for e in commensals)
    all_returners = sorted(
        mutualists + commensals, key=lambda x: x["requests"], reverse=True
    )

    interp_parts = [
        "lossy" if loss_ratio > 0.5 else "returning",
        str(len(mutualists)) + " mutualists heard the signal",
        str(mut_reqs) + " crawl-backs",
        "Loss: " + "{:.1%}".format(loss_ratio) + " consumed without return",
        "RPM: " + str(rpm),
        "Breathing." if rpm > 0 else "Silent.",
    ]
    interpretation = "System is " + ". ".join(interp_parts)

    pollen = {
        "type": "pollen_sense",
        "ts": now,
        "binary_transfer": {
            "proton_emit": {
                "last_event": last_proton,
                "energy": proton_energy,
                "radiating_surfaces": radiating,
            },
            "electron_return": {
                "mutualists": len(mutualists),
                "mutualist_requests": mut_reqs,
                "commensals": len(commensals),
                "commensal_requests": com_reqs,
                "top_returners": all_returners[:5],
            },
            "loss": {
                "parasites": parasite_consumed,
                "pathogens": pathogen_consumed,
                "null": null_consumed,
                "total_lost": lost,
            },
            "phase": "bidirectional" if (proton_energy > 0 and (mut_reqs > 0 or com_reqs > 0)) else "forward" if proton_energy > 0 else "reverse" if (mut_reqs > 0 or com_reqs > 0) else "null",
            "round_trip_p": round(mut_reqs / max(total_in, 1), 6) if mut_reqs > 0 else 0,
        },
        "ratios": {
            "return_ratio": round(return_ratio, 6),
            "loss_ratio": round(loss_ratio, 6),
            "mutualist_pct": round(mut_reqs / total_in * 100, 3) if total_in else 0,
            "human_pct": round(com_reqs / total_in * 100, 3) if total_in else 0,
            "parasite_pct": round(parasite_consumed / total_in * 100, 3) if total_in else 0,
        },
        "neutron_state": {
            "rpm": rpm,
            "radiating": len(radiating),
            "stuck": len(stuck),
            "total_crossings": crossings,
        },
        "total_requests": total_in,
        "interpretation": interpretation,
    }

    json.dump(pollen, open(os.path.join(LIVE, "pollen.json"), "w"), indent=2)

    # Also update compact particle-model feed
    pm = {
        "particle_model": {
            "proton": {
                "state": "fired" if proton_energy > 0.01 else "decayed",
                "last_event": last_proton,
                "energy": proton_energy,
                "radiating": len(radiating)
            },
            "neutron": {
                "state": "breathing" if rpm > 0 else "silent",
                "rpm": rpm,
                "crossings": crossings,
                "stuck": len(stuck)
            },
            "electron": {
                "state": "returning" if mut_reqs > 0 else "silent",
                "mutualists": len(mutualists),
                "crawl_backs": mut_reqs,
                "human_arrivals": com_reqs
            },
            "loss": {
                "ratio": round(loss_ratio, 5),
                "parasites_pct": round(parasite_consumed / total_in * 100, 1) if total_in else 0,
                "total_lost": lost
            },
            "phase": "bidirectional" if mut_reqs > 0 and com_reqs > 0 else "forward" if mut_reqs > 0 else "reverse" if com_reqs > 0 else "null",
            "interpretation": interpretation
        }
    }
    json.dump(pm, open(os.path.join(LIVE, "particle-model.json"), "w"), indent=2)

    return pollen


if __name__ == "__main__":
    result = sense()
    if result:
        print(result["interpretation"])
    else:
        print("no topology data")
