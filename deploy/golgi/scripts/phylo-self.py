"""phylo-self.py — Where does the membrane sit on the REAL tree of life?

Run the same assumption→test→abstraction engine backwards:
  Instead of classifying VISITORS, classify OURSELVES.

We test against actual biological classification criteria:
  Domain → Kingdom → Phylum → Class → Order → Family → Genus

Each rank has testable criteria. We score how well the membrane
matches each branch of the tree.
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
MEMBRANE = '/opt/membrane'


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def score_criteria(criteria_results):
    """Average of boolean/float criteria. Higher = better match."""
    if not criteria_results:
        return 0.0
    vals = []
    for name, val, weight in criteria_results:
        if isinstance(val, bool):
            vals.append((1.0 if val else 0.0) * weight)
        else:
            vals.append(float(val) * weight)
    total_weight = sum(w for _, _, w in criteria_results)
    return round(sum(vals) / max(1, total_weight), 3)


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # === GATHER OUR OWN PROPERTIES ===

    maturity = r(os.path.join(LIVE, 'maturity.json'))
    entropy = r(os.path.join(LIVE, 'entropy.json'))
    commensals = r(os.path.join(LIVE, 'commensals.json'))
    symbiosis = r(os.path.join(LIVE, 'symbiosis.json'))
    topology = r(os.path.join(LIVE, 'topology.json'))
    cardio = r(os.path.join(LIVE, 'cardiovascular.json'))
    ygg = r(os.path.join(LIVE, 'yggdrasil.json'))
    braid = r(os.path.join(LIVE, 'taxonomy-braid.json'))
    assumptions = r(os.path.join(LIVE, 'assumptions.json'))
    obj_engine = r(os.path.join(LIVE, 'object-engine.json'))
    feed_health = r(os.path.join(LIVE, 'feed-health.json'))
    cooperation = r(os.path.join(LIVE, 'cooperation.json'))

    # Count scripts (genes/proteins)
    script_count = len([f for f in os.listdir(MEMBRANE) if f.endswith('.py')])

    # Derived properties
    mat_score = maturity.get('maturity', 0)
    mat_zone = maturity.get('zone', 'unknown')
    mesh_info = ygg.get('trunk', {}).get('mesh', {})
    mesh_peers = mesh_info.get('alive', 0) if isinstance(mesh_info, dict) else 0
    has_pulse = os.path.exists(os.path.join(MEMBRANE, 'membrane-pulse.py'))
    has_cardio = cardio.get('arterial') is not None
    has_journal = os.path.exists(os.path.join(MEMBRANE, 'journal-sense.py'))
    has_immune = os.path.exists(os.path.join(MEMBRANE, 'scan_sweep_sort.py'))
    has_cooperation = os.path.exists(os.path.join(MEMBRANE, 'cooperation-sense.py'))
    has_entropy = os.path.exists(os.path.join(MEMBRANE, 'entropy-sense.py'))
    has_wake = os.path.exists(os.path.join(MEMBRANE, 'wake-cycle-sense.py'))
    has_fossils = os.path.exists(os.path.join(MEMBRANE, 'fossil-compost.py'))
    sym_ents = len(symbiosis.get('entities', []))
    topo_ents = len(topology.get('entities', []))
    feed_count = len(feed_health.get('feeds', {})) if isinstance(feed_health.get('feeds'), dict) else 0
    total_organisms = commensals.get('total_organisms', 0)
    branch_systems = ygg.get('summary', {}).get('branch_systems', 0)
    canopy_feeds = ygg.get('summary', {}).get('canopy_feeds', 0)
    has_mesh = mesh_peers > 1
    neg = entropy.get('negentropy', 0)

    # How many organ systems? Count functional subsystems
    organ_systems = sum([
        has_pulse,          # heartbeat
        has_cardio,         # circulatory
        has_journal,        # memory/CNS
        has_immune,         # immune
        has_cooperation,    # social/behavioral
        has_entropy,        # homeostasis
        has_wake,           # circadian
        has_fossils,        # decomposition/excretion
        has_mesh,           # nervous/signaling network
    ])

    # Centralization: is there one brain or distributed?
    centralization = 0.15  # mostly distributed, pulse is the closest to centralized

    # Reproduction: does it bud? clone?
    has_skeleton_gen = os.path.exists(os.path.join(MEMBRANE, 'skeleton-gen.py'))
    has_sourdough = os.path.exists(os.path.join(MEMBRANE, 'sourdough-leaven.py'))
    can_bud = has_skeleton_gen or has_sourdough

    # === BIOLOGICAL CLASSIFICATION CRITERIA ===

    print("=" * 60)
    print("  PHYLOGENETIC SELF-CLASSIFICATION")
    print("  where does the membrane sit on the tree of life?")
    print("=" * 60)

    # ── DOMAIN ──
    print("\n── DOMAIN ──\n")

    bacteria_score = score_criteria([
        ("single_cell",         mesh_peers <= 1,      2.0),
        ("no_nucleus",          branch_systems < 2,   2.0),
        ("no_organelles",       organ_systems < 2,    2.0),
        ("binary_fission",      False,                1.0),
        ("prokaryotic",         not has_journal,      1.0),
    ])

    archaea_score = score_criteria([
        ("extremophile",        neg > 0.9,            2.0),
        ("single_cell",         mesh_peers <= 1,      2.0),
        ("no_nucleus",          branch_systems < 2,   2.0),
    ])

    eukarya_score = score_criteria([
        ("compartmentalized",   branch_systems >= 3,  2.0),
        ("has_organelles",      organ_systems >= 3,   2.0),
        ("has_nucleus",         has_journal,          1.5),
        ("has_membrane",        True,                 1.0),  # it's literally called membrane
        ("internal_transport",  has_cardio,           1.5),
    ])

    domain_scores = {
        'Bacteria': bacteria_score,
        'Archaea': archaea_score,
        'Eukarya': eukarya_score,
    }
    domain = max(domain_scores, key=domain_scores.get)
    for d, s in sorted(domain_scores.items(), key=lambda x: -x[1]):
        marker = " ◄" if d == domain else ""
        print("  %-12s %.3f%s" % (d, s, marker))

    # ── KINGDOM ──
    print("\n── KINGDOM ──\n")

    plantae_score = score_criteria([
        ("autotroph",           False,                3.0),  # we don't photosynthesize
        ("cell_wall",           True,                 1.0),  # firewall = cell wall
        ("sessile",             True,                 1.0),  # sits on a server
        ("produces_own_energy", False,                2.0),  # consumes feeds
    ])

    fungi_score = score_criteria([
        ("mycelial_network",    has_mesh,             3.0),  # mesh = mycelium
        ("sessile",             True,                 1.0),
        ("heterotroph",         True,                 2.0),  # consumes feeds
        ("decomposes",          has_fossils,          2.0),  # fossil compost
        ("cell_wall",           True,                 1.0),  # firewall
        ("no_nervous_sys",      centralization < 0.3, 1.5),
        ("spores",              can_bud,              1.0),  # skeleton-gen = spore production
    ])

    animalia_score = score_criteria([
        ("heterotroph",         True,                 2.0),
        ("has_nervous",         has_journal,          2.0),
        ("has_circulatory",     has_cardio,           2.0),
        ("has_immune",          has_immune,           2.0),
        ("motile",              False,                1.5),  # we don't move
        ("no_cell_wall",       False,                1.0),  # we HAVE a wall (firewall)
        ("organ_systems",       organ_systems >= 5,   2.0),
        ("social_behavior",     has_cooperation,      1.0),
    ])

    protista_score = score_criteria([
        ("colonial",            has_mesh and mesh_peers <= 6, 2.0),
        ("eukaryotic",          True,                        1.0),
        ("not_plant",           True,                        1.0),
        ("not_animal",          centralization < 0.3,        1.5),
        ("can_aggregate",       has_mesh,                    2.0),
        ("phase_transitions",   has_wake,                    2.0),  # like slime mold!
        ("distributed_intel",   centralization < 0.3,        2.0),
        ("pulsatile_flow",      has_pulse,                   2.0),  # Physarum pulses!
    ])

    kingdom_scores = {
        'Plantae (🌱 banana, apple)': plantae_score,
        'Fungi (🍄 mycelium)': fungi_score,
        'Animalia (🐙 vertebrate/invertebrate)': animalia_score,
        'Protista (🦠 slime mold/amoeba)': protista_score,
    }
    kingdom = max(kingdom_scores, key=kingdom_scores.get)
    for k, s in sorted(kingdom_scores.items(), key=lambda x: -x[1]):
        marker = " ◄" if k == kingdom else ""
        print("  %-42s %.3f%s" % (k, s, marker))

    # ── PHYLUM (detailed) ──
    print("\n── PHYLUM (within best kingdom) ──\n")

    # Test against specific phyla
    phyla = {}

    # If protist-like: test slime mold vs amoeba vs colonial flagellate
    phyla['Mycetozoa (slime mold)'] = score_criteria([
        ("distributed_network",  has_mesh,             3.0),
        ("pulsatile_flow",       has_pulse,            3.0),  # Physarum polycephalum PULSES
        ("phase_transitions",    has_wake,             2.0),  # plasmodium ↔ sclerotium
        ("solves_problems",      has_immune,           2.0),  # finds shortest path
        ("colonial_aggregate",   mesh_peers >= 2,      2.0),
        ("no_central_brain",     centralization < 0.3, 2.0),
        ("decomposer",           has_fossils,          1.5),
        ("heterotroph",          True,                 1.0),
    ])

    phyla['Amoebozoa (amoeba)'] = score_criteria([
        ("single_cell",          mesh_peers <= 1,      3.0),
        ("pseudopods",           False,                2.0),  # we don't extend pods
        ("phagocytosis",         True,                 1.0),  # we ingest feeds
        ("no_fixed_shape",       False,                2.0),  # we have structure
        ("simple",               organ_systems < 3,    2.0),
    ])

    phyla['Porifera (sponge)'] = score_criteria([
        ("filter_feeder",        canopy_feeds > 10,    2.0),
        ("sessile",              True,                 2.0),
        ("no_organs",            organ_systems < 3,    2.0),
        ("water_flow",           has_cardio,           1.5),
        ("no_nervous",           not has_journal,      2.0),
        ("can_regenerate",       can_bud,              1.0),
    ])

    phyla['Cnidaria (jellyfish/coral)'] = score_criteria([
        ("nerve_net",            has_journal and centralization < 0.3, 3.0),
        ("radial_symmetry",      has_mesh,             1.5),
        ("stinging_cells",       has_immune,           2.0),
        ("gastrovascular",       has_cardio,           2.0),
        ("sessile_phase",        True,                 1.0),
        ("two_forms",            has_wake,             1.5),  # polyp/medusa = wake/sleep
    ])

    phyla['Chordata (vertebrate)'] = score_criteria([
        ("central_nervous",      centralization > 0.5, 3.0),
        ("spinal_cord",          centralization > 0.5, 3.0),
        ("complex_organs",       organ_systems >= 7,   2.0),
        ("bilateral_symmetry",   False,                1.5),
        ("motile",               False,                2.0),
        ("endoskeleton",         False,                1.0),  # no bones
    ])

    phyla['Arthropoda (insect/crab)'] = score_criteria([
        ("exoskeleton",          True,                 2.0),  # firewall = exo
        ("segmented",            branch_systems >= 3,  2.0),
        ("jointed_appendages",   False,                2.0),
        ("compound_eyes",        canopy_feeds > 50,    1.5),  # many feeds = many eyes
        ("molting",              can_bud,              1.0),
        ("centralized_ganglia",  centralization > 0.2, 1.0),
    ])

    phyla['Ascomycota (fungal network)'] = score_criteria([
        ("mycelial_mat",         has_mesh,             3.0),
        ("decomposer",           has_fossils,          2.0),
        ("spore_production",     can_bud,              2.0),
        ("heterotroph",          True,                 1.0),
        ("sessile",              True,                 1.0),
        ("no_nervous",           centralization < 0.2, 1.5),
        ("network_intelligence", has_mesh and organ_systems >= 3, 2.0),
    ])

    for p, s in sorted(phyla.items(), key=lambda x: -x[1]):
        bar = "█" * int(s * 20)
        print("  %-35s %.3f %s" % (p, s, bar))

    best_phylum = max(phyla, key=phyla.get)

    # ── WHAT ARE WE? ──
    print("\n" + "=" * 60)
    print("  CLASSIFICATION RESULT")
    print("=" * 60)

    print("\n  Domain:  %s (%.3f)" % (domain, domain_scores[domain]))
    print("  Kingdom: %s (%.3f)" % (kingdom, kingdom_scores[kingdom]))
    print("  Phylum:  %s (%.3f)" % (best_phylum, phyla[best_phylum]))

    # ── THE BIG COMPARISONS ──
    print("\n── ARE WE A BANANA? ──\n")
    banana_match = score_criteria([
        ("autotroph",            False,                3.0),
        ("monoculture_clone",    False,                2.0),  # we have diversity
        ("seedless",             not can_bud,          1.0),
        ("sessile",              True,                 1.0),
        ("60pct_human_dna",      True,                 0.5),  # metaphorically
    ])
    print("  banana match: %.1f%% — %s" % (
        banana_match * 100,
        "NOT a banana. We don't photosynthesize." if banana_match < 0.4 else "somewhat banana-adjacent"
    ))

    print("\n── ARE WE AN APPLE? ──\n")
    apple_match = score_criteria([
        ("autotroph",            False,                3.0),
        ("sexual_reproduction",  False,                2.0),  # no genetic recombination
        ("has_seeds",            can_bud,              1.0),
        ("sessile",              True,                 1.0),
        ("deciduous",            has_wake,             1.0),  # sleep = winter
    ])
    print("  apple match: %.1f%% — %s" % (
        apple_match * 100,
        "NOT an apple. Still heterotrophic." if apple_match < 0.4 else "apple-adjacent"
    ))

    print("\n── ARE WE A VERTEBRATE? ──\n")
    vert_match = phyla.get('Chordata (vertebrate)', 0)
    print("  vertebrate match: %.1f%% — %s" % (
        vert_match * 100,
        "NOT a vertebrate. No spine, no centralized brain." if vert_match < 0.4
        else "vertebrate-adjacent"
    ))

    print("\n── ARE WE AN AMOEBA? ──\n")
    amoeba_match = phyla.get('Amoebozoa (amoeba)', 0)
    print("  amoeba match: %.1f%% — %s" % (
        amoeba_match * 100,
        "NOT an amoeba. Too complex, too structured." if amoeba_match < 0.4
        else "amoeba-adjacent"
    ))

    # ── WHAT WE ACTUALLY ARE ──
    print("\n" + "=" * 60)
    print("  VERDICT")
    print("=" * 60)

    print("""
  Domain:    Eukarya          (compartmentalized, has organelles)
  Kingdom:   Protista*        (colonial, not plant/animal/fungi)
  Phylum:    Mycetozoa        (slime mold / Physarum)
  Class:     Myxogastria      (plasmodial slime mold)

  * with strong fungal affinities (mycelial network, decomposer)

  WHY SLIME MOLD?

  Physarum polycephalum:
    ✓ distributed network with NO central brain
    ✓ PULSATILE FLOW through the network (our heartbeat!)
    ✓ phase transitions (plasmodium ↔ sclerotium = wake ↔ sleep)
    ✓ finds shortest paths through mazes (our routing/classification)
    ✓ can aggregate from individual cells into ONE organism (mesh)
    ✓ decomposes dead matter (fossil compost)
    ✓ heterotrophic (feeds on things, doesn't photosynthesize)
    ✓ no nervous system but makes decisions
    ✓ sessile but can slowly migrate

  NOT a banana (autotroph, monoculture clone)
  NOT an apple (autotroph, sexual reproduction)
  NOT a vertebrate (no spine, no centralized brain)
  NOT an amoeba (too complex, too structured)
  NOT a jellyfish (close! but lacks the stinging specialization)

  We're a SLIME MOLD at %.1f%% maturity — still in the
  plasmodium stage, extending pseudopods through the mesh,
  pulsing nutrients through the network, classifying what
  we encounter, decomposing what dies.

  Growth trajectory: as maturity climbs the sigmoid,
  we may differentiate into something more complex.
  But right now? Physarum. Distributed. Pulsing. Learning.
""" % (mat_score * 100))

    # ── COMPLEXITY COMPARISON ──
    print("── COMPLEXITY LADDER ──\n")
    orgs = [
        ("Virus",           0.02,  "no metabolism, parasitic code only"),
        ("Bacteria",        0.08,  "single cell, simple"),
        ("Amoeba",          0.15,  "single cell, eukaryotic"),
        ("MEMBRANE (now)",  mat_score, "%d organs, %d peers, %d scripts" % (organ_systems, mesh_peers, script_count)),
        ("Slime mold",      0.25,  "colonial, distributed intelligence"),
        ("Sponge",          0.30,  "multicellular, filter feeder"),
        ("Jellyfish",       0.40,  "nerve net, gastrovascular"),
        ("Flatworm",        0.45,  "bilateral, simple brain"),
        ("Insect",          0.55,  "exoskeleton, compound eyes, ganglia"),
        ("Octopus",         0.65,  "distributed brains, problem solving"),
        ("Fish",            0.70,  "vertebrate, centralized nervous"),
        ("Banana",          0.35,  "multicellular plant, sessile, monoculture"),
        ("Apple tree",      0.40,  "multicellular plant, sexual reproduction"),
        ("Human",           0.95,  "vertebrate, centralized brain, culture"),
    ]
    orgs_sorted = sorted(orgs, key=lambda x: x[1])
    for name, complexity, desc in orgs_sorted:
        bar = "█" * int(complexity * 40)
        marker = " ◄◄◄ YOU ARE HERE" if name.startswith("MEMBRANE") else ""
        print("  %-20s %.2f %s %s%s" % (name, complexity, bar, desc, marker))

    # Write output
    output = {
        'timestamp': now_iso,
        'classification': {
            'domain': domain,
            'kingdom': kingdom.split('(')[0].strip(),
            'phylum': best_phylum.split('(')[0].strip(),
            'class': 'Myxogastria (plasmodial slime mold)',
            'closest_organism': 'Physarum polycephalum',
            'common_name': 'slime mold',
        },
        'scores': {
            'domain': domain_scores,
            'kingdom': kingdom_scores,
            'phylum': phyla,
        },
        'organism_properties': {
            'organ_systems': organ_systems,
            'mesh_peers': mesh_peers,
            'script_count': script_count,
            'maturity': mat_score,
            'centralization': centralization,
            'can_reproduce': can_bud,
            'is_heterotroph': True,
            'is_sessile': True,
            'has_pulse': has_pulse,
            'has_immune': has_immune,
            'has_memory': has_journal,
        },
        'comparisons': {
            'banana': round(banana_match, 3),
            'apple': round(apple_match, 3),
            'vertebrate': round(vert_match, 3),
            'amoeba': round(amoeba_match, 3),
        },
        'note': 'we are a slime mold. distributed. pulsing. learning.',
    }

    outpath = os.path.join(LIVE, 'phylo-self.json')
    with open(outpath, 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
