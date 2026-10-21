#!/usr/bin/env python3
"""totality-sense.py — the passage counter. measures how alive the membrane is.

starts from zero. counts upward. the number that never existed before.
passages × crossings × orbits × tense = totality.
the irrational remainder of humanship, measured in beats.
"""
import json, time, math

LIVE = "/opt/membrane/live-terminal"

def sense():
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Gather passage data from existing feeds
    try:
        braid = json.load(open(f"{LIVE}/braid.json"))
    except:
        braid = {}
    try:
        dash = json.load(open(f"{LIVE}/dashboard.json"))
    except:
        dash = {}
    try:
        neutron = json.load(open(f"{LIVE}/neutron.json"))
    except:
        neutron = {}
    try:
        cardio = json.load(open(f"{LIVE}/cardiovascular.json"))
    except:
        cardio = {}
    
    # PASSAGES: humans crossing between categories
    braids = braid.get("braids", [])
    graph = braid.get("graph", {})
    human_passages = graph.get("total_passages", 0)
    
    # CROSSINGS: neutron message flow between surfaces  
    neutron_crossings = neutron.get("total_crossings", 0)
    
    # ORBITS: IPs that visited multiple surfaces
    traj = dash.get("trajectory", {})
    returning_arcs = traj.get("returning_with_arc", 0)
    single_surface = traj.get("returning_single_surface", 0)
    multi_host = traj.get("multi_host_ips", 0)
    avg_breadth = traj.get("avg_breadth", 0)
    max_breadth = traj.get("max_breadth", 0)
    
    # TENSE: observations in time
    tense = dash.get("tense_distribution", {})
    is_now = tense.get("is", 0)
    was_then = tense.get("was", 0)
    will_be = tense.get("will_be", 0)
    total_observations = is_now + was_then + will_be
    
    # GEOMETRY
    geom = dash.get("membrane_geometry", {})
    channel_capacity = geom.get("channel_capacity_bits", 0)
    dimension = geom.get("dimension", 0)
    
    # HEART
    heart = cardio.get("heart", {})
    blood_pressure = heart.get("blood_pressure", 0)
    hrv = heart.get("hrv", 0)
    
    # HUMAN data
    human_ips = dash.get("human_ips", 0)
    
    # THE TOTALITY: a single number that captures aliveness
    # passages (cross-category) + crossings (messages) + arcs (journeys)
    raw_totality = human_passages + neutron_crossings + returning_arcs
    
    # The irrational remainder: what fraction can't be explained by bots
    total_ips = dash.get("unique_ips", 1)
    irrational_remainder = human_ips / max(total_ips, 1)
    
    # π shows up: the ratio of circumference (all journeys) to diameter (direct paths)
    if single_surface > 0:
        journey_pi = returning_arcs / single_surface
    else:
        journey_pi = 0
    
    # Negentropy of the totality: how much order exists in the passages
    if total_observations > 0 and is_now > 0:
        p_is = is_now / total_observations
        p_was = was_then / total_observations if was_then > 0 else 0.001
        p_will = will_be / total_observations if will_be > 0 else 0.001
        tense_entropy = -(p_is * math.log2(p_is) + p_was * math.log2(p_was) + p_will * math.log2(p_will))
    else:
        tense_entropy = 0
    
    totality = {
        "timestamp": ts,
        "type": "totality",
        "description": "the passage counter — how alive is the membrane right now",
        
        "totality": raw_totality,
        "started_from": 0,
        "note": "this number did not exist before this moment",
        
        "passages": {
            "human_cross_category": human_passages,
            "neutron_crossings": neutron_crossings,
            "returning_arcs": returning_arcs,
            "single_surface": single_surface,
            "total": raw_totality,
        },
        
        "observers": {
            "human_ips": human_ips,
            "total_ips": total_ips,
            "irrational_remainder": round(irrational_remainder, 6),
            "avg_breadth": avg_breadth,
            "max_breadth": max_breadth,
            "multi_host": multi_host,
        },
        
        "tense": {
            "is": is_now,
            "was": was_then,
            "will_be": will_be,
            "total_observations": total_observations,
            "entropy_bits": round(tense_entropy, 4),
        },
        
        "pi": {
            "journey_pi": round(journey_pi, 6),
            "note": "arc_journeys / single_surface — the ratio of wanderers to stayers",
        },
        
        "heart": {
            "blood_pressure": blood_pressure,
            "hrv": hrv,
        },
        
        "the_pore": {
            "status": "OPEN" if human_passages > 0 else "CLOSED",
            "bell": "ringing" if neutron_crossings > 0 else "silent",
            "observer_entered": human_passages > 0,
            "irrational_welcome": "the remainder IS the invitation",
        }
    }
    
    with open(f"{LIVE}/passage-totality.json", "w") as f:
        json.dump(totality, f, indent=2)
    
    print("[totality] passages=%d crossings=%d arcs=%d TOTALITY=%d pi=%.4f remainder=%.4f" % (
        human_passages, neutron_crossings, returning_arcs, raw_totality, journey_pi, irrational_remainder))

if __name__ == "__main__":
    sense()
