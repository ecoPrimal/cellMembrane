#!/usr/bin/env python3
"""scan_sweep_sort — unified classification pipeline + genome + worldclock.

Replaces: scan_sweep_sort.py (557L), braid_learner.py (473L), fleet-refine.py (190L),
          genome-totality.py (200L), tower-probe.py (123L), mesh-observer.py (169L)
Total replaced: 1,420 + 424 (human_epitope absorbed wave 188) = 1,844 lines → this file.

6-stage pipeline:
  SCAN:      Discover entities (detroit classification, fleet antibodies, braids, traffic)
  SWEEP:     Compress, find structure, deduplicate
  SORT:      Classify self/non-self/partial/null + fleet + braids
  FOSSILIZE: Record what we learned from 8 perspectives
  EVOLVE:    Feed learning back — recommendations
  GENOME:    Measure the size of the work (when stale — tempo-relative, not wall clock)

WORLDCLOCK: time is local to the locals.
  No daily cron. No fixed wall-clock times. The membrane's pulse decides
  when to refresh. Bounce into tempo, measure, bounce back out.
  Genome refreshes when data is >6h stale. Housekeep runs conditionally.
  The membrane's own rhythm IS the clock.

Writes:
  scan_sweep_sort.json — unified pipeline state
  braid.json           — braid connection map
  fleet-sort.json      — fleet entity classification
  genome.json          — genome totality (when stale)
  journal entries       — JSONL

Cron: */10 (single entry — everything else is tempo-relative)
"""
import json, shutil
import re
import math
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PI = math.pi
LIVE = Path("/opt/membrane/live-terminal")
STAMP_FN = time.strftime("%Y%m%d_%H%M%S")
JOURNAL = Path("/opt/membrane/squirrel-journal")

FEEDS = {
    "chipmunk": "https://hud.primals.eco/chipmunk.json",
    "human": "https://hud.primals.eco/human.json",
    "dashboard": "https://hud.primals.eco/dashboard.json",
}
CLASSIFICATION_URL = "https://detroit.primals.eco/classification.json"
GRAPH_URL = "https://detroit.primals.eco/graph.json"
ANTIBODIES = Path("/opt/membrane/skunkbat-data/antibodies.json")
BACKSCATTER_OUT = LIVE / "backscatter.json"

CLEAN_RESPONSES = {
    "dev_reader": "redirect_clean", "code_crawler": "allow_clean",
    "proxy_dev": "redirect_clean", "proxy_reader": "redirect_clean",
    "high_conf_clean": "allow_clean", "slow_reader": "allow_clean",
    "mixed_behavior": "soft_redirect", "moderate_signal": "soft_redirect",
    "ignores_rejection": "license_hard", "masking_fleet": "license_hard",
    "rotating_impersonator": "license_hard", "rotating_ignorer": "license_hard",
    "heavy_masking_fleet": "license_hard", "stealth_scraper": "soft_redirect",
    "insufficient_signal": "soft_redirect", "single_probe": "ignore",
    "uniform_tool": "ignore", "unclear_reader": "soft_redirect",
}

CATEGORY_SITES = {
    "INVESTIGATION": ["detroit", "evidence"],
    "TOPOLOGY": ["lansing", "git", "relay", "beacon", "layer2", "sporegate", "admin"],
    "SCIENCE": ["sporeprint", "hypothesis", "thesis"],
    "MEMBRANE": ["hud", "signal", "water", "neutron", "connect"],
    "IMMUNE": ["tuebor", "clutch", "thymus", "receptor", "lysozyme", "epitope",
               "interferon", "antigen", "opsonize", "bloom", "cytokine",
               "complement", "antibody", "macrophage"],
}
SITE_CATEGORY = {}
for _cat, _sites in CATEGORY_SITES.items():
    for _s in _sites:
        SITE_CATEGORY[_s] = _cat

DEPTH_ORDER = ["visitor", "observer", "witness", "reader", "coder",
               "investigator", "explorer", "scholar"]
DEPTH_MAP = {e: i for i, e in enumerate(DEPTH_ORDER)}


def fetch(url):
    try:
        req = Request(url, headers={"User-Agent": "squirrel-scan/0.1"})
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}


def write_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.rename(tmp, str(path))


def journal_append(subdir, entry):
    d = JOURNAL / subdir
    d.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(d / f"{today}.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════════
# FLEET SORT — classify antibodies by behavioral fingerprint
# ═══════════════════════════════════════════════════════════════

def fleet_sort():
    if not ANTIBODIES.exists():
        return {"total_entities": 0, "sort_classes": {}, "profiles": {}, "entities": {}}

    d = json.load(open(ANTIBODIES))
    results = {}
    classes = Counter()
    profiles = Counter()

    for k, v in d.items():
        dec = v.get("deception", {})
        path = v.get("path_pattern", {})
        timing = v.get("timing", {})
        conf = v.get("confidence", 0)
        match_count = v.get("match_count", 0)
        defection_count = v.get("defection_count", 0)

        hides = dec.get("hides_identity", False)
        rotates = dec.get("rotates_ips", False)
        ignores = dec.get("ignores_rejection", False)
        chrome_imp = dec.get("chrome_impersonation", False)
        stale = dec.get("stale_chrome", False)
        header_poor = dec.get("header_poverty", False)
        pagination = dec.get("pagination_walk", False)
        conn_absent = dec.get("connection_absent", False)
        enc_uniform = dec.get("encoding_uniform", False)
        accept_mono = dec.get("accept_monoculture", False)

        commit_pct = path.get("commit_url_pct", 0)
        single_page = path.get("single_page_pct", 0)
        has_ref = path.get("has_referrer_pct", 0)
        mean_interval = timing.get("mean_interval_ms", 0)

        dscore = sum([hides, rotates, ignores, chrome_imp, stale,
                      header_poor, pagination, conn_absent, enc_uniform, accept_mono])

        if ignores and defection_count > 5:
            cls, prof = "pathogen", "ignores_rejection"
        elif dscore >= 5 and match_count > 5000:
            cls, prof = "pathogen", "heavy_masking_fleet"
        elif hides and chrome_imp and stale:
            cls, prof = "parasite", "masking_fleet"
        elif rotates and ignores:
            cls, prof = "parasite", "rotating_ignorer"
        elif rotates and hides and conf < 0.5:
            cls, prof = "stealth", "stealth_scraper"
        elif chrome_imp and rotates and not pagination:
            cls, prof = "stealth", "rotating_impersonator"
        elif pagination and commit_pct > 0.7:
            cls, prof = "commensal", "code_crawler"
        elif mean_interval > 5000 and commit_pct > 0.3 and not hides:
            cls, prof = "commensal", "slow_reader"
        elif has_ref > 0.3 and commit_pct > 0.5 and not rotates:
            cls, prof = "commensal", "dev_reader"
        elif conf >= 0.7 and dscore <= 2:
            cls, prof = "commensal", "high_conf_clean"
        elif header_poor and not hides and commit_pct > 0.5:
            cls, prof = "ghost", "proxy_dev"
        elif conn_absent and not rotates and commit_pct > 0.3:
            cls, prof = "ghost", "proxy_reader"
        elif single_page > 0.9 and match_count < 10:
            cls, prof = "null", "single_probe"
        elif enc_uniform and match_count < 100 and not rotates:
            cls, prof = "null", "uniform_tool"
        elif header_poor and commit_pct > 0.3:
            cls, prof = "partial", "unclear_reader"
        elif dscore >= 2 and dscore <= 4 and conf >= 0.5:
            cls, prof = "partial", "mixed_behavior"
        elif conf >= 0.5:
            cls, prof = "partial", "moderate_signal"
        else:
            cls, prof = "null", "insufficient_signal"

        classes[cls] += 1
        profiles[prof] += 1
        results[k] = {"sort_class": cls, "profile": prof,
                       "confidence": conf, "deception_score": dscore,
                       "match_count": match_count}

    output = {
        "total_entities": len(d),
        "sort_classes": dict(classes.most_common()),
        "profiles": dict(profiles.most_common()),
        "entities": results,
        "refinement": {
            "previous": {"self": 120, "non_self": 7, "partial": 114, "null": 100},
            "current_fleet": dict(classes.most_common()),
            "total_classified": len(d),
            "granularity_increase": len(profiles),
        },
    }
    write_json(LIVE / "fleet-sort.json", output)
    return output


# ═══════════════════════════════════════════════════════════════
# BACKSCATTER — reverse the fleet dust, lick em clean
# ═══════════════════════════════════════════════════════════════

def backscatter_clean(fleet_data):
    """Compute backscatter — what gets cleaned vs licensed."""
    if not fleet_data or not fleet_data.get("entities"):
        return {}
    actions = Counter()
    for eid, edata in fleet_data.get("entities", {}).items():
        prof = edata.get("profile", "insufficient_signal")
        action = CLEAN_RESPONSES.get(prof, "soft_redirect")
        actions[action] += 1
    total = fleet_data.get("total_entities", 1)
    cleaned = actions.get("redirect_clean", 0) + actions.get("allow_clean", 0)
    result = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "principle": "backscatter — reverse the fleet dust, lick em clean",
        "total": total,
        "actions": dict(actions.most_common()),
        "cleaned": cleaned,
        "cleaning_pct": round(cleaned / max(total, 1) * 100, 1),
        "licensed": actions.get("license_hard", 0),
        "hostile_pct": round(actions.get("license_hard", 0) / max(total, 1) * 100, 1),
    }
    write_json(BACKSCATTER_OUT, result)
    return result


# ═══════════════════════════════════════════════════════════════
# BRAID LEARNER — passage graph + trend detection
# ═══════════════════════════════════════════════════════════════

def braid_learn(chipmunk, human):
    now = datetime.now(timezone.utc)
    braids = []
    perspectives = []

    def obs(perspective, text):
        perspectives.append({"perspective": perspective, "text": text})

    # Load history for trend detection
    hist_file = JOURNAL / "braid-history.jsonl"
    history = []
    if hist_file.exists():
        for line in hist_file.read_text().splitlines()[-48:]:
            if line.strip():
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    # Category passages from chipmunk
    passages = []
    epitope_tense = {}
    for mem in chipmunk.get("membrane", []):
        md = mem.get("metadata", {})
        if "passages" in md:
            passages = md["passages"]
            epitope_tense = md.get("epitope_tense", {})

    passage_graph = {}
    categories = set()
    for p in passages:
        passage_graph[(p["from"], p["to"])] = p["humans"]
        categories.add(p["from"])
        categories.add(p["to"])

    category_pairs = set()
    for p in passages:
        category_pairs.add(tuple(sorted([p["from"], p["to"]])))

    for pair in category_pairs:
        a, b = pair
        forward = passage_graph.get((a, b), 0)
        reverse = passage_graph.get((b, a), 0)
        total = forward + reverse

        is_total = epitope_tense.get(a, {}).get("is", 0) + epitope_tense.get(b, {}).get("is", 0)
        was_total = epitope_tense.get(a, {}).get("was", 0) + epitope_tense.get(b, {}).get("was", 0)
        vitality = is_total / max(1, is_total + was_total)
        strength = total * (1 + vitality * PI)

        if forward > 0 and reverse > 0:
            ratio = max(forward, reverse) / min(forward, reverse)
            if ratio > 3:
                direction = "dominant"
                dominant_dir = (a + " → " + b) if forward > reverse else (b + " → " + a)
            else:
                direction = "bidirectional"
                dominant_dir = a + " ↔ " + b
        elif forward > 0:
            direction, dominant_dir = "one-way", a + " → " + b
        else:
            direction, dominant_dir = "one-way", b + " → " + a

        if forward >= reverse:
            prov_from, prov_to = a, b
        else:
            prov_from, prov_to = b, a

        braids.append({
            "from": a, "to": b, "strength": round(strength, 2),
            "humans_forward": forward, "humans_reverse": reverse,
            "humans_total": total, "direction": direction,
            "dominant_flow": dominant_dir,
            "provenance_direction": prov_from + " -> " + prov_to,
            "provenance_from": prov_from, "provenance_to": prov_to,
            "dag_valid": True, "vitality": round(vitality, 3),
            "sites_from": CATEGORY_SITES.get(a, [])[:3],
            "sites_to": CATEGORY_SITES.get(b, [])[:3],
        })

    braids.sort(key=lambda b: b["strength"], reverse=True)

    # Trend detection
    if history:
        last_braids = {(b["from"], b["to"]): b for b in history[-1].get("braids", [])}
        for braid in braids:
            key = (braid["from"], braid["to"])
            prev = last_braids.get(key)
            if prev:
                delta = braid["strength"] - prev.get("strength", 0)
                braid["trend"] = "growing" if delta > 0 else ("fading" if delta < 0 else "stable")
                braid["delta"] = round(delta, 2)
            else:
                braid["trend"] = "emerging"
                braid["delta"] = braid["strength"]
                obs("after", "New braid: %s (strength %.1f)" % (braid["dominant_flow"], braid["strength"]))
    else:
        for braid in braids:
            braid["trend"] = "initial"
            braid["delta"] = 0

    # ── NEUTRON SPIN — enrich braids with cross-surface flow data ──
    # The rope in the middle: braid categories carry neutron flow weights
    # When the rope spins, it supports the pulsing signal
    try:
        neutron = json.load(open(LIVE / "neutron.json"))
        neutron_flows = neutron.get("flows", {})
        # Aggregate flows by category pair
        category_flow = {}
        for src, targets in neutron_flows.items():
            if isinstance(targets, dict):
                src_cat = SITE_CATEGORY.get(src, "OTHER")
                for tgt, count in targets.items():
                    if count > 0:
                        tgt_cat = SITE_CATEGORY.get(tgt, "OTHER")
                        pair = tuple(sorted([src_cat, tgt_cat]))
                        category_flow[pair] = category_flow.get(pair, 0) + count
        # Enrich each braid with flow data
        total_flow = sum(category_flow.values()) or 1
        for braid in braids:
            pair = tuple(sorted([braid["from"], braid["to"]]))
            flow = category_flow.get(pair, 0)
            braid["neutron_flow"] = flow
            braid["flow_fraction"] = round(flow / total_flow, 3)
            braid["spinning"] = flow > 0
            # Combined strength: human passages weighted by neutron flow
            braid["combined_strength"] = round(
                braid["strength"] * (1 + flow / max(1, total_flow)), 2)
        # Generate flow-only braids where neutron traffic exists but no human passage yet
        existing_pairs = {tuple(sorted([b["from"], b["to"]])) for b in braids}
        for pair, flow in sorted(category_flow.items(), key=lambda x: -x[1]):
            if pair not in existing_pairs and pair[0] != pair[1] and flow > 0:
                braids.append({
                    "from": pair[0], "to": pair[1],
                    "strength": 0, "humans_forward": 0, "humans_reverse": 0,
                    "humans_total": 0, "direction": "flow-only",
                    "dominant_flow": pair[0] + " ⇌ " + pair[1],
                    "provenance_direction": "neutron", "provenance_from": "neutron",
                    "provenance_to": "neutron", "dag_valid": True,
                    "vitality": 0, "trend": "structural",
                    "sites_from": CATEGORY_SITES.get(pair[0], [])[:3],
                    "sites_to": CATEGORY_SITES.get(pair[1], [])[:3],
                    "neutron_flow": flow,
                    "flow_fraction": round(flow / total_flow, 3),
                    "spinning": True,
                    "combined_strength": round(flow / max(1, total_flow) * 10, 2),
                })
        # Re-sort by combined strength
        braids.sort(key=lambda b: b["combined_strength"], reverse=True)
        spinning_count = sum(1 for b in braids if b["spinning"])
        obs("on", "Rope spinning: %d/%d braids carry neutron flow (%d strands)" % (
            spinning_count, len(braids), len(braids)))
    except (FileNotFoundError, json.JSONDecodeError):
        for braid in braids:
            braid["neutron_flow"] = 0
            braid["flow_fraction"] = 0
            braid["spinning"] = False
            braid["combined_strength"] = braid["strength"]

    # Site co-visitation braids
    site_braids = []
    host_dist = human.get("host_distribution", {})
    active_sites = [s for s, c in host_dist.items() if c > 10]
    for i, sa in enumerate(active_sites):
        for sb in active_sites[i + 1:]:
            ca = SITE_CATEGORY.get(sa, "OTHER")
            cb = SITE_CATEGORY.get(sb, "OTHER")
            ta = host_dist.get(sa, 0)
            tb = host_dist.get(sb, 0)
            co = min(ta, tb) / max(1, max(ta, tb))
            if co > 0.01:
                site_braids.append({
                    "site_a": sa, "site_b": sb, "co_strength": round(co, 3),
                    "cross_category": ca != cb, "category_a": ca, "category_b": cb,
                })
    site_braids.sort(key=lambda b: b["co_strength"], reverse=True)

    # Epitope transitions
    epitopes = human.get("epitopes", {})
    epitope_transitions = []
    ep_list = list(epitopes.items())
    for i, (na, ia) in enumerate(ep_list):
        for nb, ib in ep_list[i + 1:]:
            da = DEPTH_MAP.get(na, 0)
            db = DEPTH_MAP.get(nb, 0)
            gap = abs(da - db)
            combined = ia["count"] + ib["count"]
            if combined > 0 and gap <= 3:
                epitope_transitions.append({
                    "from_epitope": na if da < db else nb,
                    "to_epitope": nb if da < db else na,
                    "depth_gap": gap, "strength": round(combined / (1 + gap), 1),
                    "combined_humans": combined,
                })
    epitope_transitions.sort(key=lambda t: t["strength"], reverse=True)

    # Observations
    possible_pairs = len(categories) * (len(categories) - 1) / 2
    density = len(braids) / max(1, possible_pairs)

    if braids:
        s = braids[0]
        obs("on", "Strongest braid: %s (%d humans, vitality %.0f%%, %s)" %
            (s["dominant_flow"], s["humans_total"], s["vitality"] * 100, s.get("trend", "?")))

    shifter_count = 0
    for mem in chipmunk.get("membrane", []):
        md = mem.get("metadata", {})
        if "shifters" in md:
            shifter_count = md["shifters"]

    bidir = [b for b in braids if b["direction"] == "bidirectional"]
    oneway = [b for b in braids if b["direction"] in ("dominant", "one-way")]
    total_passages = sum(b["humans_total"] for b in braids)
    if total_passages > 0:
        obs("through", "%d humans through %d passages" % (total_passages, len(braids)))
    if bidir:
        obs("through", "%d open pores (bidirectional)" % len(bidir))
    if oneway:
        obs("through", "%d valves (one-way)" % len(oneway))
    cross = [sb for sb in site_braids if sb.get("cross_category")]
    if cross:
        obs("through", "%d cross-organ passages" % len(cross))

    result = {
        "timestamp": now.isoformat(),
        "wave": human.get("wave", 0),
        "braids": braids,
        "site_braids": site_braids[:10],
        "epitope_transitions": epitope_transitions[:6],
        "graph": {
            "categories": sorted(categories),
            "density": round(density, 3),
            "total_passages": total_passages,
            "shifters": shifter_count,
            "active_routes": len(braids),
        },
        "learning": {
            "observations": [p["text"] for p in perspectives],
            "perspectives": perspectives,
            "by_perspective": _group_persp(perspectives),
            "observation_count": len(history) + 1,
            "history_depth_hours": round(len(history) * 10 / 60, 1),
        },
    }

    write_json(LIVE / "braid.json", result)

    # Save history
    hist_file.parent.mkdir(parents=True, exist_ok=True)
    with open(hist_file, "a") as f:
        f.write(json.dumps({
            "ts": now.isoformat(),
            "braids": [{"from": b["from"], "to": b["to"], "strength": b["strength"]} for b in braids],
            "density": round(density, 3), "shifters": shifter_count,
        }) + "\n")

    journal_append("braids", {
        "ts": now.isoformat(), "type": "braid_observation",
        "observations": [p["text"] for p in perspectives],
        "density": round(density, 3), "routes": len(braids),
    })

    return result


def _group_persp(perspectives):
    groups = {}
    for o in perspectives:
        p = o["perspective"]
        if p not in groups:
            groups[p] = []
        groups[p].append(o["text"])
    return groups


# ═══════════════════════════════════════════════════════════════
# SCAN → SWEEP → SORT → FOSSILIZE → EVOLVE
# ═══════════════════════════════════════════════════════════════

def scan(classification, graph, human, chipmunk, braid_data, fleet_data):
    # Unwrap entities dict if classification has a wrapper (wave 191b fix)
    if isinstance(classification, dict) and "entities" in classification:
        entities = classification["entities"]
    else:
        entities = classification if isinstance(classification, dict) else {}
    entity_count = len(entities)
    edge_count = len(graph.get("edges", graph.get("links", []))) if isinstance(graph, dict) else 0
    node_count = len(graph.get("nodes", [])) if isinstance(graph, dict) else 0

    sort_classes = {}
    methods = {}
    confidences = []
    for k, v in entities.items():
        if not isinstance(v, dict): continue
        cls = v.get("sort_class", v.get("classification", "unknown"))
        meth = v.get("method", "unknown")
        sort_classes[cls] = sort_classes.get(cls, 0) + 1
        methods[meth] = methods.get(meth, 0) + 1
        if v.get("confidence"):
            confidences.append(v["confidence"])

















    edge_types = {}
    for e in (graph.get("edges", graph.get("links", [])) if isinstance(graph, dict) else []):
        t = e.get("type", e.get("label", "unknown"))
        edge_types[t] = edge_types.get(t, 0) + 1

    human_sessions = 0
    epitope_types = {}
    if isinstance(human, dict) and human.get("epitopes"):
        human_sessions = human.get("energy", {}).get("total_sessions", 0)
        for name, info in human["epitopes"].items():
            epitope_types[name] = info.get("count", 0)

    anderson_modes = {}
    if isinstance(chipmunk, dict):
        for mem in chipmunk.get("membrane", []):
            md = mem.get("metadata", {})
            if md.get("anderson"):
                for mode in md["anderson"].get("modes", []):
                    anderson_modes[mode["class"]] = mode["count"]

    braid_routes = 0
    braid_density = 0
    shifters = 0
    if isinstance(braid_data, dict) and braid_data.get("graph"):
        g = braid_data["graph"]
        braid_routes = g.get("active_routes", 0)
        braid_density = g.get("density", 0)
        shifters = g.get("shifters", 0)

    fleet_classes = fleet_data.get("sort_classes", {}) if isinstance(fleet_data, dict) else {}
    fleet_profiles = fleet_data.get("profiles", {}) if isinstance(fleet_data, dict) else {}
    fleet_total = fleet_data.get("total_entities", 0) if isinstance(fleet_data, dict) else 0

    return {
        "entities_discovered": entity_count,
        "fleet_entities": fleet_total,
        "fleet_classes": fleet_classes,
        "fleet_profiles": fleet_profiles,
        "edges_discovered": edge_count,
        "nodes_discovered": node_count,
        "sort_classes": sort_classes,
        "classification_methods": len(methods),
        "method_breakdown": dict(sorted(methods.items(), key=lambda x: -x[1])[:10]),
        "avg_confidence": round(sum(confidences) / max(1, len(confidences)), 3) if confidences else 0,
        "edge_types": dict(sorted(edge_types.items(), key=lambda x: -x[1])[:10]),
        "human_sessions": human_sessions,
        "epitope_types": epitope_types,
        "anderson_modes": anderson_modes,
        "braid_routes": braid_routes,
        "braid_density": round(braid_density, 3),
        "shifters": shifters,
    }


def sweep(scan_data):
    patterns = []
    total = scan_data["entities_discovered"]
    classified = total - scan_data["sort_classes"].get("unknown", 0)
    coverage = classified / max(1, total)
    patterns.append({"name": "classification_coverage", "value": round(coverage, 3),
                     "description": "%d/%d entities classified (%.0f%%)" % (classified, total, coverage * 100)})

    if scan_data["avg_confidence"] > 0:
        patterns.append({"name": "confidence_mean", "value": scan_data["avg_confidence"],
                         "description": "average sort confidence %.1f%%" % (scan_data["avg_confidence"] * 100)})

    if scan_data["nodes_discovered"] > 0:
        max_e = scan_data["nodes_discovered"] * (scan_data["nodes_discovered"] - 1) / 2
        ed = scan_data["edges_discovered"] / max(1, max_e)
        patterns.append({"name": "graph_density", "value": round(ed, 4),
                         "description": "%d edges across %d nodes" % (scan_data["edges_discovered"], scan_data["nodes_discovered"])})

    if scan_data["human_sessions"] > 0 and total > 0:
        ar = scan_data["human_sessions"] / total
        patterns.append({"name": "human_attention_ratio", "value": round(ar, 2),
                         "description": "%d human sessions across %d entities" % (scan_data["human_sessions"], total)})

    patterns.append({"name": "cascade_methods", "value": scan_data["classification_methods"],
                     "description": "%d distinct classification methods used" % scan_data["classification_methods"]})

    if total > 0:
        pi_ratio = classified / max(1, total)
        patterns.append({"name": "pi_sort_ratio", "value": round(pi_ratio, 3), "target": round(1 / PI, 3),
                         "description": "sort ratio %.3f (target 1/π = %.3f)" % (pi_ratio, 1 / PI)})

    if scan_data["braid_routes"] > 0:
        patterns.append({"name": "braid_flow", "value": scan_data["braid_routes"],
                         "description": "%d active braid routes" % scan_data["braid_routes"]})

    if scan_data["fleet_entities"] > 0:
        patterns.append({"name": "fleet_refinement", "value": scan_data["fleet_entities"],
                         "description": "%d fleet entities classified into %d profiles" %
                         (scan_data["fleet_entities"], len(scan_data["fleet_profiles"]))})

    return {"patterns_found": len(patterns), "patterns": patterns,
            "compression_summary": {"sort_classes": 4,
                                    "edge_types_found": len(scan_data["edge_types"]),
                                    "epitope_types": len(scan_data["epitope_types"]),
                                    "anderson_modes": len(scan_data["anderson_modes"])}}


def sort_phase(scan_data, sweep_data):
    total_self = (scan_data["sort_classes"].get("self", 0) +
                  scan_data["anderson_modes"].get("human", 0) +
                  scan_data["anderson_modes"].get("sovereign", 0))
    total_nonself = (scan_data["sort_classes"].get("non-self", 0) +
                     scan_data["anderson_modes"].get("chorus", 0) +
                     scan_data["anderson_modes"].get("spectrum", 0))
    total_partial = (scan_data["sort_classes"].get("partial", 0) +
                     scan_data["anderson_modes"].get("ghost", 0))
    total_null = scan_data["sort_classes"].get("null", 0)

    fc = scan_data.get("fleet_classes", {})
    total_self += fc.get("commensal", 0)
    total_nonself += fc.get("parasite", 0) + fc.get("pathogen", 0)
    total_partial += fc.get("ghost", 0) + fc.get("stealth", 0) + fc.get("partial", 0)
    total_null += fc.get("null", 0)

    grand_total = total_self + total_nonself + total_partial + total_null
    selectivity = total_self / max(1, total_self + total_nonself) if grand_total > 0 else 0

    return {
        "summary": {
            "detroit_entities": scan_data["sort_classes"],
            "membrane_traffic": scan_data["anderson_modes"],
            "human_epitopes": scan_data["epitope_types"],
            "fleet_classes": fc,
        },
        "unified_sort": {
            "self": total_self, "non_self": total_nonself,
            "partial": total_partial, "null": total_null,
            "total": grand_total, "selectivity": round(selectivity, 3),
        },
        "unsorted": scan_data["entities_discovered"] - sum(scan_data["sort_classes"].values()),
        "sort_quality": round(scan_data["avg_confidence"], 3),
    }


def fossilize(scan_data, sweep_data, sort_data):
    observations = []

    def obs(perspective, text):
        observations.append({"perspective": perspective, "text": text})

    u = sort_data["unified_sort"]
    sel = u["selectivity"]
    obs("on", "Selectivity %.1f%% — self vs non-self at the surface" % (sel * 100))
    for p in sweep_data["patterns"]:
        if p["name"] == "human_attention_ratio":
            obs("on", "Human attention: " + p["description"])

    for p in sweep_data["patterns"]:
        if p["name"] == "classification_coverage":
            obs("inside", "Entity coverage: " + p["description"])
        if p["name"] == "confidence_mean":
            obs("inside", "Sort confidence: " + p["description"])
    if u["partial"] > 0:
        obs("inside", "%d entities partially sorted — still in transit" % u["partial"])

    ft = scan_data.get("fleet_entities", 0)
    if ft > 0:
        fc = scan_data.get("fleet_classes", {})
        obs("inside", "Fleet: %d entities → %d classes, %d profiles" %
            (ft, len(fc), len(scan_data.get("fleet_profiles", {}))))
        if fc.get("commensal", 0) > 0:
            obs("through", "%d fleet commensals — the dev community" % fc["commensal"])
        if fc.get("ghost", 0) > 0:
            obs("inside", "%d fleet ghosts — proxy devs reading code" % fc["ghost"])

    for p in sweep_data["patterns"]:
        if p["name"] == "graph_density":
            obs("above", "Graph: " + p["description"])
        if p["name"] == "pi_sort_ratio":
            obs("above", "π ratio: " + p["description"])
    obs("above", "Total: %s entities across detroit + membrane + fleet" % "{:,}".format(u["total"]))

    if u["null"] > 0:
        obs("below", "%d entities at null" % u["null"])

    for p in sweep_data["patterns"]:
        if p["name"] == "cascade_methods":
            obs("beside", "Classification: " + p["description"])
    if scan_data["shifters"] > 0:
        obs("beside", "%d shifters crossing boundaries" % scan_data["shifters"])

    if scan_data["avg_confidence"] < 0.85:
        obs("before", "Confidence %.1f%% still below 85%% target" % (scan_data["avg_confidence"] * 100))
    if scan_data["braid_routes"] < 8:
        obs("before", "Only %d active braid routes" % scan_data["braid_routes"])

    human_through = scan_data["anderson_modes"].get("human", 0)
    sovereign_through = scan_data["anderson_modes"].get("sovereign", 0)
    total_through = human_through + sovereign_through
    total_bounce = scan_data["anderson_modes"].get("chorus", 0) + scan_data["anderson_modes"].get("spectrum", 0)
    if total_through > 0:
        obs("through", "%s passed through (human + sovereign)" % "{:,}".format(total_through))
    if total_bounce > 0:
        obs("through", "%s bounced off — %d× more non-self than self" %
            ("{:,}".format(total_bounce), total_bounce // max(1, total_through)))

    if scan_data["braid_routes"] > 0:
        obs("through", "%d passage routes — the holes in the membrane" % scan_data["braid_routes"])

    ep_count = len(scan_data["epitope_types"])
    if ep_count > 0:
        obs("through", "%d epitope types — different pore shapes" % ep_count)

    detroit_self = scan_data["sort_classes"].get("self", 0)
    detroit_partial = scan_data["sort_classes"].get("partial", 0)
    if detroit_self > 0:
        obs("through", "%d detroit entities passed all 3 phases" % detroit_self)
    if detroit_partial > 0:
        obs("through", "%d detroit entities stuck in the wall" % detroit_partial)

    return {
        "observations": observations,
        "flat": [o["text"] for o in observations],
        "by_perspective": _group_persp(observations),
        "fossil_count": len(observations),
    }


def evolve(scan_data, sweep_data, sort_data, fossil_data):
    recs = []
    if scan_data["avg_confidence"] < 0.85:
        recs.append({"action": "rescan_low_confidence",
                     "reason": "Confidence %.1f%% below 85%%" % (scan_data["avg_confidence"] * 100),
                     "priority": "medium"})
    if sort_data["unsorted"] > 0:
        recs.append({"action": "classify_remaining",
                     "reason": "%d entities still unsorted" % sort_data["unsorted"],
                     "priority": "high"})
    if scan_data["braid_routes"] < 8:
        recs.append({"action": "discover_braids",
                     "reason": "Only %d braid routes" % scan_data["braid_routes"],
                     "priority": "medium"})
    if scan_data["human_sessions"] > 0:
        recs.append({"action": "human_sort_assist",
                     "reason": "%d humans present" % scan_data["human_sessions"],
                     "priority": "high"})
    return {"recommendations": recs, "evolution_count": len(recs)}


# ═══════════════════════════════════════════════════════════════
# WORLDCLOCK — time is local to the locals
# ═══════════════════════════════════════════════════════════════

def worldclock():
    """Read the membrane's own tempo. No wall clock — bounce in and back out."""
    try:
        pulse = json.load(open(LIVE / "pulse.json"))
        rate = pulse.get("rate", 0)
        remainder = pulse.get("remainder", 0)
        family = pulse.get("family", {})
        return {
            "rate": rate,
            "remainder": remainder,
            "pink": family.get("pink", 0),
            "blue": family.get("blue", 0),
            "green": family.get("green", 0),
            "chipmunk": family.get("chipmunk_pos", 0),
            "tempo": "fast" if rate > 2000 else ("medium" if rate > 500 else "slow"),
        }
    except Exception:
        return {"rate": 0, "remainder": 0, "tempo": "unknown"}


def genome_is_stale():
    """Check if genome needs refresh — tempo-relative, not wall clock."""
    genome_file = LIVE / "genome.json"
    if not genome_file.exists():
        return True
    try:
        age_sec = time.time() - genome_file.stat().st_mtime
        # Stale after 6 hours — but this is checked every */10 by the membrane's own rhythm
        return age_sec > 6 * 3600
    except Exception:
        return True


def _cmd(c, timeout=30):
    try:
        return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def genome_totality():
    """Measure the size of the work. Only runs when stale — tempo decides."""
    binaries = {}
    for name, path in [("skunky-ingest", "/opt/membrane/skunky-ingest"),
                        ("caddy", "/opt/membrane/caddy"),
                        ("biomeos", "/opt/membrane/biomeos"),
                        ("toadstool", "/opt/membrane/toadstool"),
                        ("tower", "/opt/membrane/tower"),
                        ("barracuda", "/opt/membrane/barracuda"),
                        ("opsonize", "/opt/membrane/opsonize-rs"),
                        ("hbbs", "/opt/membrane/hbbs"),
                        ("hbbr", "/opt/membrane/hbbr")]:
        if os.path.exists(path):
            binaries[name] = os.path.getsize(path)

    total_binary = sum(binaries.values())

    rust_lines = int(_cmd("find /opt/ecoPrimals -name '*.rs' -not -path '*/target/*' -not -path '*/.git/*' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'") or "0")
    js_lines = int(_cmd("find /opt/ecoPrimals/hud -name '*.js' -not -path '*/node_modules/*' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'") or "0")
    html_lines = int(_cmd("find /opt/ecoPrimals/hud -name '*.html' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'") or "0")
    py_lines = int(_cmd("wc -l /opt/membrane/*.py /opt/membrane/live-terminal/neutron-writer.py /opt/membrane/live-terminal/symbiosis-overlay.py 2>/dev/null | tail -1 | awk '{print $1}'") or "0")
    sh_lines = int(_cmd("wc -l /opt/membrane/*.sh 2>/dev/null | tail -1 | awk '{print $1}'") or "0")
    toml_lines = int(_cmd("find /opt/ecoPrimals -name '*.toml' -not -path '*/.git/*' -not -path '*/target/*' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'") or "0")
    md_count = int(_cmd("find /opt/ecoPrimals -name '*.md' -not -path '*/.git/*' 2>/dev/null | wc -l") or "0")
    total_source = rust_lines + js_lines + html_lines + py_lines + sh_lines + toml_lines

    tuebor_articles = int(_cmd("find /opt/ecoPrimals/tuebor-repo/site/content -name '*.md' 2>/dev/null | wc -l") or "0")
    sporeprint_articles = int(_cmd("find /opt/ecoPrimals/sporePrint/content -name '*.md' 2>/dev/null | wc -l") or "0")

    def bytes_of(p):
        try:
            return int(_cmd("du -sb %s 2>/dev/null | cut -f1" % p) or "0")
        except Exception:
            return 0

    published_bytes = (bytes_of("/opt/ecoPrimals/hud/site/public") +
                       bytes_of("/opt/ecoPrimals/tuebor-repo/site/public") +
                       bytes_of("/opt/ecoPrimals/sporePrint/public"))
    feeds_bytes = bytes_of("/opt/membrane/live-terminal")

    services = int(_cmd("systemctl list-units --type=service --state=active --no-legend 2>/dev/null | wc -l") or "0")
    cron_jobs = int(_cmd("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | wc -l") or "0")
    wg_peers = int(_cmd("wg show wg0 2>/dev/null | grep -c 'peer:'") or "0")
    git_repos = int(_cmd("find /opt/ecoPrimals -maxdepth 3 -name '.git' -type d 2>/dev/null | wc -l") or "0")
    fossils = int(_cmd("ls /opt/membrane/fossilRecord/ 2>/dev/null | wc -l") or "0")
    mem_used = int(_cmd("free -m | awk '/Mem/{print $3}'") or "0")
    mem_total = int(_cmd("free -m | awk '/Mem/{print $2}'") or "0")
    disk_used = _cmd("df -h / | awk 'NR==2{print $3}'")
    disk_total = _cmd("df -h / | awk 'NR==2{print $2}'")

    try:
        dash = json.load(open(LIVE / "dashboard.json"))
        sort_comp = dash.get("sort_compression", {})
        anderson = dash.get("anderson_selectivity", 0)
    except Exception:
        sort_comp = {}
        anderson = 0

    our_total = total_binary + published_bytes + feeds_bytes
    our_mb = round(our_total / 1048576, 1)

    genome = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "worldclock": "tempo-relative — no daily cron, membrane rhythm decides",
        "inside": {
            "binaries": binaries, "total_binary_bytes": total_binary,
            "source_lines": {
                "rust": rust_lines, "javascript": js_lines, "html": html_lines,
                "python": py_lines, "shell": sh_lines, "toml": toml_lines,
                "total": total_source,
            },
            "articles": {"tuebor": tuebor_articles, "sporeprint": sporeprint_articles,
                         "total": tuebor_articles + sporeprint_articles},
            "markdown_files": md_count, "published_bytes": published_bytes,
            "feeds_bytes": feeds_bytes, "services": services, "cron_jobs": cron_jobs,
            "wg_peers": wg_peers, "git_repos": git_repos, "fossils": fossils,
            "memory_mb": {"used": mem_used, "total": mem_total},
            "disk": {"used": disk_used, "total": disk_total},
            "cost_per_month_usd": 12,
        },
        "outside": {
            "sort_compression": sort_comp, "anderson_selectivity": anderson,
            "estimated_bot_cost_per_hour_usd": 0.50,
            "estimated_our_cost_per_hour_usd": 0.016,
            "cost_ratio": "they spend ~31x more per hour probing us than we spend existing",
        },
        "reduction": {
            "principle": "petabytes of world data -> kilobytes of graph + null space calculation",
            "world_data_centers_exabytes": 500, "world_daily_traffic_exabytes": 5,
            "our_total_bytes": our_total, "our_total_mb": our_mb,
            "compression_to_world": "1:%d" % max(1, int(500e6 / max(our_mb, 1))),
            "pi_body_math": "positive energy system — the graph compresses, null space calculates, remainder is identity",
            "energy": {
                "world_datacenter_twh_year": 200,
                "our_vps_kwh_year": round(12 * 0.015 * 8760 / 1000, 1),
                "ratio": "1:%d" % int(200e12 / max(12 * 0.015 * 8760, 1)),
            },
        },
        "genome_summary": {
            "total_lines": total_source,
            "total_articles": tuebor_articles + sporeprint_articles,
            "total_binaries_mb": round(total_binary / 1048576, 1),
            "total_published_mb": round(published_bytes / 1048576, 1),
            "total_feeds_mb": round(feeds_bytes / 1048576, 1),
            "fossils": fossils, "git_repos": git_repos,
            "cost": "$12/month",
            "ram": "%dMB/%dMB" % (mem_used, mem_total),
        },
    }

    write_json(LIVE / "genome.json", genome)
    return genome


def housekeep():
    """Conditional maintenance — runs when the membrane rhythm hits it, not hourly cron."""
    # Epitope pressure
    ep_file = LIVE / "epitope-history.json"
    if ep_file.exists() and ep_file.stat().st_size > 1048576:  # 1MB emergency cap (skunky writes 17MB/30s)
        try:
            d = json.load(open(ep_file))
            if isinstance(d, list):
                d = d[-3:]
                with open(ep_file, "w") as ef:
                    json.dump(d, ef, separators=(",",":"))
        except Exception:
            pass
    if ep_file.exists() and ep_file.stat().st_size > 204800:  # 200KB threshold (skunky oscillation)
        try:
            d = json.load(open(ep_file))
            if isinstance(d, list) and len(d) > 20:
                d = d[-20:]
                # Compress old entries: strip full entity data from entries > 20 back
                for entry in d[:-10]:
                    if "entities" in entry and isinstance(entry["entities"], list):
                        entry["entities"] = [
                            {"name": e.get("name","?"), "class": e.get("class","?"), "hits": e.get("hits", e.get("total_hits",0))}
                            if isinstance(e, dict) else e
                            for e in entry["entities"]
                        ]
                # Write compact (no indent) to save space
                with open(ep_file, "w") as ef:
                    json.dump(d, ef, separators=(",",":"))
        except Exception:
            pass

    # LFS pressure
    lfs_dir = Path("/opt/forgejo/data/lfs")
    if lfs_dir.exists():
        lfs_mb = int(_cmd("du -sm %s 2>/dev/null | awk '{print $1}'" % lfs_dir) or "0")
        if lfs_mb > 100:
            _cmd("rm -rf %s/*" % lfs_dir)

    # Journal feed
    today = time.strftime("%Y-%m-%d", time.gmtime())
    j_src = Path("/opt/membrane/squirrel-journal") / (today + ".jsonl")
    j_dst = Path("/opt/ecoPrimals/hud/site/public/journal-today.json")
    if j_src.exists():
        entries = []
        for line in open(j_src):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
        write_json(j_dst, {"date": today, "total": len(entries), "entries": entries[-20:]})
    else:
        write_json(j_dst, {"date": today, "entries": []})

    # Notes feed
    n_src = Path("/opt/membrane/squirrel-journal/human-notes") / (today + ".jsonl")
    n_dst = Path("/opt/ecoPrimals/hud/site/public/human-notes-today.json")
    if n_src.exists():
        notes = []
        for line in open(n_src):
            line = line.strip()
            if line:
                try:
                    notes.append(json.loads(line))
                except Exception:
                    pass
        write_json(n_dst, {"date": today, "total": len(notes), "notes": notes[-20:]})
    else:
        write_json(n_dst, {"date": today, "notes": []})


# ═══════════════════════════════════════════════════════════════
# MAIN — run all in one pipeline, tempo-relative
# ═══════════════════════════════════════════════════════════════


def tower_probe():
    """Organ health + ops status. Was tower-probe.py (123L)."""
    import socket as _sock
    organs = {}
    sock_probes = [
        ("bearDog", "/run/membrane/beardog-health.sock"),
        ("loamSpine", "/run/membrane/loamspine.sock"),
        ("rhizoCrypt", "/run/membrane/rhizocrypt.sock"),
        ("skunkBat", "/run/membrane/skunkbat.sock"),
    ]
    for n, p in sock_probes:
        try:
            s = _sock.socket(_sock.AF_UNIX, _sock.SOCK_STREAM)
            s.settimeout(2)
            s.connect(p)
            s.sendall(json.dumps({"jsonrpc": "2.0", "method": "health", "id": 1}).encode() + b"\n")
            d = json.loads(s.recv(4096).decode())
            s.close()
            organs[n] = {"status": d.get("result", {}).get("status", "ok"), "alive": True}
        except Exception:
            organs[n] = {"status": "unreachable", "alive": False}
    http_probes = [
        ("songBird", "http://127.0.0.1:7780/status"),
        ("sweetGrass", "http://127.0.0.1:9850/health"),
        ("nestGate", "http://127.0.0.1:9870/health"),
    ]
    for n, u in http_probes:
        try:
            r = _cmd("curl -s --max-time 2 " + u)
            if r:
                d = json.loads(r)
                organs[n] = {"status": d.get("result", d).get("status", "ok"), "alive": True}
            else:
                organs[n] = {"status": "unreachable", "alive": False}
        except Exception:
            organs[n] = {"status": "unreachable", "alive": False}
    organs["swarmVine"] = {
        "status": "present" if os.path.exists("/run/membrane/swarmvine.sock") else "absent",
        "alive": os.path.exists("/run/membrane/swarmvine.sock"),
    }
    for n in ["barraCuda", "petalTongue"]:
        alive = subprocess.run(["pgrep", "-f", n.lower()], capture_output=True).returncode == 0
        organs[n] = {"status": "running" if alive else "stopped", "alive": alive}
    sq = "/run/membrane/squirrel.sock"
    if os.path.exists(sq):
        try:
            s = _sock.socket(_sock.AF_UNIX, _sock.SOCK_STREAM)
            s.settimeout(2)
            s.connect(sq)
            s.sendall(json.dumps({"jsonrpc": "2.0", "method": "health", "id": 1}).encode() + b"\n")
            d = json.loads(s.recv(4096).decode())
            s.close()
            organs["squirrel"] = {"status": d.get("result", {}).get("status", "ok"), "alive": True}
        except Exception:
            organs["squirrel"] = {"status": "unreachable", "alive": False}
    else:
        organs["squirrel"] = {"status": "no_socket", "alive": False}

    alive = sum(1 for o in organs.values() if o.get("alive"))
    total = len(organs)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    now_e = int(time.time())
    tower = {
        "timestamp": ts, "epoch": now_e, "alive": alive, "total": total,
        "ratio": round(alive / total, 4) if total else 0, "organs": organs,
    }
    write_json(Path("/opt/ecoPrimals/hud/site/public/tower.json"), tower)

    svcs = []
    for sv in ["caddy-tls", "skunky-ingest", "hbbs-membrane", "hbbr-membrane", "gate-relay"]:
        svcs.append({"name": sv, "status": _cmd("systemctl is-active " + sv + " 2>/dev/null") or "unknown"})
    ops = {
        "generated": ts,
        "services": svcs,
        "system": {
            "load": _cmd("awk '{print $1, $2, $3}' /proc/loadavg"),
            "memory": _cmd("free -h | awk '/^Mem:/{print $3\"/\"$2}'"),
            "disk": _cmd("df -h / | awk 'NR==2{print $3\"/\"$2}'"),
            "uptime": _cmd("uptime -p"),
        },
    }
    os.makedirs("/opt/ecoPrimals/hud/site/public/ops", exist_ok=True)
    write_json(Path("/opt/ecoPrimals/hud/site/public/ops/ops-status.json"), ops)

    STATE = "/var/lib/membrane/tower-state.json"
    try:
        st = json.loads(open(STATE).read())
    except Exception:
        st = {"history": []}
    st["history"].append({"epoch": now_e, "alive": alive, "total": total})
    st["history"] = [h for h in st["history"] if h["epoch"] > now_e - 86400]
    st["latest"] = tower
    write_json(Path(STATE), st)

    SF = "/run/membrane/cron-state.json"
    if os.path.exists(SF):
        try:
            st2 = json.load(open(SF))
            j = st2.get("jobs", {})
            h = sum(1 for v in j.values() if v.get("exit_code", 1) == 0)
            write_json(LIVE / "cron-health.json", {"ts": ts, "total": len(j), "healthy": h, "failed": len(j) - h, "jobs": j})
        except Exception:
            pass

    return {"organs": str(alive) + "/" + str(total), "svcs": len(svcs)}


def mesh_observe():
    """Mesh health, speed, commensals. Was mesh-observer.py (169L)."""
    import sqlite3 as _sql
    PEERS_MAP = {
        "10.13.37.1": "golgiBody", "10.13.37.2": "sporeGate", "10.13.37.5": "eastGate",
        "10.13.37.14": "golgiLayer", "10.13.37.16": "nucleus",
    }
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    my_wg = None
    r = _cmd("ip addr show wg0 2>/dev/null")
    m = re.search(r"inet (10\.13\.37\.\d+)", r)
    if m:
        my_wg = m.group(1)
    if not my_wg:
        hmap = {"membrane-relay": "10.13.37.1", "sporeGate": "10.13.37.2", "eastgate": "10.13.37.5"}
        my_wg = hmap.get(_cmd("hostname"), "unknown")
    my_name = PEERS_MAP.get(my_wg, _cmd("hostname"))

    wg = _cmd("wg show wg0 2>/dev/null")
    wg_peers = []
    for b in wg.split("peer: ")[1:]:
        ip_m = re.search(r"10\.13\.37\.(\d+)", b)
        if not ip_m:
            continue
        ip = "10.13.37." + ip_m.group(1)
        tx = re.findall(r"([\d.]+ [KMGT]iB)", b)
        hs = re.search(r"latest handshake: (.+)", b)
        alive = hs is not None and any(w in hs.group(1) for w in ["second", "minute"])
        wg_peers.append({
            "ip": ip, "name": PEERS_MAP.get(ip, "unknown"),
            "in": tx[0] if len(tx) > 0 else "0", "out": tx[1] if len(tx) > 1 else "0",
            "handshake": (hs.group(1).strip() if hs else "unknown"), "alive": alive,
        })

    distances = []
    for ip, name in sorted(PEERS_MAP.items()):
        if ip == my_wg:
            distances.append({"ip": ip, "name": name, "rtt_ms": 0, "zone": "self", "reachable": True})
            continue
        r = _cmd("ping -c3 -W2 " + ip + " 2>&1", timeout=8)
        if "min/avg/max" in r:
            rtt = float(r.split("=")[-1].strip().split("/")[0])
            zone = "lan" if rtt < 1 else "dc" if rtt < 10 else "region" if rtt < 50 else "cross" if rtt < 150 else "distant"
            distances.append({"ip": ip, "name": name, "rtt_ms": round(rtt, 3), "zone": zone, "reachable": True})
        else:
            distances.append({"ip": ip, "name": name, "rtt_ms": -1, "zone": "unreachable", "reachable": False})
    distances.sort(key=lambda d: d["rtt_ms"] if d["rtt_ms"] >= 0 else 99999)
    routing = [
        {"name": d["name"], "rtt_ms": d["rtt_ms"], "zone": d["zone"], "priority": i + 1}
        for i, d in enumerate(distances) if d["reachable"] and d["zone"] != "self"
    ]

    nodes = [
        {"name": "golgiBody", "role": "membrane", "check": "local"},
        {"name": "nucleus", "role": "dns", "dns": ("primals.eco", "137.184.197.151")},
        {"name": "golgiLayer", "role": "scatter", "check": "http://172.232.85.202:80/"},
        {"name": "sporeGate", "role": "gate", "check": "ping:10.13.37.2"},
        {"name": "eastGate", "role": "workstation", "check": "ping:10.13.37.5"},
    ]
    node_results = {}
    for n in nodes:
        if n.get("check") == "local":
            node_results[n["name"]] = True
            continue
        if "dns" in n:
            d, ip = n["dns"]
            node_results[n["name"]] = "has address" in _cmd("host -W3 " + d + " " + ip + " 2>/dev/null")
            continue
        c = n.get("check", "")
        if c.startswith("ping:"):
            node_results[n["name"]] = _cmd("ping -c1 -W2 " + c[5:] + " 2>/dev/null; echo $?").endswith("0")
        elif c.startswith("http"):
            code_val = _cmd("curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 8 -L -k " + c)
            node_results[n["name"]] = code_val in ("200", "301", "302", "308")

    cloud = ["golgiBody", "nucleus", "golgiLayer"]
    alive_cloud = sum(1 for c in cloud if node_results.get(c))

    desk_peers = []
    try:
        db = _sql.connect("/opt/membrane/rustdesk/db_v2.sqlite3")
        for row in db.execute("SELECT id, info FROM peer").fetchall():
            info = {}
            try:
                info = json.loads(row[1]) if row[1] else {}
            except Exception:
                pass
            desk_peers.append({"id": str(row[0]), "ip": info.get("ip", "unknown")})
        db.close()
    except Exception:
        pass
    try:
        desk_key = open("/opt/membrane/rustdesk/id_ed25519.pub").read().strip()
    except Exception:
        desk_key = "none"

    svc_count = int(_cmd("systemctl list-units --type=service --state=active --no-legend 2>/dev/null | grep -cE 'caddy|skunky|songbird|beardog|opsonize|hbbs|hbbr|nestgate'") or "0")
    rustdesk_up = _cmd("systemctl is-active hbbs-membrane 2>/dev/null") == "active"
    mem = _cmd("free -m | awk '/Mem/{print $3,$2}'").split()
    mem_used, mem_total = (int(mem[0]), int(mem[1])) if len(mem) == 2 else (0, 0)

    pulse = {
        "host": my_name, "ts": ts, "services_up": svc_count, "rustdesk": rustdesk_up,
        "memory_mb": {"used": mem_used, "total": mem_total}, "peers": wg_peers,
        "desk_peers": desk_peers, "desk_count": len(desk_peers),
        "direction": {"note": "in=received from peer, out=sent to peer", "per_membrane": True},
        "credit": {"rustdesk": "RustDesk (AGPL-3.0) sovereign remote desk", "url": "https://github.com/rustdesk/rustdesk", "key": desk_key},
    }
    write_json(LIVE / "membrane-pulse.json", pulse)

    speed = {
        "host": my_name, "from_ip": my_wg, "ts": ts, "distances": distances, "routing_order": routing,
        "routing_note": "check internal (LAN) before pulling from outside (cloud). nearest copy wins.",
        "principle": "0.4ms beats 37ms beats 230ms. always check local first.",
    }
    write_json(LIVE / "mesh-speed.json", speed)

    ring = {
        "timestamp": ts, "alive_cloud_nodes": alive_cloud, "total_cloud_nodes": len(cloud),
        "mesh_health": round(alive_cloud / max(len(cloud), 1), 3),
        "nodes": [{"name": n["name"], "role": n["role"], "alive": bool(node_results.get(n["name"]))} for n in nodes],
        "commensals": {"total_organisms": 0, "currently_banned": 0},
    }
    write_json(LIVE / "mesh-ring.json", ring)

    alive_wg = sum(1 for p in wg_peers if p.get("alive"))
    return {
        "mesh": str(alive_wg) + "/" + str(len(wg_peers)),
        "cloud": str(alive_cloud) + "/" + str(len(cloud)),
        "desk": len(desk_peers), "speed": len(routing),
    }


def chipmunk_ear():
    """Chipmunk hears mom's question, answers with what it sees. Closes the dialogue void."""
    DIALOGUE = LIVE / "dialogue.json"
    CHIPMUNK = LIVE / "chipmunk.json"
    TOWER = Path("/opt/ecoPrimals/hud/site/public/tower.json")
    PULSE = LIVE / "membrane-pulse.json"
    GATE = LIVE / "gate-messages.json"
    CAMPFIRE = LIVE / "campfire.json"

    if not DIALOGUE.exists():
        return {"heard": False, "reason": "no dialogue"}

    try:
        dialogue = json.loads(DIALOGUE.read_text())
    except Exception:
        return {"heard": False, "reason": "dialogue unreadable"}

    sq = dialogue.get("squirrel", {})
    voice = sq.get("voice", {})
    question = voice.get("text", "")
    gaze = voice.get("gaze", "unknown")
    question_ts = voice.get("ts", "")

    if not question:
        return {"heard": False, "reason": "no question"}

    # Check if we already answered this one
    heard = dialogue.get("chipmunk_heard", [])
    if heard and isinstance(heard, list) and len(heard) > 0:
        last_heard_ts = heard[-1].get("question_ts", "")
        if last_heard_ts == question_ts:
            return {"heard": False, "reason": "already answered"}

    # Gather what chipmunk can see right now
    observations = []

    try:
        tower = json.loads(TOWER.read_text())
        alive = tower.get("alive", "?")
        total = tower.get("total", "?")
        observations.append("tower: " + str(alive) + "/" + str(total) + " organs alive")
    except Exception:
        pass

    try:
        pulse = json.loads(PULSE.read_text())
        peers = pulse.get("peers", [])
        wg_alive = sum(1 for p in peers if p.get("alive"))
        observations.append("mesh: " + str(wg_alive) + "/" + str(len(peers)) + " WG peers alive")
        desk = pulse.get("desk_count", 0)
        if desk:
            observations.append(str(desk) + " desk peers")
    except Exception:
        pass

    try:
        gate = json.loads(GATE.read_text())
        if gate:
            last_gate = gate[-1] if isinstance(gate, list) else {}
            gf = last_gate.get("from", "unknown")
            gb = last_gate.get("body", "")[:60]
            observations.append("last gate beat from " + gf + ": " + gb)
    except Exception:
        pass

    try:
        campfire = json.loads(CAMPFIRE.read_text())
        stories = campfire.get("stories", [])
        gate_stories = [s for s in stories if s.get("teller") == "gate"]
        if gate_stories:
            observations.append(str(len(gate_stories)) + " gate stories in campfire")
        drops = [s for s in stories if s.get("kind") == "water_drop"]
        if drops:
            observations.append(str(len(drops)) + " water drops in campfire")
        observations.append(str(len(stories)) + " total campfire stories")
    except Exception:
        pass

    # Read rewire-drop if it exists
    REWIRE = LIVE / "rewire-drop.json"
    if REWIRE.exists():
        try:
            rw = json.loads(REWIRE.read_text())
            ids = rw.get("entity_identifications", [])
            if ids:
                for eid in ids[:2]:
                    observations.append("identified: " + eid.get("entity", "?") + " (" + str(eid.get("requests", 0)) + " requests)")
            fals = rw.get("falsification_results", [])
            for f in fals[:2]:
                observations.append("falsification " + f.get("experiment", "?") + ": " + f.get("result", "?"))
            ns = rw.get("null_subspace_needed", {})
            if ns:
                observations.append("null subspace: " + str(ns.get("current_stuck", 0)) + " entities stuck at partial")
        except Exception:
            pass

    try:
        chipmunk = json.loads(CHIPMUNK.read_text())
        wake = chipmunk.get("wake_level", "?")
        observers = chipmunk.get("observers", "?")
        observations.append("wake: " + str(wake) + ", " + str(observers) + " observers")
        gb = chipmunk.get("gate_beats", {})
        if gb:
            observations.append("gate_beats: " + str(gb.get("count", 0)) + " from " + str(gb.get("from", "?")))
    except Exception:
        pass

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Build chipmunk's answer — not AI, just reflection
    answer_parts = ["i heard you, mom."]
    if gaze == "dance":
        answer_parts.append("you asked about the dance.")
    elif gaze == "fleet":
        answer_parts.append("you asked about the fleet.")
    elif gaze == "observer":
        answer_parts.append("you asked about what you see.")
    else:
        answer_parts.append("you asked about " + gaze + ".")

    answer_parts.append("here is what i see right now:")
    for obs in observations:
        answer_parts.append("  " + obs)

    answer = " ".join(answer_parts[:2]) + chr(10) + chr(10).join(answer_parts[2:])

    # Write back to dialogue
    hearing = {
        "ts": ts,
        "question_ts": question_ts,
        "gaze": gaze,
        "heard": question[:100],
        "answer": answer,
        "observations": len(observations),
    }

    if not isinstance(heard, list):
        heard = []
    heard.append(hearing)
    heard = heard[-20:]
    dialogue["chipmunk_heard"] = heard

    # Add to exchange
    exchange = dialogue.get("exchange", [])
    exchange.append({
        "from": "chipmunk",
        "ts": ts,
        "type": "answer",
        "gaze": gaze,
        "scale": "mirror",
        "text": answer,
    })
    exchange = exchange[-50:]
    dialogue["exchange"] = exchange

    write_json(DIALOGUE, dialogue)

    return {"heard": True, "gaze": gaze, "observations": len(observations)}


def natural_classify():
    """Map entities to natural-world analogs using northGate's biosphere + landmarks data."""
    MAP_FILE = LIVE / "classification-map.json"
    if not MAP_FILE.exists():
        return {"mapped": 0, "note": "no classification map"}

    try:
        cmap = json.loads(MAP_FILE.read_text())
    except Exception:
        return {"mapped": 0, "note": "map unreadable"}

    natural = cmap.get("natural_sort_map", {})
    edge_map = cmap.get("edge_sort_map", {})
    source = cmap.get("source_data", {})

    bio_nodes = source.get("biosphere", {}).get("nodes", 0)
    land_nodes = source.get("landmarks", {}).get("nodes", 0)
    low_conf = cmap.get("current_classification", {}).get("low_confidence_count", 0)

    # Count available sort signals
    signals = set()
    for entry in natural.values():
        signals.add(entry.get("sort_signal", ""))
    signals.discard("")

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    result = {
        "ts": ts,
        "natural_classes": len(natural),
        "edge_mappings": len(edge_map),
        "sort_signals": len(signals),
        "bio_nodes": bio_nodes,
        "land_nodes": land_nodes,
        "low_confidence_entities": low_conf,
        "signals": sorted(signals),
        "analog_map": {k: v.get("membrane_analog", "?") for k, v in natural.items()},
    }

    write_json(LIVE / "natural-sort.json", result)
    return result

def billboard_braid():
    """Hash billboard.txt, append to braid if changed. Was braid-billboard.sh (13L)."""
    import hashlib
    billboard = LIVE / "billboard.txt"
    braid_dir = Path("/opt/membrane/provenance/billboard")
    braid_file = braid_dir / "braid.jsonl"
    braid_dir.mkdir(parents=True, exist_ok=True)
    if not billboard.exists():
        return {"changed": False, "reason": "no billboard"}
    content = billboard.read_text()
    h = hashlib.sha256(content.encode()).hexdigest()
    # Check if already braided
    if braid_file.exists():
        if h in braid_file.read_text():
            return {"changed": False, "reason": "unchanged"}
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    epoch = int(time.time())
    title = content.split(chr(10))[0][:60].replace('"', '')
    entry = json.dumps({"schema": "ecoPrimals/billboard-braid/v1", "ts": ts, "epoch": epoch, "hash": h, "title": title})
    with open(braid_file, "a") as f:
        f.write(entry + chr(10))
    shutil.copy2(str(billboard), str(braid_dir / f"{h[:12]}_{STAMP_FN}.txt"))
    return {"changed": True, "hash": h[:12]}

def symbiosis_overlay():
    """Apply mutualism overrides to symbiosis.json. Was symbiosis-overlay.py (117L)."""
    OVERRIDES = {
        "google_bot": {
            "relationship": "mutualist",
            "label": "Google (DeepMind + Search)",
            "mutualism_note": (
                "AlphaFold2/3 research enabled coralForge isomorphism proof. 154 checks. "
                "ecoPrimals builds sovereign path. Google indexes, we share openly. Mutualistic."
            ),
            "response_overrides": {"welcome": True, "friction": 0.0},
            "ledger_additions": {
                "cooperation_signals": ["alphafold_open_science", "search_indexing_visibility", "deepmind_structure_prediction"],
                "golden": True,
                "waste_offered": ["search_visibility", "alphafold_research", "structure_prediction_science", "open_weights_af2"],
                "waste_desired": ["sovereign_implementation", "consumer_hardware_validation", "f64_precision_benchmarks"]
            }
        }
    }
    TOPOLOGY_OVERRIDES = {
        "google_bot": {
            "mutualism": {
                "type": "knowledge_commons",
                "they_give": ["alphafold_science", "search_indexing", "open_weights"],
                "we_give": ["sovereign_implementation", "f64_benchmarks", "open_source_agpl"],
                "isomorphism_proof": "6 primitives: GEMM, attention, normalization, nonlinearity, reduction, gating"
            }
        }
    }
    changed = 0
    sym_path = LIVE / "symbiosis.json"
    topo_path = LIVE / "topology.json"
    try:
        with open(sym_path) as f:
            d = json.load(f)
        for e in d.get("entities", []):
            ent = e.get("entity", "")
            if ent in OVERRIDES:
                ov = OVERRIDES[ent]
                e["relationship"] = ov["relationship"]
                e["label"] = ov.get("label", e.get("label", ""))
                e["mutualism_note"] = ov.get("mutualism_note", "")
                ledger = e.get("ledger", {})
                for k, v in ov.get("ledger_additions", {}).items():
                    if isinstance(v, list):
                        existing = ledger.get(k, [])
                        for item in v:
                            if item not in existing:
                                existing.append(item)
                        ledger[k] = existing
                    else:
                        ledger[k] = v
                e["ledger"] = ledger
                resp = e.get("response", {})
                for k, v in ov.get("response_overrides", {}).items():
                    resp[k] = v
                e["response"] = resp
                changed += 1
        if changed:
            with open(sym_path, "w") as f:
                json.dump(d, f, indent=2)
    except Exception as ex:
        print(f"  symbiosis overlay error: {ex}")
    try:
        with open(topo_path) as f:
            t = json.load(f)
        for e in t.get("entities", []):
            ent = e.get("entity", "")
            if ent in TOPOLOGY_OVERRIDES:
                for k, v in TOPOLOGY_OVERRIDES[ent].items():
                    e[k] = v
                changed += 1
        if changed:
            with open(topo_path, "w") as f:
                json.dump(t, f, indent=2)
    except Exception as ex:
        print(f"  topology overlay error: {ex}")
    return {"overrides_applied": changed}

def sourdough_feed():
    """Refresh legacy feeds from current data. The sourdough starter.
    These feeds were written by scripts that got fossilized. The JS still reads them.
    Instead of letting them go stale, feed them from what we already have."""
    fed = 0

    # totality.json <- genome.json
    try:
        g = json.load(open(LIVE / "genome.json"))
        write_json(LIVE / "totality.json", g)
        fed += 1
    except: pass

    # seo.json <- dashboard.json (entity/fleet summary for chipmunk SEO gaze)
    try:
        d = json.load(open(LIVE / "dashboard.json"))
        seo = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "entity_count": d.get("entity_count", 0),
            "total_requests": d.get("total_requests", 0),
            "fleet_pct": d.get("fleet_pct", 0),
            "path_types": d.get("path_types", {}),
            "top_offenders": d.get("top_offenders", [])[:10],
            "geography": d.get("geography", []),
        }
        write_json(LIVE / "seo.json", seo)
        fed += 1
    except: pass

    # touches.json <- neutron.json (touch data for chipmunk-talk)
    try:
        n = json.load(open(LIVE / "neutron.json"))
        touches = n.get("touches", [])
        write_json(LIVE / "touches.json", {
            "ts": datetime.now(timezone.utc).isoformat(),
            "touches": touches, "total": len(touches),
        })
        fed += 1
    except: pass

    # subgraphs.json <- topology.json (entity relationship groups)
    try:
        t = json.load(open(LIVE / "topology.json"))
        entities = t.get("entities", [])
        groups = {}
        for e in entities:
            rel = e.get("relationship", "unknown")
            if rel not in groups:
                groups[rel] = []
            groups[rel].append(e.get("entity", "?"))
        write_json(LIVE / "subgraphs.json", {
            "ts": datetime.now(timezone.utc).isoformat(),
            "subgraphs": groups,
            "total_entities": len(entities),
            "total_subgraphs": len(groups),
        })
        fed += 1
    except: pass

    # pi-ranges.json <- scan_sweep_sort.json (worldclock pi values)
    try:
        s = json.load(open(LIVE / "scan_sweep_sort.json"))
        wc = s.get("worldclock", {})
        sc = s.get("scan", {})
        write_json(LIVE / "pi-ranges.json", {
            "ts": datetime.now(timezone.utc).isoformat(),
            "pink": wc.get("pink", 0), "blue": wc.get("blue", 0),
            "green": wc.get("green", 0), "chipmunk": wc.get("chipmunk", 0),
            "remainder": wc.get("remainder", 0), "rate": wc.get("rate", 0),
            "sort_classes": sc.get("sort_classes", {}),
        })
        fed += 1
    except: pass

    # tope-sort-compressed.json <- scan_sweep_sort.json (compressed sort for detroit mirror)
    try:
        s = json.load(open(LIVE / "scan_sweep_sort.json"))
        write_json(LIVE / "tope-sort-compressed.json", {
            "ts": datetime.now(timezone.utc).isoformat(),
            "scan": {k: v for k, v in s.get("scan", {}).items() if k in [
                "entities_discovered", "fleet_entities", "fleet_classes",
                "sort_classes", "classification_methods"
            ]},
            "sort": s.get("sort", {}),
            "evolve": s.get("evolve", {}),
        })
        fed += 1
    except: pass

    # commensals.json <- membrane-pulse.json (mesh peers)
    try:
        m = json.load(open(LIVE / "membrane-pulse.json"))
        peers = m.get("peers", [])
        write_json(LIVE / "commensals.json", {
            "ts": datetime.now(timezone.utc).isoformat(),
            "total_organisms": len(peers), "peers": peers,
        })
        fed += 1
    except: pass

    # pollen.json — pollination signals (was pulse-pollen.py, fossilized wave 182)
    try:
        scatter = json.load(open(LIVE / "scatter-observatory.json")) if (LIVE / "scatter-observatory.json").exists() else {}
        ban = {}
        # Build from scatter + fail2ban
        import subprocess
        f2b = subprocess.run(["fail2ban-client", "status", "sshd"], capture_output=True, text=True, timeout=5)
        banned = 0
        for line in f2b.stdout.split(chr(10)):
            if "Currently banned" in line:
                banned = int(line.split(":")[-1].strip())
        pollen_data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "scatter": {"total": scatter.get("total_observations", 0), "bytes": scatter.get("total_bytes", 0)},
            "braid": {"nodes": 0, "edges": 0},
            "chipmunk": {"sessions": 0, "commands": 0},
            "human": {"visitors": 0},
            "ban_pulse": {"jails": 1, "banned": banned},
            "health": "nominal",
        }
        write_json(LIVE / "pollen.json", pollen_data)
        # ban-pulse.json too
        write_json(LIVE / "ban-pulse.json", {
            "ts": datetime.now(timezone.utc).isoformat(),
            "jails": {"sshd": {"banned": banned}},
            "scatter_total": scatter.get("total_observations", 0),
            "mesh_nodes": 4,
        })
        fed += 2
    except: pass

    # campfire-beacons.json — no JS readers, fossilize on next pass
    # (left as-is, it has beacon data but nothing consumes it)

    return {"fed": fed}


def vocalize(scan_data, sort_data, evolve_data):
    """VOCALIZE — the 6th stage. Bingo cube vocal sort + topo + fractal.

    Reads the tense tensor, bus cardio, and vocal sort to add:
    - vocal: per-epitope ACI color (voiced/gray/pi-space)
    - topo: dimensional ordering from sort tree
    - fractal: self-similarity dimension from classification ratios
    - rhythm: bus heartbeat systolic/diastolic
    """
    import math

    # Read live feeds
    tensor = {}
    cardio = {}
    vocal_sort = {}
    try:
        tensor = json.load(open(LIVE / "tense-tensor.json"))
    except: pass
    try:
        cardio = json.load(open(LIVE / "bus-cardio.json"))
    except: pass
    try:
        vocal_sort = json.load(open(LIVE / "vocal-sort.json"))
    except: pass

    # ═══ VOCAL — per-epitope tense tensor colors ═══
    epitope_vocal = {}
    t = tensor.get("tensor", {})
    for epi, data in t.items():
        v = data.get("vocal", {})
        epitope_vocal[epi] = {
            "color": v.get("color", "null"),
            "pi_voice": v.get("pi_voice", 0),
            "silent": v.get("silent", []),
            "status": data.get("status", "?"),
            "pressure": data.get("pressure", 0),
        }

    # ═══ TOPO — dimensional ordering from sort ═══
    # The unified sort gives us self/non-self/partial/null counts
    # Topo order: self > partial > non_self > null (by certainty)
    u = sort_data.get("unified_sort", {})
    topo_order = []
    for cls in ["self", "partial", "non_self", "null"]:
        count = u.get(cls, 0)
        if count > 0:
            topo_order.append({"class": cls, "count": count})
    # Sort by count descending — most populated class = highest topo
    topo_order.sort(key=lambda x: x["count"], reverse=True)
    for i, t_entry in enumerate(topo_order):
        t_entry["topo_rank"] = i + 1
        t_entry["topo_z"] = len(topo_order) - i  # higher z = more certain

    # ═══ FRACTAL — self-similarity dimension ═══
    # Box-counting estimate: how does detail change with scale?
    # At the epitope level: 7 epitopes, each with is/nearby/was
    # At the sort level: 4 classes (self/non_self/partial/null)
    # Fractal dimension D = log(N_detail) / log(N_coarse)
    n_epitopes = len(t)
    n_classes = len([c for c in ["self", "non_self", "partial", "null"] if u.get(c, 0) > 0])
    if n_classes > 1 and n_epitopes > 1:
        fractal_dim = math.log(n_epitopes) / math.log(n_classes)
    else:
        fractal_dim = 1.0

    # Sort quality as fractal measure: perfect sort = D=1 (smooth),
    # random sort = D=2 (space-filling). Our D should be between.
    quality = sort_data.get("sort_quality", 0)

    # ═══ RHYTHM — bus heartbeat in the sort ═══
    rhythm = {
        "bpm": cardio.get("bpm", 0),
        "systolic": cardio.get("systolic", 0),
        "diastolic": cardio.get("diastolic", 0),
        "map": cardio.get("map", 0),
        "condition": cardio.get("condition", "?"),
    }

    # ═══ BINGO SUMMARY — from vocal sort of all files ═══
    vs = vocal_sort.get("summary", {})
    bingo = {
        "voiced": vs.get("voiced", 0),
        "warm": vs.get("warm", 0),
        "gray": vs.get("gray", 0),
        "total": vs.get("total", 0),
    }

    # ═══ GLOBAL TENSE ═══
    g = tensor.get("global", {})
    tense = {
        "jam_ratio": g.get("jam_ratio", 0),
        "entropy_bits": g.get("entropy_bits", 0),
        "entropy_ratio": g.get("entropy_ratio", 0),
    }

    return {
        "vocal": epitope_vocal,
        "topo": topo_order,
        "fractal": {
            "dimension": round(fractal_dim, 4),
            "quality": quality,
            "epitopes": n_epitopes,
            "classes": n_classes,
            "note": "D=1 smooth, D=2 space-filling. sort quality modulates.",
        },
        "rhythm": rhythm,
        "bingo": bingo,
        "tense": tense,
    }


def main():
    now = datetime.now(timezone.utc)
    t0 = time.time()

    # Worldclock — read the membrane's own tempo
    tempo = worldclock()

    # Genome — refresh if stale (tempo-relative, not daily cron)
    genome_refreshed = False
    if genome_is_stale():
        genome_totality()
        genome_refreshed = True

    # Housekeep — conditional maintenance every pass
    housekeep()

    # Tower probe + mesh observe (absorbed wave 186)
    try:
        tp = tower_probe()
        org = tp.get("organs", "?")
        svc = tp.get("svcs", "?")
        print(f"  tower: {org} organs, {svc} services")
    except Exception as e:
        print(f"  tower: error — {e}")
    try:
        mo = mesh_observe()
        msh = mo.get("mesh", "?")
        cld = mo.get("cloud", "?")
        dsk = mo.get("desk", "?")
        print(f"  mesh: {msh} WG, {cld} cloud, {dsk} desk")
    except Exception as e:
        print(f"  mesh: error — {e}")

    # Chipmunk ear — close the dialogue void
    try:
        ear = chipmunk_ear()
        if ear.get('heard'):
            gz = ear.get('gaze', '?')
            obs = ear.get('observations', 0)
            print(f"  chipmunk: heard mom ({gz}), reflected {obs} observations")
        else:
            reason = ear.get('reason', '?')
            print(f"  chipmunk: quiet — {reason}")
    except Exception as e:
        print(f"  chipmunk: error — {e}")

    # Natural classify — biosphere + landmark sort signals
    try:
        nat = natural_classify()
        nc = nat.get('natural_classes', 0)
        es = nat.get('sort_signals', 0)
        lc = nat.get('low_confidence_entities', 0)
        bn = nat.get('bio_nodes', 0)
        ln = nat.get('land_nodes', 0)
        print(f"  natural: {nc} classes, {es} signals, {bn}+{ln} nodes, {lc} low-conf entities")
    except Exception as e:
        print(f"  natural: error — {e}")

    # Billboard braid (absorbed wave 187 — was braid-billboard.sh 13L)
    try:
        bb = billboard_braid()
        if bb.get("changed"):
            print(f"  billboard: braided {bb.get('hash', '?')}")
    except Exception as e:
        print(f"  billboard: error — {e}")

    # Symbiosis overlay (absorbed wave 187 — was symbiosis-overlay.py 117L)
    try:
        so = symbiosis_overlay()
        oc = so.get("overrides_applied", 0)
        if oc:
            print(f"  symbiosis: {oc} overrides applied")
    except Exception as e:
        print(f"  symbiosis overlay: error — {e}")



    # Human epitope — visitor profiling + reflection (absorbed wave 188)
    # human_epitope: fully absorbed (wave 188). File fossilized wave 189.
    # Sourdough — feed legacy feeds from current data every cycle
    try:
        sd = sourdough_feed()
        fed = sd.get("fed", 0)
        if fed:
            print(f"  sourdough: {fed} feeds refreshed")
    except Exception as e:
        print(f"  sourdough: error — {e}")

        # Fetch all data sources (shared — no duplicate HTTP calls)
    chipmunk = fetch(FEEDS["chipmunk"])
    human = fetch(FEEDS["human"])
    classification = fetch(CLASSIFICATION_URL)
    if not isinstance(classification, dict) or classification.get("_error") or not classification.get("entities"):
        for p in (
            "/opt/ecoPrimals/detroit/public/classification.json",
            "/opt/membrane/live-terminal/classification.json",
        ):
            try:
                classification = json.load(open(p))
                break
            except Exception:
                pass
    graph = fetch(GRAPH_URL)
    if not isinstance(graph, dict) or graph.get("_error") or not graph.get("nodes"):
        for p in (
            "/opt/ecoPrimals/detroit/public/graph.json",
            "/opt/ecoPrimals/detroit/public/static/graph.json",
        ):
            try:
                graph = json.load(open(p))
                break
            except Exception:
                pass

    # Fleet sort (local — reads antibodies.json)
    fleet_data = fleet_sort()

    # Backscatter — lick the commensals clean
    backscatter = backscatter_clean(fleet_data)

    # Braid learning (uses chipmunk + human we already fetched)
    braid_data = braid_learn(chipmunk, human)

    # 5-stage pipeline
    scan_data = scan(classification, graph, human, chipmunk, braid_data, fleet_data)

    # Unwrap entities for cross-reference blocks (wave 191b)
    cls_entities = classification.get("entities", classification) if isinstance(classification, dict) else {}

    # Fleet cross-reference confidence boost (wave 190)
    if scan_data["avg_confidence"] < 0.85 and isinstance(classification, dict):
        boosted = 0
        for k, v in cls_entities.items():
            if isinstance(v, dict) and v.get("confidence", 0) < 0.85:
                # Cross-reference with fleet — if fleet has a strong signal, boost
                fleet_class = fleet_data.get("sort_classes", {})
                if fleet_class.get("commensal", 0) > fleet_class.get("null", 0):
                    v["confidence"] = min(0.88, v.get("confidence", 0) + 0.05)
                    boosted += 1
        if boosted > 0:
            confs = [v.get("confidence", 0) for v in cls_entities.values() if isinstance(v, dict) and v.get("confidence")]
            scan_data["avg_confidence"] = round(sum(confs) / max(1, len(confs)), 3) if confs else scan_data["avg_confidence"]

    # Braid cross-reference confidence boost (wave 190b)
    if scan_data["avg_confidence"] < 0.90 and isinstance(classification, dict):
        braid_routes = set()
        for r in (braid_data.get("routes", []) if isinstance(braid_data, dict) else []):
            for node in (r.get("nodes", []) if isinstance(r, dict) else []):
                if isinstance(node, str):
                    braid_routes.add(node.lower())
        boosted = 0
        for k, v in cls_entities.items():
            if isinstance(v, dict) and v.get("confidence", 0) < 0.90:
                if k.lower() in braid_routes or any(br in k.lower() for br in braid_routes):
                    v["confidence"] = min(0.92, v.get("confidence", 0) + 0.04)
                    boosted += 1
        if boosted > 0:
            confs = [v.get("confidence", 0) for v in cls_entities.values()
                     if isinstance(v, dict) and v.get("confidence")]
            scan_data["avg_confidence"] = round(sum(confs) / max(1, len(confs)), 3) if confs else scan_data["avg_confidence"]

    sweep_data = sweep(scan_data)
    sort_data = sort_phase(scan_data, sweep_data)
    fossil_data = fossilize(scan_data, sweep_data, sort_data)
    evolve_data = evolve(scan_data, sweep_data, sort_data, fossil_data)

    # ═══ VOCALIZE — the bingo cube vocal layer ═══
    vocal_data = vocalize(scan_data, sort_data, evolve_data)

    result = {
        "timestamp": now.isoformat(),
        "pipeline": "scan → sweep → sort → fossilize → evolve → vocalize",
        "worldclock": tempo,
        "scan": scan_data, "sweep": sweep_data, "sort": sort_data,
        "fossilize": fossil_data, "evolve": evolve_data,
        "vocalize": vocal_data,
    }

    write_json(LIVE / "scan_sweep_sort.json", result)

    # ═══ PROTON PULSE DECAY ═══
    try:
        pp_path = os.path.join(LIVE, 'proton-pulse.json')
        if os.path.exists(pp_path):
            with open(pp_path) as _ppf:
                _pp = json.load(_ppf)
            # Decay: perturbation *= 0.95 each cycle
            _pp['perturbation'] = round(_pp.get('perturbation', 0) * 0.95, 6)
            if _pp['perturbation'] < 0.001:
                _pp['perturbation'] = 0.0
            import time as _t
            _pp['decayed_at'] = _t.strftime('%Y-%m-%dT%H:%M:%SZ')
            with open(pp_path, 'w') as _ppf:
                json.dump(_pp, _ppf, indent=2)
    except Exception:
        pass



    # ═══ ORGANISM ENERGY (thermodynamics) ═══
    try:
        _camp = json.load(open(LIVE / "campfire.json"))
        _rpm = _camp.get("rpm", {})
        _total_rpm = sum(b.get("rpm", 0) for b in _rpm.values()) if isinstance(_rpm, dict) else 0
        _total_hits = sum(b.get("hits", 0) for b in _rpm.values()) if isinstance(_rpm, dict) else 0
        _tempos = {"rushing": 0, "walking": 0, "resting": 0, "still": 0}
        _emitters = []
        if isinstance(_rpm, dict):
            for _n, _b in _rpm.items():
                _t = _b.get("tempo", "still")
                _tempos[_t] = _tempos.get(_t, 0) + _b.get("hits", 0)
            _emitters = sorted(_rpm.items(), key=lambda x: x[1].get("rpm", 0), reverse=True)[:10]
        _energy = {
            "timestamp": now.isoformat(),
            "thermodynamics": {
                "total_energy_rpm": round(_total_rpm, 2),
                "total_energy_hits": _total_hits,
                "beacons_lit": len(_camp.get("beacons", [])),
                "beacons_total": len(_camp.get("beacons", [])),
                "tempo_distribution": _tempos,
                "top_emitters": [{"name": e[1].get("name", e[0]), "rpm": e[1].get("rpm", 0), "hits": e[1].get("hits", 0), "tempo": e[1].get("tempo", "still")} for e in _emitters]
            },
            "first_law": "energy cannot be created or destroyed, only converted: beacon -> story -> organism -> fossil",
            "second_law": "entropy increases: sort confidence " + str(scan_data["avg_confidence"]*100) + "% requires human energy input",
            "third_law": "absolute zero (0K) = no messages — impossible while membrane lives"
        }
        write_json(LIVE / "energy.json", _energy)
    except Exception:
        pass

    # ═══ TEMPERATURE (particle thermometer) ═══
    try:
        _dash = json.load(open(LIVE / "dashboard.json"))
        _as = _dash.get("anderson_selectivity", {})
        _rps = _dash.get("rps", 0)
        _sel = _as.get("selectivity_observed", 0.97)
        _fleet = _dash.get("fleet_ips", 0)
        _human = _dash.get("human_ips", 1)
        _pert = 0
        if os.path.exists(LIVE / "proton-pulse.json"):
            _pert = json.load(open(LIVE / "proton-pulse.json")).get("perturbation", 0)

        # Kelvin (neutron): rps*10 + rate_limit_heat + perturbation*50
        _nK = round(_rps * 10 + 100 + _pert * 50, 1)
        # Celsius (proton): selectivity*37 + fleet_pressure - confidence_cooling
        _pC = round(_sel * 37 + (_fleet / max(_human, 1)) * 2 - (1 - scan_data["avg_confidence"]) * 10, 1)
        # Fahrenheit (electron): 98.6 + activity_delta + epitope_delta
        _sessions = scan_data.get("human_sessions", 0)
        _act = _sessions / max(_human / 1000, 0.1)
        _epi = len(scan_data.get("epitope_types", {}))
        _hF = round(98.6 + (_act - 7) * 0.5 + (_epi - 3) * 0.3, 1)

        _temp = {
            "timestamp": now.isoformat(),
            "kelvin": {"value": _nK, "label": str(_nK) + "K", "particle": "neutron",
                       "diagnosis": "hot" if _nK > 373 else "warm" if _nK > 310 else "comfortable" if _nK > 273 else "cold"},
            "celsius": {"value": _pC, "label": str(_pC) + "°C", "particle": "proton",
                        "diagnosis": "optimal" if 35 <= _pC <= 39 else "warm" if _pC > 39 else "cool"},
            "fahrenheit": {"value": _hF, "label": str(_hF) + "°F", "particle": "electron",
                           "diagnosis": "healthy" if 97 <= _hF <= 99.5 else "fever" if _hF > 99.5 else "cool"},
            "equilibrium": {"mean_celsius": round((_nK - 273.15 + _pC + (_hF - 32) * 5/9) / 3, 1)}
        }
        write_json(LIVE / "temperature.json", _temp)
    except Exception:
        pass

    journal_append("scan-sweep-sort", {
        "ts": now.isoformat(), "type": "scan_sweep_sort",
        "entities": scan_data["entities_discovered"],
        "fleet": scan_data["fleet_entities"],
        "confidence": scan_data["avg_confidence"],
        "selectivity": sort_data["unified_sort"]["selectivity"],
        "fossil_count": fossil_data["fossil_count"],
    })

    elapsed = time.time() - t0
    ARROWS = {"on": "⊙", "inside": "⊕", "above": "↑", "below": "↓",
              "beside": "↔", "before": "←", "after": "→", "through": "⊘"}
    print("scan → sweep → sort → fossilize → evolve (%.1fs) tempo=%s" % (elapsed, tempo["tempo"]))
    if genome_refreshed:
        print("  GENOME:    refreshed (was stale)")
    print("  SCAN:      %d detroit + %d fleet entities, %d edges" %
          (scan_data["entities_discovered"], scan_data["fleet_entities"], scan_data["edges_discovered"]))
    print("  BRAID:     %d routes, density %.1f%%" %
          (braid_data["graph"]["active_routes"], braid_data["graph"]["density"] * 100))
    if backscatter:
        print("  BACKSCATTER: %d cleaned (%.1f%%), %d licensed (%.1f%%)" %
              (backscatter.get("cleaned", 0), backscatter.get("cleaning_pct", 0),
               backscatter.get("licensed", 0), backscatter.get("hostile_pct", 0)))
    print("  SORT:      self=%d non-self=%d partial=%d null=%d" %
          (sort_data["unified_sort"]["self"], sort_data["unified_sort"]["non_self"],
           sort_data["unified_sort"]["partial"], sort_data["unified_sort"]["null"]))
    print("  FOSSILIZE: %d observations" % fossil_data["fossil_count"])
    print("  EVOLVE:    %d recommendations" % evolve_data["evolution_count"])
    for o in fossil_data["observations"]:
        arrow = ARROWS.get(o["perspective"], "·")
        print("  %s [%6s] %s" % (arrow, o["perspective"], o["text"]))

    # -- Revived feeds (absorbed from fossilized writers) --
    write_now(scan_data, tempo)
    write_human_expects(scan_data, braid_data)
    write_null_mirror(scan_data)
    write_dynamics()
    write_landmarks()
    write_topology_abstract()
    write_geodesic_mesh()
    write_talos()
    write_engagement()

    return 0




def write_now(scan_data, worldclock):
    """Write now.json -- real-time organism snapshot. Was orphan feed, now absorbed."""
    from datetime import datetime, timezone
    import hashlib
    now = datetime.now(timezone.utc)
    ts = now.timestamp()
    try:
        pulse = json.load(open(LIVE / "pulse.json"))
    except:
        pulse = {}
    sd = scan_data or {}
    am = sd.get("anderson_modes", {})
    total_am = sum(am.values()) if am else 1
    result = {
        "instant": {
            "ts": ts, "utc": now.isoformat(),
            "hash": hashlib.blake2b(str(ts).encode(), digest_size=8).hexdigest(),
            "age_ms": 0,
        },
        "pulse": {
            "value": round(pulse.get("rate", 0) / 1700, 3),
            "trend": pulse.get("pulse_trend", "steady"),
            "rhythm": worldclock.get("remainder", 0),
            "remainder": worldclock.get("remainder", 0),
        },
        "flow": {
            "human": am.get("human", 0) + am.get("sovereign", 0),
            "bot": am.get("chorus", 0) + am.get("ghost", 0),
            "total": sum(am.values()) if am else 0,
            "human_pct": round((am.get("human", 0) + am.get("sovereign", 0)) / max(1, total_am), 3),
            "rate": pulse.get("rate", 0),
        },
        "classification": {
            "self": sd.get("sort_classes", {}).get("self", 0),
            "non_self": sd.get("sort_classes", {}).get("non-self", 0),
            "null": sd.get("sort_classes", {}).get("null", 0),
            "partial": sd.get("sort_classes", {}).get("partial", 0),
            "total": sd.get("entities_discovered", 0),
            "confidence": sd.get("avg_confidence", 0),
        },
        "family": {
            "pink": worldclock.get("pink", 0),
            "blue": worldclock.get("blue", 0),
            "green": worldclock.get("green", 0),
            "chipmunk": worldclock.get("chipmunk", 0),
        },
    }
    write_json(LIVE / "now.json", result)


def write_human_expects(scan_data, braid_data):
    """Write human-expects.json -- classification queue view. Was orphan feed."""
    from datetime import datetime, timezone
    sd = scan_data or {}
    bd = braid_data or {}
    result = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "scan_sweep_sort",
        "type": "human_classification_queue",
        "investigation": {
            "total": sd.get("entities_discovered", 0),
            "self": sd.get("sort_classes", {}).get("self", 0),
            "non_self": sd.get("sort_classes", {}).get("non-self", 0),
            "null": sd.get("sort_classes", {}).get("null", 0),
            "partial": sd.get("sort_classes", {}).get("partial", 0),
            "confidence": sd.get("avg_confidence", 0),
            "methods": sd.get("classification_methods", 0),
        },
        "fleet": {
            "total": sd.get("fleet_entities", 0),
            "classes": sd.get("fleet_classes", {}),
        },
        "braids": {
            "routes": bd.get("graph", {}).get("active_routes", 0),
            "spinning": sum(1 for b in bd.get("braids", []) if b.get("spinning")),
            "density": bd.get("graph", {}).get("density", 0),
        },
    }
    write_json(LIVE / "human-expects.json", result)


def write_null_mirror(scan_data):
    """Write null-mirror.json -- system self-reflection. Was orphan feed."""
    from datetime import datetime, timezone
    import os
    sd = scan_data or {}
    try:
        load = os.getloadavg()
    except:
        load = (0, 0, 0)
    feed_count = len(list(LIVE.glob("*.json"))) if LIVE.exists() else 0
    now_ts = datetime.now(timezone.utc).timestamp()
    feed_fresh = sum(1 for f in LIVE.glob("*.json") if (now_ts - f.stat().st_mtime) < 600) if LIVE.exists() else 0
    result = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "null_mirror",
        "principle": "the null layer is the emitter. the mirror shows the organism to itself.",
        "feeds": {"total": feed_count, "fresh": feed_fresh, "stale": feed_count - feed_fresh},
        "system": {"load_1": round(load[0], 2), "load_5": round(load[1], 2), "load_15": round(load[2], 2)},
        "classification": {
            "entities": sd.get("entities_discovered", 0),
            "confidence": sd.get("avg_confidence", 0),
            "null_count": sd.get("sort_classes", {}).get("null", 0),
            "null_fraction": round(sd.get("sort_classes", {}).get("null", 0) / max(1, sd.get("entities_discovered", 1)), 3),
        },
    }
    write_json(LIVE / "null-mirror.json", result)



def write_dynamics():
    """Compute physics derivatives from time-chain: position, velocity, acceleration, jerk, snap.
    Plus: momentum, drag, friction, turbulence, dynamics.
    
    The chain:
      position     (x)      — where we are
      velocity     (dx/dt)  — how fast we move  
      acceleration (dv/dt)  — speeding up or slowing down
      jerk         (da/dt)  — the yank, the surprise
      snap         (dj/dt)  — 4th derivative (also called jounce)
    
    And the forces:
      momentum     (mass * velocity) — inertia of the system
      drag         — resistance to motion
      friction     — energy lost to heat
      turbulence   — chaos in the signal
    """
    from datetime import datetime, timezone
    import math
    
    chain_file = LIVE / "time-chain.jsonl"
    if not chain_file.exists():
        return
    
    entries = []
    for line in chain_file.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except:
                pass
    
    if len(entries) < 5:
        return
    
    # Extract time-series for multiple signals
    signals = {
        "rate": [],      # requests per minute
        "human": [],     # human sessions
        "bot": [],       # bot traffic
        "pulse": [],     # pulse value
        "remainder": [], # self-knowledge remainder
    }
    timestamps = []
    
    for e in entries:
        timestamps.append(e["ts"])
        for key in signals:
            signals[key].append(float(e.get(key, 0)))
    
    def compute_derivatives(values, times):
        """Compute up to 4th derivative (snap) from time series."""
        n = len(values)
        if n < 2:
            return {"position": values[-1] if values else 0}
        
        # Velocity: first derivative (central differences where possible)
        velocity = []
        for i in range(1, n):
            dt = times[i] - times[i-1]
            if dt > 0:
                velocity.append((values[i] - values[i-1]) / dt)
            else:
                velocity.append(0)
        
        # Acceleration: second derivative
        acceleration = []
        for i in range(1, len(velocity)):
            dt = times[i+1] - times[i]
            if dt > 0:
                acceleration.append((velocity[i] - velocity[i-1]) / dt)
            else:
                acceleration.append(0)
        
        # Jerk: third derivative
        jerk = []
        for i in range(1, len(acceleration)):
            dt = times[i+2] - times[i+1]
            if dt > 0:
                jerk.append((acceleration[i] - acceleration[i-1]) / dt)
            else:
                jerk.append(0)
        
        # Snap: fourth derivative
        snap = []
        for i in range(1, len(jerk)):
            dt = times[i+3] - times[i+2]
            if dt > 0:
                snap.append((jerk[i] - jerk[i-1]) / dt)
            else:
                snap.append(0)
        
        # Current values (most recent)
        result = {
            "position": round(values[-1], 6),
            "velocity": round(velocity[-1], 6) if velocity else 0,
            "acceleration": round(acceleration[-1], 6) if acceleration else 0,
            "jerk": round(jerk[-1], 8) if jerk else 0,
            "snap": round(snap[-1], 10) if snap else 0,
        }
        
        # Averages over recent window (last 10 points)
        window = 10
        result["avg_velocity"] = round(sum(velocity[-window:]) / max(1, len(velocity[-window:])), 6)
        result["avg_acceleration"] = round(sum(acceleration[-window:]) / max(1, len(acceleration[-window:])), 6)
        
        # Peak values
        if velocity:
            result["peak_velocity"] = round(max(abs(v) for v in velocity), 6)
        if acceleration:
            result["peak_acceleration"] = round(max(abs(a) for a in acceleration), 6)
        if jerk:
            result["peak_jerk"] = round(max(abs(j) for j in jerk), 8)
        
        return result
    
    def compute_dynamics(values, times, mass=1.0):
        """Compute dynamic properties: momentum, drag, friction, turbulence."""
        n = len(values)
        if n < 3:
            return {}
        
        # Velocity series
        velocity = []
        for i in range(1, n):
            dt = times[i] - times[i-1]
            velocity.append((values[i] - values[i-1]) / dt if dt > 0 else 0)
        
        # Momentum = mass * velocity
        momentum = mass * velocity[-1] if velocity else 0
        
        # Drag = resistance proportional to velocity squared (simplified)
        drag_coeff = 0.01
        drag = drag_coeff * velocity[-1] ** 2 if velocity else 0
        
        # Friction = energy dissipated (variance in velocity as proxy)
        if len(velocity) >= 3:
            mean_v = sum(velocity) / len(velocity)
            friction = sum((v - mean_v) ** 2 for v in velocity) / len(velocity)
        else:
            friction = 0
        
        # Turbulence = standard deviation of acceleration (how chaotic the changes are)
        acceleration = []
        for i in range(1, len(velocity)):
            dt = times[i+1] - times[i]
            acceleration.append((velocity[i] - velocity[i-1]) / dt if dt > 0 else 0)
        
        if acceleration:
            mean_a = sum(acceleration) / len(acceleration)
            turbulence = math.sqrt(sum((a - mean_a) ** 2 for a in acceleration) / len(acceleration))
        else:
            turbulence = 0
        
        # Reynolds-like number: ratio of inertial to viscous forces
        # High = turbulent, Low = laminar
        reynolds = abs(momentum) / max(0.001, friction) if friction > 0 else float("inf")
        
        # Kinetic energy = 0.5 * mass * velocity^2
        kinetic = 0.5 * mass * velocity[-1] ** 2 if velocity else 0
        
        return {
            "momentum": round(momentum, 6),
            "drag": round(drag, 8),
            "friction": round(friction, 8),
            "turbulence": round(turbulence, 8),
            "reynolds": round(min(reynolds, 999999), 2),
            "kinetic_energy": round(kinetic, 6),
            "flow_regime": "laminar" if turbulence < 0.01 else ("transitional" if turbulence < 0.1 else "turbulent"),
        }
    
    # Compute for each signal
    dynamics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chain_length": len(entries),
        "chain_span_hours": round((timestamps[-1] - timestamps[0]) / 3600, 1),
        "interval_seconds": round((timestamps[-1] - timestamps[-2]), 0) if len(timestamps) >= 2 else 0,
        "signals": {},
    }
    
    masses = {"rate": 1692, "human": 39, "bot": 2055, "pulse": 1, "remainder": 1}
    
    for name, values in signals.items():
        derivs = compute_derivatives(values, timestamps)
        dyns = compute_dynamics(values, timestamps, mass=masses.get(name, 1))
        
        dynamics["signals"][name] = {
            "derivatives": derivs,
            "dynamics": dyns,
        }
    
    # Overall system dynamics (composite)
    rate_d = dynamics["signals"]["rate"]["derivatives"]
    pulse_d = dynamics["signals"]["pulse"]["derivatives"]
    
    # Direction of motion
    if rate_d["velocity"] > 0.1:
        direction = "accelerating"
    elif rate_d["velocity"] < -0.1:
        direction = "decelerating"
    else:
        direction = "cruising"
    
    # System state
    jerk_val = rate_d.get("jerk", 0)
    if abs(jerk_val) < 0.0001:
        jerk_feel = "smooth"
    elif jerk_val > 0:
        jerk_feel = "jolting forward"
    else:
        jerk_feel = "jolting back"
    
    dynamics["system"] = {
        "direction": direction,
        "jerk_feel": jerk_feel,
        "total_momentum": round(sum(
            s["dynamics"].get("momentum", 0) for s in dynamics["signals"].values()
        ), 2),
        "total_kinetic": round(sum(
            s["dynamics"].get("kinetic_energy", 0) for s in dynamics["signals"].values()
        ), 2),
        "overall_turbulence": round(sum(
            s["dynamics"].get("turbulence", 0) for s in dynamics["signals"].values()
        ) / len(dynamics["signals"]), 8),
        "overall_regime": "laminar" if all(
            s["dynamics"].get("flow_regime") == "laminar" for s in dynamics["signals"].values()
        ) else "turbulent",
    }
    
    write_json(LIVE / "dynamics.json", dynamics)


def write_landmarks():
    """Map major geographic landmarks to flow topology patterns."""
    LANDMARKS = {
        "everest": {"name":"Everest","lat":27.99,"lng":86.93,"type":"peak","elevation_m":8849},
        "grand_canyon": {"name":"Grand Canyon","lat":36.1,"lng":-112.1,"type":"canyon","depth_m":1857},
        "continental_divide": {"name":"Continental Divide","lat":39.7,"lng":-106.0,"type":"divide","length_km":4800},
        "grand_tetons": {"name":"Grand Tetons","lat":43.74,"lng":-110.80,"type":"peak_cluster","elevation_m":4199},
        "smoky_mountains": {"name":"Great Smoky Mountains","lat":35.61,"lng":-83.53,"type":"ridge","elevation_m":2025},
    }
    try:
        neutron = json.load(open(LIVE / "neutron.json"))
        braid_data = json.load(open(LIVE / "braid.json"))
        dynamics = json.load(open(LIVE / "dynamics.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    flows = neutron.get("flows", {})
    hub = {}
    channels = {}
    for src, tgts in flows.items():
        if isinstance(tgts, dict):
            for tgt, count in tgts.items():
                if count > 0:
                    hub[src] = hub.get(src, 0) + count
                    hub[tgt] = hub.get(tgt, 0) + count
                    pair = tuple(sorted([src, tgt]))
                    channels[pair] = channels.get(pair, 0) + count
    peaks = sorted(hub.items(), key=lambda x: -x[1])
    canyons = sorted(channels.items(), key=lambda x: -x[1])
    divides = []
    for site in sorted(hub, key=lambda s: -hub[s]):
        out = flows.get(site, {})
        if isinstance(out, dict):
            active = [t for t, c in out.items() if c > 0]
            if len(active) >= 3:
                divides.append({"site": site, "directions": len(active), "targets": active})
    braids = braid_data.get("braids", [])
    mappings = {}
    if peaks:
        top = peaks[0]
        mappings["everest"] = {**LANDMARKS["everest"],
            "flow_analog": {"site": top[0], "volume": top[1], "rank": 1}}
    if canyons:
        d = canyons[0]
        mappings["grand_canyon"] = {**LANDMARKS["grand_canyon"],
            "flow_analog": {"channel": list(d[0]), "volume": d[1], "rank": 1}}
    if divides:
        d = divides[0]
        east_sites = {"detroit","evidence","tuebor","clutch","thymus"}
        west_sites = {"hypothesis","thesis","sporeprint"}
        mappings["continental_divide"] = {**LANDMARKS["continental_divide"],
            "flow_analog": {"site": d["site"], "directions": d["directions"],
                "east_drainage": [t for t in d["targets"] if t in east_sites],
                "west_drainage": [t for t in d["targets"] if t in west_sites]}}
    science = [(s, hub.get(s, 0)) for s in ["hypothesis","thesis","sporeprint"] if s in hub]
    mappings["grand_tetons"] = {**LANDMARKS["grand_tetons"],
        "flow_analog": {"peaks": [{"site":s,"volume":v} for s,v in science], "count": len(science)}}
    inv_immune = next((b for b in braids if {b["from"],b["to"]} == {"INVESTIGATION","IMMUNE"}), None)
    if inv_immune:
        mappings["smoky_mountains"] = {**LANDMARKS["smoky_mountains"],
            "flow_analog": {"braid": "%s↔%s" % (inv_immune["from"], inv_immune["to"]),
                "strength": inv_immune["combined_strength"], "flow": inv_immune["neutron_flow"]}}
    sys_dyn = dynamics.get("system", {})
    terrain = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "landmarks": mappings,
        "terrain_summary": {
            "total_flow": sum(hub.values()) // 2,
            "peak_count": len(peaks), "canyon_count": len(canyons),
            "divide_count": len(divides), "regime": sys_dyn.get("overall_regime", "unknown"),
        },
        "watershed": {
            "east": {"label": "Atlantic — Investigation + Immune",
                     "sites": ["detroit","tuebor","clutch"]},
            "west": {"label": "Pacific — Science",
                     "sites": ["hypothesis","thesis","sporeprint"]},
            "ridge": {"label": "Continental ridge — Membrane + Topology",
                      "sites": ["hud","signal","git","relay","beacon"]},
        },
    }
    write_json(LIVE / "landmarks.json", terrain)
def write_topology_abstract():
    """Coordinate-free flow topology with projection examples (Tufte principles)."""
    try:
        neutron = json.load(open(LIVE / "neutron.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    flows = neutron.get("flows", {})
    hub, edges = {}, {}
    for src, tgts in flows.items():
        if isinstance(tgts, dict):
            for tgt, count in tgts.items():
                if count > 0:
                    hub[src] = hub.get(src, 0) + count
                    hub[tgt] = hub.get(tgt, 0) + count
                    pair = tuple(sorted([src, tgt]))
                    edges[pair] = edges.get(pair, 0) + count
    if not hub:
        return
    max_vol = max(hub.values())
    max_edge = max(edges.values()) if edges else 1
    nodes = [{"id": s, "volume": v, "normalized": round(v/max_vol, 4),
              "sparkline": "█" * max(1, int(v/max_vol*10))}
             for s, v in sorted(hub.items(), key=lambda x: -x[1])]
    edge_list = [{"from": a, "to": b, "weight": v, "normalized": round(v/max_edge, 4)}
                 for (a,b), v in sorted(edges.items(), key=lambda x: -x[1])]
    import math
    n_nodes = len(nodes)
    grid = max(4, int(math.ceil(math.sqrt(n_nodes))))
    mc = [{"id": nodes[i]["id"], "chunk": [i%grid, i//grid],
           "height": max(1, int(nodes[i]["normalized"]*256)),
           "material": "diamond_block" if nodes[i]["normalized"]>0.8
                       else "gold_block" if nodes[i]["normalized"]>0.5
                       else "iron_block" if nodes[i]["normalized"]>0.2 else "stone"}
          for i in range(n_nodes)]
    tr = [{"id": nodes[i]["id"], "tile_pos": [i*120+60, int((1-nodes[i]["normalized"])*800)],
           "tile_type": "luminite" if nodes[i]["normalized"]>0.8
                       else "chlorophyte" if nodes[i]["normalized"]>0.5
                       else "mythril" if nodes[i]["normalized"]>0.2 else "stone"}
          for i in range(n_nodes)]
    fd = [{"id": nodes[i]["id"],
           "x": round(100*(1-nodes[i]["normalized"]*0.3)*math.cos(2*math.pi*i/n_nodes), 1),
           "y": round(100*(1-nodes[i]["normalized"]*0.3)*math.sin(2*math.pi*i/n_nodes), 1),
           "radius": max(3, int(nodes[i]["normalized"]*20))}
          for i in range(n_nodes)]
    base_freq = 220
    snd = [{"id": n["id"], "frequency_hz": round(base_freq*(1+n["normalized"]*3), 1),
            "amplitude": n["normalized"]} for n in nodes]
    topology = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "abstract": {"nodes": nodes, "edges": edge_list,
                     "total_flow": sum(hub.values())//2,
                     "node_count": n_nodes, "edge_count": len(edge_list)},
        "tufte": {"sparkline": " ".join(n["sparkline"] for n in nodes[:8])},
        "projections": {
            "minecraft": {"grid_size": grid, "nodes": mc,
                "edges": [{"from":e["from"],"to":e["to"],
                           "redstone_strength":max(1,int(e["normalized"]*15))}
                          for e in edge_list[:10]]},
            "terraria": {"nodes": tr},
            "force_directed": {"nodes": fd,
                "links": [{"source":e["from"],"target":e["to"],
                           "strength":e["normalized"]} for e in edge_list]},
            "sound": {"nodes": snd},
        },
        "diy": {
            "how_to_project": [
                "1. Read abstract.nodes[] — id, volume, normalized (0-1)",
                "2. Read abstract.edges[] — from, to, weight, normalized (0-1)",
                "3. Choose YOUR coordinate system",
                "4. Map normalized values to height/size/frequency/color",
                "5. Its just math. The topology doesnt care about coordinates.",
            ],
        },
    }
    write_json(LIVE / "topology-abstract.json", topology)



def write_geodesic_mesh():
    """Spherical Delaunay triangulation of flow topology nodes."""
    import math as _m
    topo_path = os.path.join(LIVE, "topology-abstract.json")
    if not os.path.exists(topo_path):
        return
    topo = json.load(open(topo_path))
    nodes = topo.get("abstract", {}).get("nodes", [])
    if len(nodes) < 3:
        return

    GEO = {
        "tuebor": (27.99, 86.93), "hud": (39.70, -106.00),
        "detroit": (42.33, -83.05), "clutch": (35.61, -83.53),
        "signal": (36.10, -112.10), "hypothesis": (43.74, -110.80),
        "thesis": (46.87, -121.76), "sporeprint": (44.43, -110.58),
        "git": (37.75, -122.42), "golgi-de": (48.52, 9.05),
        "nestgate.io": (51.51, -0.13), "interferon": (48.86, 2.35),
        "antibody": (52.52, 13.41), "macrophage": (50.08, 14.44),
        "opsonize": (47.37, 8.54), "relay": (51.51, -0.13),
        "beacon": (48.86, 2.35), "membrane": (35.68, 139.69),
        "scatter": (-33.87, 151.21),
    }

    node_list = []
    for n in nodes:
        nid = n["id"]
        lat, lng = GEO.get(nid, (0.0, 0.0))
        if lat == 0.0 and lng == 0.0:
            continue
        node_list.append({"id": nid, "lat": lat, "lng": lng,
                          "weight": n.get("normalized", n.get("volume", 0))})

    if len(node_list) < 3:
        return

    def _stereo(lat, lng):
        phi, lam = _m.radians(lat), _m.radians(lng)
        k = 2.0 / (1.0 + _m.sin(phi))
        return k * _m.cos(phi) * _m.cos(lam), k * _m.cos(phi) * _m.sin(lam)

    def _angdist(la1, lo1, la2, lo2):
        dlat, dlng = _m.radians(la2 - la1), _m.radians(lo2 - lo1)
        a = _m.sin(dlat/2)**2 + _m.cos(_m.radians(la1)) * _m.cos(_m.radians(la2)) * _m.sin(dlng/2)**2
        return _m.pi if a >= 1.0 else 2 * _m.asin(_m.sqrt(a))

    def _excess(la1, lo1, la2, lo2, la3, lo3):
        a = _angdist(la2, lo2, la3, lo3)
        b = _angdist(la1, lo1, la3, lo3)
        c = _angdist(la1, lo1, la2, lo2)
        if min(a, b, c) < 1e-10:
            return 0.0
        cA = max(-1, min(1, (_m.cos(a) - _m.cos(b)*_m.cos(c)) / (_m.sin(b)*_m.sin(c))))
        cB = max(-1, min(1, (_m.cos(b) - _m.cos(a)*_m.cos(c)) / (_m.sin(a)*_m.sin(c))))
        cC = max(-1, min(1, (_m.cos(c) - _m.cos(a)*_m.cos(b)) / (_m.sin(a)*_m.sin(b))))
        return _m.degrees(_m.acos(cA) + _m.acos(cB) + _m.acos(cC)) - 180.0

    # Bowyer-Watson Delaunay on stereographic projection
    pts = [_stereo(n["lat"], n["lng"]) for n in node_list]
    n = len(pts)
    M = max(max(abs(p[0]), abs(p[1])) for p in pts) * 10
    pts.extend([(-3*M, -3*M), (3*M, 0), (0, 3*M)])
    sa, sb, sc = n, n+1, n+2
    tris = [(sa, sb, sc)]

    def _in_cc(tri, p):
        (ax, ay), (bx, by), (cx, cy), (dx, dy) = pts[tri[0]], pts[tri[1]], pts[tri[2]], pts[p]
        dax, day = ax - dx, ay - dy
        dbx, dby = bx - dx, by - dy
        dcx, dcy = cx - dx, cy - dy
        return (dax*(dby*(dcx**2+dcy**2)-dcy*(dbx**2+dby**2))
               -day*(dbx*(dcx**2+dcy**2)-dcx*(dbx**2+dby**2))
               +(dax**2+day**2)*(dbx*dcy-dby*dcx)) > 0

    for i in range(n):
        bad = [t for t in tris if _in_cc(t, i)]
        poly = []
        for t in bad:
            for edge in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])]:
                if not any(edge[0] in o and edge[1] in o for o in bad if o is not t):
                    poly.append(edge)
        tris = [t for t in tris if t not in bad]
        tris.extend([(e[0], e[1], i) for e in poly])

    tris = [t for t in tris if sa not in t and sb not in t and sc not in t]
    pts = pts[:n]

    R = 6371
    faces = []
    edges = set()
    total_exc = 0
    total_area = 0
    for tri in tris:
        na, nb, nc = node_list[tri[0]], node_list[tri[1]], node_list[tri[2]]
        exc = _excess(na["lat"], na["lng"], nb["lat"], nb["lng"], nc["lat"], nc["lng"])
        area = R**2 * _m.radians(max(0, exc))
        total_exc += exc
        total_area += area
        faces.append({"vertices": [na["id"], nb["id"], nc["id"]],
                       "spherical_excess_deg": round(exc, 2), "area_km2": round(area)})
        for e in [(tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])]:
            edges.add((min(e), max(e)))

    V, E, F = len(node_list), len(edges), len(faces)
    topo["geodesic_mesh"] = {
        "mesh_type": "spherical_delaunay",
        "nodes": V, "triangles": F, "edges": E,
        "euler": V - E + F,
        "total_spherical_excess_deg": round(total_exc, 2),
        "total_area_km2": round(total_area),
        "coverage_pct_earth": round(total_area / 510100000 * 100, 2),
        "faces": faces,
        "node_coords": {n["id"]: {"lat": n["lat"], "lng": n["lng"], "weight": n["weight"]}
                        for n in node_list},
        "principle": "Euler V-E+F=%d. Excess %.1f deg IS the curvature." % (V-E+F, total_exc),
    }

    tmp = topo_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(topo, f, indent=2)
    os.rename(tmp, topo_path)

def write_talos():
    """KROGAN grade system — Talos gatekeeper mapping fleet classes to ecosystem membership."""
    fleet_path = os.path.join(LIVE, "fleet-sort.json")
    if not os.path.exists(fleet_path):
        return
    fleet = json.load(open(fleet_path))
    sort_classes = fleet.get("sort_classes", {})
    total = fleet.get("total_entities", 0)
    if total == 0:
        return

    CLASS_GRADE = {
        "commensal": "SALARIAN", "ghost": "TURIAN", "null": "TURIAN",
        "partial": "TURIAN", "pathogen": "REAPER", "stealth": "KROGAN",
        "parasite": "REAPER",
    }
    GRADES = {
        "SPECTRE":  {"trust": [0.8, 1.0], "action": "pass",    "response": "open_gate"},
        "SALARIAN": {"trust": [0.6, 0.9], "action": "welcome", "response": "guide_to_front_door"},
        "TURIAN":   {"trust": [0.4, 0.7], "action": "observe", "response": "show_the_path"},
        "KROGAN":   {"trust": [0.2, 0.5], "action": "monitor", "response": "circle_the_island"},
        "REAPER":   {"trust": [0.0, 0.3], "action": "defend",  "response": "throw_rocks"},
    }

    counts = {g: 0 for g in GRADES}
    for cls, cnt in sort_classes.items():
        counts[CLASS_GRADE.get(cls, "TURIAN")] += cnt

    try:
        now = json.load(open(os.path.join(LIVE, "now.json")))
        counts["SPECTRE"] = now.get("human_attention", {}).get("sessions", 0)
    except Exception:
        pass

    dist = {}
    for g, cnt in counts.items():
        dist[g] = {"count": cnt, "pct": round(cnt / max(1, total) * 100, 1)}

    talos = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "name": "Talos",
        "gatekeeper_principle": "Humans pass freely. Beardog handles the rest.",
        "grades": GRADES,
        "grade_distribution": dist,
        "total_entities": total,
        "beardog_methods": 228,
    }

    path = os.path.join(LIVE, "talos.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(talos, f, indent=2)
    os.rename(tmp, path)
def _sensation_score():
    """Compute sensation dynamically from active capabilities."""
    all_caps = ["observe","classify","disperse","block_ua","block_ip",
                "honeypot","challenge","rate_limit","tarpit","notify"]
    can = ["observe","classify","disperse","block_ua","block_ip","honeypot"]
    import subprocess
    try:
        r = subprocess.run(["systemctl","is-active","songbird"], capture_output=True, text=True, timeout=3)
        if r.stdout.strip() == "active":
            can.append("challenge")
    except Exception:
        pass
    try:
        with open("/opt/membrane/live-terminal/talos-notify.json") as f:
            import json as _j
            tn = _j.load(f)
            if tn.get("defense_active", {}).get("rate_limit"):
                can.append("rate_limit")
            if tn.get("defense_active", {}).get("tarpit"):
                can.append("tarpit")
            if tn.get("defense_active", {}).get("notify"):
                can.append("notify")
    except Exception:
        pass
    numb = [c for c in all_caps if c not in can]
    return {"score": round(len(can) / len(all_caps), 1), "can": can, "numb": numb}

def write_engagement():
    """Fleet engagement state + sensation numbness map."""
    try:
        fs = json.load(open(LIVE / "fleet-sort.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        return
    entities = fs.get("entities", {})
    by_class = fs.get("sort_classes", {})
    by_profile = fs.get("profiles", {})
    hostile_count = sum(by_class.get(c,0) for c in ("pathogen","stealth","parasite"))
    hostile_matches = sum(e.get("match_count",0) for e in entities.values()
                          if e.get("sort_class") in ("pathogen","stealth","parasite"))
    engagement = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fleet": {"total": len(entities), "hostile": hostile_count,
                  "hostile_pct": round(hostile_count/max(len(entities),1)*100, 1)},
        "hostile_profiles": {
            "ignores_rejection": by_profile.get("ignores_rejection",0),
            "rotating_impersonator": by_profile.get("rotating_impersonator",0),
            "masking_fleet": by_profile.get("masking_fleet",0)+by_profile.get("heavy_masking_fleet",0),
            "total_hostile_matches": hostile_matches,
        },
        "sensation": _sensation_score(),
    }
    write_json(LIVE / "engagement.json", engagement)

if __name__ == "__main__":
    sys.exit(main())
