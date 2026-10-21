"""tense-tensor.py — tensors for the epitope classifier.

The old tense was scalar: {is: 73419, was: 11058, will_be: 6381}
81% jammed in "is". IMMUNE and SCIENCE fell through without learning.
Entropy 0.887/1.585 — barely half the information capacity.

The fix: TENSORS, not tenses.
A tensor tracks the RELATIONSHIPS between dimensions:
  - epitope (IMMUNE, TOPOLOGY, MEMBRANE, ...)
  - tense (is, was, will_be, isnt, wasnt, willneverbe)
  - vocal (the bingo cube classification: attention × curiosity × interaction)
  - tree depth (how deep in the classification hierarchy)

Systolic = transition rate INTO a state (pressure building)
Diastolic = transition rate OUT OF a state (pressure releasing)
The is/was jam = systolic >> diastolic. No release.

Fix: track transitions, not just counts. Build trees from transition patterns.

I/O: reads chipmunk.json, epitope-history.json, bingo-cube.json, passage-totality.json
     writes tense-tensor.json
"""
import json, os, time, math

LIVE = "/opt/membrane/live-terminal"

def pi_fig(value):
    """Express a number in pi figures: find the best pi^n scale."""
    PI = math.pi
    if value == 0:
        return "0"
    abs_v = abs(value)
    sign = "-" if value < 0 else ""
    # Find the best pi power where coefficient is 1-10
    for p in range(0, 8):
        coeff = abs_v / PI**p
        if 0.5 <= coeff < 10.0:
            if p == 0:
                return "%s%.2f" % (sign, coeff)
            elif p == 1:
                return "%s%.2f\u03c0" % (sign, coeff)
            else:
                return "%s%.2f\u03c0^%d" % (sign, coeff, p)
    return "%s%.2f" % (sign, abs_v)
STATE = "/var/lib/membrane/tense-tensor-state.json"

def load(name):
    try:
        return json.load(open(os.path.join(LIVE, name)))
    except:
        return {}

def load_state():
    try:
        return json.load(open(STATE))
    except:
        return {
            "transitions": {},      # epitope -> {from_tense -> {to_tense -> count}}
            "last_snapshot": {},     # epitope -> {tense -> count} from last cycle
            "tensor_history": [],    # last N tensor snapshots for BPM averaging
            "ema_alpha": 0.2,
        }

def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(s, f)

def main():
    now = time.time()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state = load_state()

    chipmunk = load("chipmunk.json")
    totality = load("passage-totality.json")
    cube = load("bingo-cube.json")
    cardio = load("bus-cardio.json")

    # ═══ CURRENT TENSE SNAPSHOT ═══
    # Per-epitope is/nearby/was from chipmunk membrane
    current = {}
    for mem in chipmunk.get("membrane", []):
        md = mem.get("metadata", {})
        et = md.get("epitope_tense", {})
        for epi, counts in et.items():
            current[epi] = {
                "is": counts.get("is", 0),
                "nearby": counts.get("nearby", 0),
                "was": counts.get("was", 0),
            }

    # Global tense from totality
    tense_global = totality.get("tense", {})

    # ═══ TRANSITIONS — detect is→was, was→will_be, etc. ═══
    last = state.get("last_snapshot", {})
    transitions = state.get("transitions", {})

    for epi, cur in current.items():
        prev = last.get(epi, {})
        if not prev:
            continue

        if epi not in transitions:
            transitions[epi] = {}

        # Detect transitions by delta
        is_delta = cur.get("is", 0) - prev.get("is", 0)
        was_delta = cur.get("was", 0) - prev.get("was", 0)
        nearby_delta = cur.get("nearby", 0) - prev.get("nearby", 0)

        # If "is" decreased and "was" increased → is→was transition
        if is_delta < 0 and was_delta > 0:
            t = transitions[epi].get("is_to_was", 0)
            transitions[epi]["is_to_was"] = t + abs(is_delta)

        # If "was" decreased and "is" increased → was→is transition (revival)
        if was_delta < 0 and is_delta > 0:
            t = transitions[epi].get("was_to_is", 0)
            transitions[epi]["was_to_is"] = t + abs(was_delta)

        # If "nearby" increased → approaching, potential will_be
        if nearby_delta > 0:
            t = transitions[epi].get("approaching", 0)
            transitions[epi]["approaching"] = t + nearby_delta

        # If "nearby" decreased and "is" increased → nearby→is (arrived)
        if nearby_delta < 0 and is_delta > 0:
            t = transitions[epi].get("arrived", 0)
            transitions[epi]["arrived"] = t + abs(nearby_delta)

        # If both is and nearby decreased → departed entirely
        if is_delta < 0 and nearby_delta < 0:
            t = transitions[epi].get("departed", 0)
            transitions[epi]["departed"] = t + abs(is_delta)

    state["last_snapshot"] = current
    state["transitions"] = transitions

    # ═══ TENSOR — epitope × tense × vocal ═══
    # Each epitope gets a tensor row with:
    #   counts: is, nearby, was (current)
    #   rates: systolic (into is), diastolic (out of is)
    #   vocal: bingo cube ACI score
    #   tree_depth: classification depth
    tensor = {}
    for epi, cur in current.items():
        is_c = cur.get("is", 0)
        nearby_c = cur.get("nearby", 0)
        was_c = cur.get("was", 0)
        total = is_c + nearby_c + was_c

        # Transition rates
        trans = transitions.get(epi, {})
        systolic = trans.get("arrived", 0) + trans.get("was_to_is", 0)   # pressure IN
        diastolic = trans.get("is_to_was", 0) + trans.get("departed", 0)  # pressure OUT

        # Status from transitions — the tensor tense, not the scalar tense
        # "fell" means: had is > 0 in the past, now is=0, and diastolic > systolic
        #   (more pressure OUT than IN — the classifier didn't learn, it just leaked)
        # "recovering" means: fell but nearby > 0 (approaching again)
        # "approaching" means: never had is, but nearby > 0
        # "present" means: is > 0 (actively classified)
        if is_c > 0:
            status = "present"
        elif diastolic > 0 and nearby_c > 0:
            status = "recovering"  # fell but coming back (nearby)
        elif diastolic > 0 and nearby_c == 0:
            status = "fell"        # fell through, not returning
        elif nearby_c > 0:
            status = "approaching"
        elif was_c > 0:
            status = "dormant"     # only in was, no transitions
        else:
            status = "null"

        # Vocal — bingo cube ACI classification
        # Attention = is/total, Curiosity = nearby/total, Interaction = transitions/total
        attention = is_c / max(1, total)
        curiosity = nearby_c / max(1, total)
        interaction = (systolic + diastolic) / max(1, total)
        aci = attention * curiosity * interaction

        # Pi-space: when ACI=0, which voice is silent?
        # The zero IS the information. Gray = honest null.
        silent = []
        if attention == 0: silent.append("attention")
        if curiosity == 0: silent.append("curiosity")
        if interaction == 0: silent.append("interaction")

        if aci == 0 and total > 0:
            # Fall to pi-space — the null gray
            # But we still have partial voices: whichever dimensions > 0
            # pi_voice = the non-zero dimensions averaged (partial signal in gray)
            nonzero = [v for v in [attention, curiosity, interaction] if v > 0]
            pi_voice = sum(nonzero) / max(1, len(nonzero)) if nonzero else 0
            color = "gray"
        elif aci > 0:
            # Full voice — all 3 dimensions active
            pi_voice = aci
            color = "voiced"
        else:
            pi_voice = 0
            color = "null"

        # Tree depth — how many levels of classification
        # is + nearby + was = 3 levels
        # transitions add depth
        tree_depth = 0
        if is_c > 0: tree_depth += 1
        if nearby_c > 0: tree_depth += 1
        if was_c > 0: tree_depth += 1
        tree_depth += min(3, len(trans))

        # Per-epitope tea cup — this epitope's own sigma
        epi_counts = [is_c, nearby_c, was_c]
        epi_mu = sum(epi_counts) / max(1, len(epi_counts))
        epi_var = sum((x - epi_mu)**2 for x in epi_counts) / max(1, len(epi_counts))
        epi_sigma = math.sqrt(epi_var) if epi_var > 0 else 0.001
        # Z-score of each tense state for this epitope
        epi_z = {}
        epi_bands = {}
        for tname, tcount in [("is", is_c), ("nearby", nearby_c), ("was", was_c)]:
            z = (tcount - epi_mu) / max(0.001, epi_sigma)
            epi_z[tname] = round(z, 2)
            if abs(z) <= 1: epi_bands[tname] = "normal"
            elif abs(z) <= 2: epi_bands[tname] = "notable"
            else: epi_bands[tname] = "action"
        # Error: standard error of the mean
        epi_se = epi_sigma / math.sqrt(max(1, len(epi_counts)))
        epi_verdict = "holds" if all(b != "action" for b in epi_bands.values()) else "overflow"

        tensor[epi] = {
            "counts": {"is": is_c, "nearby": nearby_c, "was": was_c},
            "rates": {"systolic": systolic, "diastolic": diastolic},
            "pressure": round(systolic / max(1, diastolic), 3) if diastolic > 0 else (999 if systolic > 0 else 0),
            "status": status,
            "vocal": {
                "attention": round(attention, 4),
                "curiosity": round(curiosity, 4),
                "interaction": round(interaction, 4),
                "aci": round(aci, 6),
                "pi_voice": round(pi_voice, 4),
                "color": color,
                "silent": silent,
            },
            "tree_depth": tree_depth,
            "tea_cup": {
                "mu": round(epi_mu, 2),
                "sigma": round(epi_sigma, 2),
                "se": round(epi_se, 2),
                "z": epi_z,
                "bands": epi_bands,
                "verdict": epi_verdict,
            },
        }

    # ═══ GLOBAL TENSOR METRICS ═══
    all_is = sum(t["counts"]["is"] for t in tensor.values())
    all_nearby = sum(t["counts"]["nearby"] for t in tensor.values())
    all_was = sum(t["counts"]["was"] for t in tensor.values())
    all_total = all_is + all_nearby + all_was

    # Entropy of the tense distribution (from global counts)
    g_is = tense_global.get("is", 0)
    g_was = tense_global.get("was", 0)
    g_will = tense_global.get("will_be", 0)
    g_total = g_is + g_was + g_will
    entropy = 0
    for count in [g_is, g_was, g_will]:
        if count > 0 and g_total > 0:
            p = count / g_total
            entropy -= p * math.log2(p)

    # ═══ THE TEA CUP — normal distribution with OUR σ ═══
    # The 81% is not stuck — it IS the distribution.
    # Use our own mean/std to set error bars.
    # Within 1σ = normal (sit). 2σ = notable (watch). 3σ = action (move).
    tense_counts = [g_is, g_was, g_will]
    mu = sum(tense_counts) / max(1, len(tense_counts))
    variance = sum((x - mu)**2 for x in tense_counts) / max(1, len(tense_counts))
    sigma = math.sqrt(variance) if variance > 0 else 1

    tea_cup = {}
    for name, count in [("is", g_is), ("was", g_was), ("will_be", g_will)]:
        z = (count - mu) / max(1, sigma)
        if abs(z) <= 1:
            band = "normal"     # sit — within the cup
        elif abs(z) <= 2:
            band = "notable"    # watch — near the rim
        else:
            band = "action"     # move — overflowing
        tea_cup[name] = {
            "count": count,
            "z": round(z, 3),
            "band": band,
            "pct": round(100 * count / max(1, g_total), 1),
        }

    # Fell-through count
    fell = [epi for epi, t in tensor.items() if t["status"] == "fell"]
    active = [epi for epi, t in tensor.items() if t["status"] == "present"]
    approaching = [epi for epi, t in tensor.items() if t["status"] == "approaching"]

    # Classification tree — multi-dimensional: status × vocal × depth
    # The bingo cube sieve: Attention × Curiosity × Interaction
    # Vocal sort: rank epitopes by their ACI product
    # Tree branches: status → epitope → {depth, vocal_rank, aci}
    
    # Vocal sort — rank all epitopes by ACI (bingo cube sieve)
    aci_ranked = sorted(tensor.items(), key=lambda x: x[1]["vocal"]["aci"], reverse=True)
    for rank, (epi, t) in enumerate(aci_ranked):
        tensor[epi]["vocal_rank"] = rank + 1
    
    # Attention sort — who gets looked at most
    att_ranked = sorted(tensor.items(), key=lambda x: x[1]["vocal"]["attention"], reverse=True)
    
    # Build the tree with vocal classification
    tree = {}
    for epi, t in tensor.items():
        status = t["status"]
        if status not in tree:
            tree[status] = {}
        tree[status][epi] = {
            "depth": t["tree_depth"],
            "vocal_rank": t["vocal_rank"],
            "aci": t["vocal"]["aci"],
            "attention": t["vocal"]["attention"],
            "curiosity": t["vocal"]["curiosity"],
            "interaction": t["vocal"]["interaction"],
            "pressure": t["pressure"],
        }
    
    # Also build a flat vocal ranking for bingo cube
    vocal_tree = []
    for epi, t in aci_ranked:
        vocal_tree.append({
            "epitope": epi,
            "rank": t["vocal_rank"],
            "aci": t["vocal"]["aci"],
            "status": t["status"],
            "depth": t["tree_depth"],
        })

    # ═══ OUTPUT ═══
    output = {
        "ts": now,
        "utc": now_iso,
        "tensor": tensor,
        "global": {
            "is": g_is,
            "was": g_was,
            "will_be": g_will,
            "total": g_total,
            "entropy_bits": round(entropy, 4),
            "max_entropy": round(math.log2(3), 4),
            "entropy_ratio": round(entropy / math.log2(3), 4) if entropy > 0 else 0,
            "jam_ratio": round(g_is / max(1, g_total), 4),
            "tea_cup": {
                "mu": round(mu, 1),
                "sigma": round(sigma, 1),
                "states": tea_cup,
                "verdict": "cup holds" if all(v["band"] != "action" for v in tea_cup.values()) else "overflow",
            },
        },
        "classification_tree": tree,
        "vocal_ranking": vocal_tree,
        "summary": {
            "epitopes": len(tensor),
            "present": len(active),
            "fell": len(fell),
            "approaching": len(approaching),
            "total_transitions": sum(sum(v.values()) for v in transitions.values()),
        },
        "bus_cardio": {
            "bpm": cardio.get("bpm", 0),
            "systolic": cardio.get("systolic", 0),
            "diastolic": cardio.get("diastolic", 0),
        },
        "pi_figures": {
            "mu": pi_fig(mu),
            "sigma": pi_fig(sigma),
            "is": pi_fig(g_is),
            "was": pi_fig(g_was),
            "will_be": pi_fig(g_will),
            "total": pi_fig(g_total),
            "42_note": "42 = 4.26\u03c0\u00b2, 42/\u03c0\u00b3 \u2248 1+1/\u03c0 within 2.8%",
        },
    }

    with open(os.path.join(LIVE, "tense-tensor.json"), "w") as f:
        json.dump(output, f, indent=2)

    save_state(state)

if __name__ == "__main__":
    main()
