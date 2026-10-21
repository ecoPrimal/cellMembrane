#!/usr/bin/env python3
"""Neutron writer — adaptive, tied to RPM and pulse.
NOT cron. NOT clock. PULSE.

Rate is determined by the membrane's actual activity:
  RPM > 2000 → update every 30s (concert/event)
  RPM > 500  → update every 60s (active)
  RPM > 100  → update every 120s (normal)
  RPM < 100  → update every 300s (quiet/gaming/sleeping)

Anderson: the localization length determines how far info travels.
Gradient: northgate's gradient determines the direction of flow.
RootPulse: the heartbeat synchronizes everything.
Neural API: the capability mesh connects all surfaces.

The neutron IS the messaging axis. It breathes with the membrane.
"""

import json, os, glob, urllib.request, time
from collections import defaultdict
from datetime import datetime, timezone

LIVE = "/opt/membrane/live-terminal"

def compute_pulse_direction(pulse, flows, external_touches, total_crossings):
    """Compute the membrane's fluid systems — biology has already solved this.
    
    Real biology doesn't have one in/out metric. It has separate systems:
    
    BLOOD (cardiovascular) — bidirectional, pump-driven
      Arteries: content served outward (humans reading)
      Veins: engagement returning (humans clicking deeper)
      Heart: RPM — the pump
      
    LYMPH (lymphatic) — one-way INWARD, no pump
      Always absorbing. Filters threats. Processes at lymph nodes.
      The immune surfaces ARE the lymphatic system.
      Driven by body movement (walking tempo), not a pump.
      
    SEBUM (sebaceous) — one-way OUTWARD, secretion
      Protective surface layer. Published content.
      The investigation being shared externally.
      
    INTERSTITIAL — the medium between surfaces
      Cross-surface flows. The tissue everything floats in.
    """
    rpm = pulse.get("rate", 0)
    human = pulse.get("human", 0)
    bot = pulse.get("bot", 0)
    
    # ── IMMUNE SURFACES (lymphatic system) ──
    immune_names = {"antibody","antigen","bloom","complement","cytokine","epitope",
                    "interferon","lysozyme","macrophage","opsonize","receptor","thymus"}
    
    # Count lymphatic flows (immune surface crossings)
    lymph_flow = 0
    blood_flow = 0
    for src in flows:
        for tgt in flows[src]:
            count = flows[src][tgt]
            if src in immune_names or tgt in immune_names:
                lymph_flow += count
            else:
                blood_flow += count
    
    # ── IN-PULSE (world → membrane) ──
    in_total = sum(sum(refs.values()) for refs in external_touches.values())
    
    # ── OUT-PULSE (membrane → world) ──
    out_total = total_crossings + human
    
    # ── FLUID SYSTEMS ──
    total = max(in_total + out_total, 1)
    in_ratio = round(in_total / total, 4)
    out_ratio = round(out_total / total, 4)
    
    # Blood: human traffic (bidirectional — they bring attention IN, carry content OUT)
    blood_cells = human
    blood_pressure = round(human / max(human + bot, 1), 4)
    
    # Lymph: immune processing (one-way inward — ALWAYS absorbing, that's correct)
    lymph_active = lymph_flow > 0
    lymph_volume = lymph_flow
    
    # Sebum: outward secretion (content published, shared externally)
    # Surfaces with resting/walking tempo that aren't immune = secreting content
    sebum_flow = blood_flow  # non-immune cross-surface flows
    
    # Interstitial: the medium (bot traffic is the fluid everything floats in)
    interstitial = bot
    
    # ── OVERALL CIRCULATION STATE ──
    # Key insight: lymphatic ABSORBING is healthy, not stagnant
    # Stagnant = no fluid moving AT ALL (no humans, no lymph, no crossings)
    if blood_cells == 0 and lymph_volume == 0 and total_crossings == 0:
        state = "stagnant"       # truly nothing moving
    elif blood_pressure < 0.02 and lymph_volume == 0:
        state = "lymph_only"     # immune system active but no blood flow
    elif abs(in_ratio - out_ratio) < 0.2:
        state = "balanced"       # healthy circulation
    elif in_ratio > out_ratio:
        state = "absorbing"      # more intake — lymphatic doing its job
    else:
        state = "radiating"      # more output — sebum secreting
    
    # ── SIGMOID PRESSURE ──
    # The logistic curve of information transfer
    # Capacity ~5000 RPM for a 2GB VPS
    import math
    capacity = 5000
    x = (rpm / capacity - 0.5) * 10
    sigmoid = round(1 / (1 + math.exp(-x)), 4)
    
    return {
        "in_pulse": in_total,
        "out_pulse": out_total,
        "in_ratio": in_ratio,
        "out_ratio": out_ratio,
        "state": state,
        "human_carry": human,
        "bot_consume": bot,
        "sigmoid": sigmoid,
        "fluids": {
            "blood": {
                "cells": blood_cells,
                "pressure": blood_pressure,
                "flow": blood_flow,
            },
            "lymph": {
                "active": lymph_active,
                "volume": lymph_volume,
                "surfaces": len(immune_names),
            },
            "sebum": {
                "flow": sebum_flow,
            },
            "interstitial": {
                "volume": interstitial,
            }
        }
    }


def read_neural():
    """Neural API from campfire — all surfaces and their RPM/tempo.
    biomeOS is the orchestrator, but campfire is the living data.
    86 surfaces, each with RPM, tempo, hits, visitors."""
    try:
        with open(os.path.join(LIVE, "campfire.json")) as f:
            c = json.load(f)
            rpm_data = c.get("rpm", {})
            # Count by tempo (activity state)
            tempo_counts = {}
            total_rpm = 0
            active_surfaces = 0
            for name, data in rpm_data.items():
                tempo = data.get("tempo", "unknown")
                tempo_counts[tempo] = tempo_counts.get(tempo, 0) + 1
                rpm_val = data.get("rpm", 0)
                total_rpm += rpm_val
                if rpm_val > 0.1:
                    active_surfaces += 1
            return {
                "total_surfaces": len(rpm_data),
                "active_surfaces": active_surfaces,
                "total_rpm": round(total_rpm, 1),
                "tempo_distribution": tempo_counts,
            }
    except:
        return None


def read_anderson():
    """Anderson localization — determines how far info travels.
    High xi = info flows freely (delocalized).
    Low xi = info stays local (localized).
    This is the physics of information reach."""
    try:
        with open("/run/membrane/anderson-profile.json") as f:
            return json.load(f)
    except:
        return None

def read_dashboard_gradient():
    """Dashboard gradient — activity patterns across entity classes.
    Spectrum, chorus, stealth, ghost, etc."""
    try:
        with open(os.path.join(LIVE, "dashboard.json")) as f:
            d = json.load(f)
            return d.get("anderson_selectivity", {})
    except:
        return None

def compute_context(pulse, anderson):
    """Detect what's happening right now.
    Concert? Gaming? Working? Sleeping? The membrane knows."""
    rpm = pulse.get("rate", 0)
    trend = pulse.get("pulse_trend", "steady")
    human = pulse.get("human", 0)
    bot = pulse.get("bot", 0)
    ratio = human / max(bot, 1)

    # Compute context from RPM patterns
    context = "steady"
    if rpm > 3000:
        context = "surge"       # concert/event/DDoS
    elif rpm > 1500 and trend == "rising":
        context = "rising"      # building attention
    elif rpm < 50 and human == 0:
        context = "dormant"     # sleeping
    elif rpm < 200 and human <= 2:
        context = "focused"     # gaming/working — low RPM, focused human
    elif ratio > 0.1:
        context = "social"      # lots of humans relative to bots
    elif trend == "falling":
        context = "cooling"     # winding down

    # Anderson tells us info reach
    reach = "local"
    if anderson:
        xi_max = 0
        for mode in anderson.get("modes", []):
            p_obs = mode.get("p_observed", 0)
            if p_obs > 0.5:
                xi_max = max(xi_max, mode.get("d_eff", 1))
        if xi_max >= 3:
            reach = "global"    # info travels freely
        elif xi_max >= 2:
            reach = "regional"  # info travels moderately
        else:
            reach = "local"     # info stays nearby

    return {
        "context": context,
        "reach": reach,
        "human_bot_ratio": round(ratio, 4),
        "human_count": human,
        "bot_count": bot,
    }

LOG_DIR = "/var/log/caddy"
PULSE_PATH = os.path.join(LIVE, "pulse.json")

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def read_pulse():
    """Read the membrane pulse — RPM, trend, rhythm."""
    try:
        with open(PULSE_PATH) as f:
            return json.load(f)
    except:
        return {"rate": 100, "pulse_trend": "unknown", "pulse_rhythm": 0}

def adaptive_interval(pulse):
    """Compute update interval from pulse RPM.
    Not clock. Pulse. The membrane breathes."""
    rpm = pulse.get("rate", 100)
    trend = pulse.get("pulse_trend", "steady")

    if rpm > 2000:
        base = 30   # concert/event — fast updates
    elif rpm > 500:
        base = 60   # active — normal updates
    elif rpm > 100:
        base = 120  # quiet — slow updates
    else:
        base = 300  # sleeping — rare updates

    # Trend modifiers
    if trend == "rising":
        base = int(base * 0.7)  # speed up when activity rising
    elif trend == "falling":
        base = int(base * 1.3)  # slow down when falling

    return max(15, min(600, base))

def classify_surface(host):
    if not host: return None
    h = host.lower().replace(".primals.eco", "").split(":")[0]
    if h in ("primals", "www", ""): return "hud"
    return h if h else None

def classify_referrer(ref):
    if not ref: return "direct"
    r = ref.lower()
    if "primals.eco" in r: return "internal"
    for name, pattern in [("google","google."),("bing","bing."),("duckduckgo","duckduckgo."),
                          ("chatgpt","chatgpt."),("chatgpt","openai."),("claude","claude."),
                          ("claude","anthropic."),("twitter","t.co"),("twitter","twitter."),
                          ("twitter","x.com"),("reddit","reddit."),("github","github.")]:
        if pattern in r: return name
    return "external"

def parse_log_line(line):
    try:
        entry = json.loads(line)
        req = entry.get("request", {})
        host = req.get("host", "")
        uri = req.get("uri", "")
        headers = req.get("headers", {})
        referer = ""
        for key in ("Referer", "referer"):
            if key in headers:
                vals = headers[key]
                referer = vals[0] if isinstance(vals, list) and vals else (vals if isinstance(vals, str) else "")
                break
        return host, uri, referer
    except:
        return None, None, None

STATIC_EXT = frozenset((".js",".css",".png",".jpg",".svg",".woff",".woff2",".ico",".json",".xml",".txt",".map"))

def fetch_channels():
    chs = {}
    for name, page in [("inbox","neutron-inbox"),("notes","neutron-notes"),
                       ("reminders","neutron-reminders"),("chat","neutron-chat")]:
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8097/api/discuss?page=" + page,
                headers={"User-Agent":"neutron-writer/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                comments = data.get("comments", [])
                chs[name] = {
                    "total": data.get("total", 0),
                    "latest_body": comments[-1].get("body", "")[:120] if comments else None,
                    "latest_ts": comments[-1].get("ts", "")[:19] if comments else None,
                }
        except:
            chs[name] = {"total": 0, "error": "offline"}
    return chs

def build_neutron():
    pulse = read_pulse()
    interval = adaptive_interval(pulse)
    anderson = read_anderson()
    gradient = read_dashboard_gradient()
    context = compute_context(pulse, anderson)
    neural = read_neural()

    flows = defaultdict(lambda: defaultdict(int))
    external_touches = defaultdict(lambda: defaultdict(int))
    page_touches = defaultdict(lambda: defaultdict(int))
    total_crossings = 0

    log_files = sorted(glob.glob(os.path.join(LOG_DIR, "access*.log")))
    for lf in log_files[-2:]:
        try:
            with open(lf) as f:
                for line in f:
                    host, uri, referer = parse_log_line(line)
                    if not host: continue
                    to_surface = classify_surface(host)
                    if not to_surface: continue
                    page = uri.split("?")[0].rstrip("/") or "/"
                    if not any(page.endswith(ext) for ext in STATIC_EXT):
                        page_touches[to_surface][page] += 1
                    if not referer:
                        external_touches[to_surface]["direct"] += 1
                        continue
                    ref_class = classify_referrer(referer)
                    if ref_class == "internal":
                        from_surface = classify_surface(referer.split("//")[-1].split("/")[0])
                        if from_surface and from_surface != to_surface:
                            flows[from_surface][to_surface] += 1
                            total_crossings += 1
                    else:
                        external_touches[to_surface][ref_class] += 1
        except:
            pass


    # ── STRUCTURAL FLOWS — cross-surface links that exist in the HTML ──
    # These represent the actual hyperlink topology between surfaces.
    # Referrer-based flows only catch a fraction (HTTPS strips cross-origin referrers).
    structural = {
        "hud": {"tuebor": 8, "detroit": 4, "signal": 3, "hypothesis": 2, "thesis": 1, "clutch": 2, "sporeprint": 2, "git": 1},
        "tuebor": {"hud": 5, "detroit": 6, "signal": 2, "hypothesis": 1, "clutch": 1, "sporeprint": 1, "git": 3},
        "detroit": {"tuebor": 4, "hud": 2, "signal": 1},
        "signal": {"tuebor": 2, "hud": 1, "detroit": 1},
        "hypothesis": {"tuebor": 1, "hud": 1, "thesis": 1},
        "thesis": {"hypothesis": 1, "tuebor": 1},
        "clutch": {"tuebor": 3, "detroit": 2, "hud": 1},
        "sporeprint": {"hud": 1, "tuebor": 1, "nestgate.io": 2},
        "nestgate.io": {"sporeprint": 1, "hud": 1},
    }
    for src, targets in structural.items():
        for tgt, count in targets.items():
            flows[src][tgt] += count
            total_crossings += count

    mirrors = []
    for from_s, targets in flows.items():
        for to_s, count in targets.items():
            if count >= 2:
                mirrors.append({"from_surface":from_s,"to_surface":to_s,"crossings":count,"last_seen":utc_now()})
    mirrors.sort(key=lambda m:-m["crossings"])

    touches = []
    for surface, refs in external_touches.items():
        for ref, count in sorted(refs.items(), key=lambda x:-x[1])[:5]:
            if count >= 2:
                tp = max(page_touches.get(surface, {"/":1}).items(), key=lambda x:x[1], default=("/",0))
                touches.append({"surface":surface,"page":tp[0],"touches":count,"referrer":ref})
    touches.sort(key=lambda t:-t["touches"])

    flow_matrix = {}
    for from_s, targets in flows.items():
        flow_matrix[from_s] = dict(sorted(targets.items(), key=lambda x:-x[1]))

    all_surfaces = set()
    for s in flows: all_surfaces.add(s)
    for s in external_touches: all_surfaces.add(s)
    for targets in flows.values():
        for s in targets: all_surfaces.add(s)
    outgoing = {s: sum(flows.get(s, {}).values()) for s in all_surfaces}
    stuck = [s for s in all_surfaces if outgoing.get(s, 0) == 0]
    radiating = [s for s, c in sorted(outgoing.items(), key=lambda x:-x[1]) if c > 5][:10]

    channels = fetch_channels()
    total_msgs = sum(ch.get("total", 0) for ch in channels.values())

    neutron = {
        "generated": utc_now(),
        "wave": 180,
        "axis": "neutron — adaptive messaging axis — tied to RPM, not clock",
        "breathing": {
            "rpm": pulse.get("rate", 0),
            "trend": pulse.get("pulse_trend", "unknown"),
            "rhythm": pulse.get("pulse_rhythm", 0),
            "interval_seconds": interval,
            "pulse_raw": pulse.get("pulse_raw", 0),
            "remainder": pulse.get("remainder", 0),
        },
        "mirrors": mirrors[:50],
        "touches": touches[:100],
        "flows": flow_matrix,
        "total_crossings": total_crossings,
        "stuck": sorted(stuck),
        "radiating": radiating,
        "surfaces_observed": len(all_surfaces),
        "channels": channels,
        "total_messages": total_msgs,
        "anderson": {
            "w_population": anderson.get("w_population", 0) if anderson else 0,
            "pielou_j": anderson.get("pielou_j", 0) if anderson else 0,
            "imaginary_magnitude": gradient.get("imaginary_magnitude", 0) if gradient else 0,
            "mode_count": gradient.get("mode_count", 0) if gradient else 0,
        } if anderson or gradient else None,
        "direction": compute_pulse_direction(pulse, flow_matrix, external_touches, total_crossings),
        "context": context,
        "neural": neural,
    }

    # ── UNIFY LAYERS ──
    # Read other feeds to build a unified connection map
    try:
        with open(os.path.join(LIVE, "braid.json")) as bf:
            braid = json.load(bf)
        site_braids = braid.get("site_braids", [])
        epitope_transitions = braid.get("epitope_transitions", [])
    except:
        braid = {}
        site_braids = []
        epitope_transitions = []

    try:
        with open(os.path.join(LIVE, "scan_sweep_sort.json")) as sf:
            sss = json.load(sf)
        scan = sss.get("scan", {})
        scan_entities = scan.get("entities_discovered", 0)
        scan_edges = scan.get("edges_discovered", 0)
        scan_nodes = scan.get("nodes_discovered", 0)
        graph_density = scan_edges / max(scan_nodes * (scan_nodes - 1) / 2, 1) if scan_nodes > 1 else 0
        evolve_recs = sss.get("evolve", {}).get("recommendations", [])
    except:
        scan_entities = 0
        scan_edges = 0
        scan_nodes = 0
        graph_density = 0
        evolve_recs = []

    try:
        with open(os.path.join(LIVE, "symbiosis.json")) as sf:
            symb = json.load(sf)
        symb_entities = symb.get("entities", [])
        symb_map = {e.get("label", ""): e.get("relationship", "?") for e in symb_entities}
    except:
        symb_map = {}

    # Add unified graph to neutron
    # ── Read additional feeds for convergence ──
    try:
        with open(os.path.join(LIVE, "stories.json")) as sf:
            _stories = json.load(sf)
        story_count = len(_stories) if isinstance(_stories, list) else len(_stories.get("billboard_mix", {}).get("mix", []))
    except:
        story_count = 0

    try:
        with open(os.path.join(LIVE, "signals.json")) as sf:
            _signals = json.load(sf)
        sig_campfire = _signals.get("campfire", {})
        sig_surfaces = sig_campfire.get("surfaces", sig_campfire.get("total_surfaces", 0))
    except:
        sig_surfaces = 0

    try:
        with open(os.path.join(LIVE, "membrane-deep.json")) as sf:
            _deep = json.load(sf)
        membrane_stack = _deep.get("membrane_stack", {})
        stack_layers = membrane_stack.get("layers", membrane_stack.get("total_layers", len(membrane_stack)))
    except:
        stack_layers = 0

    try:
        with open(os.path.join(LIVE, "falsification.json")) as sf:
            _falsify = json.load(sf)
        experiments = len(_falsify) if isinstance(_falsify, dict) else 0
    except:
        experiments = 0

    try:
        with open(os.path.join(LIVE, "type-manifest.json")) as sf:
            _types = json.load(sf)
        repo_count = _types.get("repo_count", 0)
        type_count = len(_types.get("type_index", {}))
    except:
        repo_count = 0
        type_count = 0

    try:
        with open(os.path.join(LIVE, "negentropy.json")) as sf:
            _neg = json.load(sf)
        negentropy_val = _neg.get("negentropy", _neg.get("value", 0))
    except:
        negentropy_val = 0

    try:
        with open(os.path.join(LIVE, "now.json")) as sf:
            _now = json.load(sf)
        now_state = _now.get("state", _now.get("status", "?"))
    except:
        now_state = "?"

    neutron["unified"] = {
        "layers_connected": 14,
        "feeds": ["neutron", "topology", "symbiosis", "campfire", "braid", 
                  "scan_sweep_sort", "dashboard", "stories", "signals", 
                  "membrane-deep", "falsification", "type-manifest", "negentropy", "now"],
        "graph": {
            "entities": scan_entities,
            "nodes": scan_nodes,
            "edges": scan_edges,
            "density": round(graph_density, 6),
        },
        "braids": len(site_braids),
        "braid_spin": {
            "category_braids": len(braid.get("braids", [])) if isinstance(braid, dict) else 0,
            "spinning": sum(1 for b in braid.get("braids", []) if b.get("spinning")) if isinstance(braid, dict) else 0,
            "total_flow": sum(b.get("neutron_flow", 0) for b in braid.get("braids", []) if isinstance(b, dict)) if isinstance(braid, dict) else 0,
            "strongest": braid.get("braids", [{}])[0].get("dominant_flow", "none") if isinstance(braid, dict) and braid.get("braids") else "none",
        },
        "epitope_transitions": len(epitope_transitions),
        "symbiosis_classes": dict(sorted(
            {v: list(symb_map.values()).count(v) for v in set(symb_map.values())}.items()
        )) if symb_map else {},
        "evolution": [r.get("action", "?") for r in evolve_recs[:4]],
        "stories": story_count,
        "signals_surfaces": sig_surfaces,
        "membrane_stack_layers": stack_layers,
        "falsification_experiments": experiments,
        "repos": repo_count,
        "types": type_count,
        "negentropy": negentropy_val,
        "now": now_state,
    }

    with open(os.path.join(LIVE, "neutron.json"), "w") as f:
        json.dump(neutron, f, indent=2)

    print(f"neutron: {len(mirrors)} mirrors, {total_crossings} crossings, {len(stuck)} stuck, {total_msgs} msgs | RPM={pulse.get('rate',0):.0f} interval={interval}s trend={pulse.get('pulse_trend','?')}")

if __name__ == "__main__":
    build_neutron()
