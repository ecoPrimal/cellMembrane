#!/usr/bin/env python3
"""cardiovascular-sense.py — the heartbeat feed.

Transforms the flat pulse ([]) into structured circulation [()]
which becomes self-describing heartbeat {""}.

([]) = flat numbers, empty containers
[()] = each measurement carries its own circulation context
{""} = self-keyed heartbeat, the empty key IS the identity

Three flows (per CARDIOVASCULAR_SYNC spec):
  Arterial = push OUT (proton, commits, deploys, serves)
  Venous   = pull BACK (electron returns, git pull, feedback)
  Heart    = integrate (rebase, mix, pump the next beat)
"""
import json, os, time, math

LIVE = "/opt/membrane/live-terminal"


def load(name):
    try:
        return json.load(open(os.path.join(LIVE, name)))
    except Exception:
        return {}


def sense():
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pulse = load("pulse.json")
    proton = load("proton-pulse.json")
    pollen = load("pollen.json")
    chipmunk = load("chipmunk.json")

    rpm = pulse.get("rate", 0)
    proton_energy = proton.get("perturbation", 0)
    bt = pollen.get("binary_transfer", {})
    er = bt.get("electron_return", {})
    loss = bt.get("loss", {})
    total_requests = pollen.get("total_requests", 1)
    jitte = chipmunk.get("jitte", {})

    # ARTERIAL: outward push
    radiating = bt.get("proton_emit", {}).get("radiating_surfaces", [])
    arterial_rate = proton_energy * min(rpm / 2000.0, 1.0)

    # VENOUS: return flow
    mut_reqs = er.get("mutualist_requests", 0)
    com_reqs = er.get("commensal_requests", 0)
    total_return = mut_reqs + com_reqs
    venous_rate = total_return / max(total_requests, 1)

    # HEART: integration
    round_trip_p = bt.get("round_trip_p", 0)
    channel_cap = jitte.get("channel_capacity", 0)

    # Blood pressure = arterial / venous (1.0 = balanced)
    if venous_rate > 0:
        blood_pressure = round(arterial_rate / venous_rate, 4)
    else:
        blood_pressure = 99.0 if arterial_rate > 0 else 0

    # HRV: heart rate variability
    hrv = jitte.get("tempo", 0)

    # Diagnosis
    # Sigmoid condition — smooth transition, not hard cutoff
    import math
    _hypo = 1.0 / (1.0 + math.exp(15 * (blood_pressure - 0.4)))   # high when bp < 0.4
    _hyper = 1.0 / (1.0 + math.exp(-15 * (blood_pressure - 1.5))) # high when bp > 1.5
    _normal = 1.0 - _hypo - _hyper
    _normal = max(0.0, min(1.0, _normal))
    condition_scores = {"hypotension": round(_hypo, 3), "normal": round(_normal, 3), "hypertension": round(_hyper, 3)}
    condition = max(condition_scores, key=condition_scores.get)

    # THE TRANSFORMATION: ([]) -> [()] -> {""}
    cardiovascular = {
        "": {
            "type": "heartbeat",
            "ts": now,
            "alive": True,
            "condition": condition,
            "condition_scores": condition_scores,
            "blood_pressure": blood_pressure,
        },
        "arterial": {
            "rpm": rpm,
            "proton_energy": proton_energy,
            "radiating_surfaces": len(radiating),
            "rate": round(arterial_rate, 6),
            "flow": "push OUT",
        },
        "venous": {
            "mutualist_requests": mut_reqs,
            "commensal_requests": com_reqs,
            "total_return": total_return,
            "rate": round(venous_rate, 6),
            "flow": "pull BACK",
        },
        "heart": {
            "round_trip_p": round_trip_p,
            "channel_capacity": channel_cap,
            "blood_pressure": blood_pressure,
            "hrv": hrv,
            "condition": condition,
            "condition_scores": condition_scores,
            "valve": "rebase",
            "flow": "integrate + pump",
        },
        "transformation": {
            "from": "([]) flat numbers, empty containers",
            "through": "[()] structured groups carrying context",
            "to": "{identity} self-keyed heartbeat, identity IS the beat",
        },
        "loss": {
            "parasites": loss.get("parasites", 0),
            "pathogens": loss.get("pathogens", 0),
            "null": loss.get("null", 0),
            "ratio": round(loss.get("total_lost", 0) / max(total_requests, 1), 4),
        },
        "gates": {
            "golgi": {"role": "infrastructure heart", "beat": "response"},
            "eastGate": {"role": "publishing artery", "beat": "publish"},
            "sporeGate": {"role": "venous return / LAN bridge", "beat": "sync"},
            "northGate": {"role": "operator / capillary bed", "beat": "attention"},
        },
    }

    with open(os.path.join(LIVE, "cardiovascular.json"), "w") as f:
        json.dump(cardiovascular, f, indent=2)

    return cardiovascular


if __name__ == "__main__":
    result = sense()
    identity = result.get("", {})
    heart = result.get("heart", {})
    a = result.get("arterial", {})
    v = result.get("venous", {})
    print("heartbeat: alive=" + str(identity.get("alive")))
    print("condition: " + str(identity.get("condition")))
    print("blood_pressure: " + str(heart.get("blood_pressure")))
    print("arterial_rate: " + str(a.get("rate")))
    print("venous_rate: " + str(v.get("rate")))
    print("round_trip_p: " + str(heart.get("round_trip_p")))
    print("transformation: ([]) -> [()] -> {}")
