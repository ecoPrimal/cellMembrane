"""yggdrasil.py — The Tree of Life.

Everything is taxonomy. Everything classifies.
Yggdrasil braids it all into one tree:

  ROOTS (what feeds from below):
    fossils → compost → entropy → negentropy
    the dead feed the living

  TRUNK (the infrastructure):
    mesh peers → pulse → braid routes
    the nervous system

  BRANCHES (the taxonomy):
    classification: self / non-self / null / partial / other
    fleet: commensal / ghost / parasite / pathogen / stealth
    symbiosis: mutualist / commensal / parasite / pathogen
    tiers: gold / silver / bronze / iron
    leaven: leavened / rising / raw
    cooperation: cooperating / defecting / forgiven

  CANOPY (the living surface):
    site sections: network / analysis / evidence / legal / ...
    feeds: fresh / stale / expired
    phases: sleep / rest / pause / wake / full

  SAP (what flows through everything):
    sigmoid — the S-curve that shapes every transition
    entropy — the measure of disorder
    maturity — position on the growth curve

The tree is the taxonomy.
The taxonomy is the tree.
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid, phase_blend, maturity_score

LIVE = '/opt/membrane/live-terminal'
OUTPUT = os.path.join(LIVE, 'yggdrasil.json')


def r(name):
    try:
        with open(os.path.join(LIVE, name)) as f:
            return json.load(f)
    except:
        return {}


def build_roots():
    """The roots — what feeds the tree from below."""
    fc = r('fossil-compost.json')
    ent = r('entropy.json')
    fc_summary = fc.get('summary', {})

    fossils = []
    for ghost in fc.get('ghosts', []):
        fossils.append({
            'name': ghost.get('name', ''),
            'age_days': ghost.get('age_days', 0),
            'status': 'ghost',
            'signal_keys': ghost.get('signal_keys', 0),
        })
    for comp in fc.get('compost', []):
        fossils.append({
            'name': comp.get('name', ''),
            'age_days': comp.get('age_days', 0),
            'status': 'compost',
            'signal_keys': comp.get('signal_keys', 0),
        })

    return {
        'fossils': {
            'total': fc_summary.get('total_fossils', 0),
            'ghosts': fc_summary.get('ghosts', 0),
            'compost': fc_summary.get('compost', 0),
            'data_points_preserved': fc_summary.get('total_data_points_preserved', 0),
        },
        'entropy': {
            'rate': ent.get('entropy_rate', 0),
            'negentropy': ent.get('negentropy', 0),
            'health': ent.get('health', 0),
            'feed_diversity': ent.get('feed_entropy', {}).get('normalized', 0),
            'fleet_shannon': ent.get('fleet_entropy', {}).get('shannon', 0),
            'phase_shannon': ent.get('phase_entropy', {}).get('shannon', 0),
        },
        'depth': len(fossils),
        'note': 'the dead feed the living. ghosts are still referenced. compost is free.',
    }


def build_trunk():
    """The trunk — infrastructure that carries everything."""
    mesh = r('commensals.json')
    peers = mesh.get('peers', [])
    alive_peers = []
    if isinstance(peers, list):
        for p in peers:
            if isinstance(p, dict):
                alive_peers.append({
                    'name': p.get('name', ''),
                    'ip': p.get('ip', ''),
                    'alive': p.get('alive', False),
                })

    braid = r('braid.json')

    # Doorbell — who has rung it?
    doorbell = r('doorbell.json')
    db_summary = doorbell.get('summary', {})

    # Assumptions — what we know vs what we guess
    assumptions = r('assumptions.json')
    a_summary = assumptions.get('summary', {})

    # Phylogenetic self-classification
    phylo = r('phylo-self.json')
    classification = phylo.get('classification', {})

    pulse = r('membrane-pulse.json')
    wake = r('wake-cycle.json')

    return {
        'mesh': {
            'peers': alive_peers,
            'alive': sum(1 for p in alive_peers if p.get('alive')),
            'total': len(alive_peers),
        },
        'pulse': {
            'beat': pulse.get('beat', 0),
            'tempo': pulse.get('tempo', ''),
            'uptime': pulse.get('uptime_hours', 0),
        },
        'wake': {
            'level': wake.get('wake_level', 0),
            'phase': wake.get('phase', ''),
            'activation': wake.get('activation', 0),
            'blend': wake.get('phase_activations', {}),
        },
        'braid_routes': len(braid) if isinstance(braid, dict) else 0,
        'doorbell': {
            'verified': db_summary.get('verified', 0),
            'knocking': db_summary.get('knocking', 0),
            'silent': db_summary.get('silent', 0),
            'policy': 'classification != identification',
        },
        'assumptions': {
            'total': a_summary.get('total_assumptions', 0),
            'abstracted': a_summary.get('abstracted', 0),
            'refuted': a_summary.get('refuted', 0),
            'grey': a_summary.get('grey', 0),
            'abstraction_rate': a_summary.get('abstraction_rate', 0),
        },
        'phylogeny': {
            'domain': classification.get('domain', ''),
            'kingdom': classification.get('kingdom', ''),
            'phylum': classification.get('phylum', ''),
            'closest': classification.get('closest_organism', ''),
            'not_a_banana': True,
        },
        'note': 'the nervous system. mesh carries signals, braid weaves them.',
    }


def build_branches():
    """The branches — taxonomy in every dimension."""
    sss = r('scan_sweep_sort.json')
    scan = sss.get('scan', {})
    obj = r('object-engine.json')
    sym = r('symbiosis.json')
    leaven = r('sourdough-leaven.json')
    coop = r('cooperation.json')

    # Classification taxonomy
    sort_classes = scan.get('sort_classes', {})
    fleet_classes = scan.get('fleet_classes', {})

    # Symbiosis taxonomy
    sym_summary = sym.get('summary', {})

    # Object tiers
    gold = obj.get('gold', [])
    tier_summary = obj.get('tier_summary', {})

    # Leaven taxonomy
    l_summary = leaven.get('summary', {})

    # Cooperation taxonomy
    c_summary = coop.get('summary', {})

    return {
        'classification': {
            'system': 'self / non-self / null / partial / other',
            'counts': sort_classes,
            'total': sum(sort_classes.values()) if sort_classes else 0,
            'methods': scan.get('classification_methods', 0),
            'confidence': scan.get('avg_confidence', 0),
        },
        'fleet': {
            'system': 'commensal / ghost / null / parasite / pathogen / stealth',
            'counts': fleet_classes,
            'total': sum(fleet_classes.values()) if fleet_classes else 0,
        },
        'symbiosis': {
            'system': 'mutualist / commensal / parasite / pathogen',
            'mutualists': sym_summary.get('mutualists', 0),
            'commensals': sym_summary.get('commensal_active', 0),
            'parasites': sym_summary.get('parasites', 0),
            'pathogens': sym_summary.get('pathogens', 0),
            'cooperations': sym_summary.get('total_cooperations', 0),
            'defections': sym_summary.get('total_defections', 0),
        },
        'tiers': {
            'system': 'gold (pi x 10) / silver / bronze / iron',
            'gold_count': len(gold),
            'gold_top_3': [g.get('name', '') for g in gold[:3]],
            'summary': tier_summary,
        },
        'leaven': {
            'system': 'leavened / rising / raw',
            'leavened': l_summary.get('leavened', 0),
            'rising': l_summary.get('rising', 0),
            'raw': l_summary.get('raw', 0),
        },
        'cooperation': {
            'system': 'cooperating / defecting / forgiven',
            'membrane_cooperation': c_summary.get('membrane_cooperation', 0),
            'membrane_health': c_summary.get('membrane_health', 0),
        },
        'note': 'every branch is a way of seeing. every taxonomy reveals different structure.',
    }


def build_canopy():
    """The canopy — the living surface that faces the world."""
    fh = r('feed-health.json')
    fh_summary = fh.get('summary', {})

    # Site sections
    pages_dir = '/opt/ecoPrimals/detroit/worktree/site/content'
    sections = {}
    total_pages = 0
    if os.path.isdir(pages_dir):
        for root, dirs, files in os.walk(pages_dir):
            for f in files:
                if f.endswith('.md'):
                    total_pages += 1
                    rel = os.path.relpath(root, pages_dir)
                    section = rel.split('/')[0] if rel != '.' else '_root'
                    sections[section] = sections.get(section, 0) + 1

    # Visitor engagement
    vs = r('visitor-stories.json')
    campfire = r('campfire.json')

    return {
        'feeds': {
            'total': fh_summary.get('total', 0),
            'fresh': fh_summary.get('fresh', 0),
            'stale': fh_summary.get('stale', 0),
            'expired': fh_summary.get('expired', 0),
            'fossil': fh_summary.get('fossil', 0),
            'health_pct': fh_summary.get('health_pct', 0),
        },
        'site': {
            'total_pages': total_pages,
            'sections': sections,
            'section_count': len(sections),
        },
        'stories': {
            'campfire': campfire.get('total_stories', 0),
            'visitors': vs.get('total_visitors', 0),
            'archetypes': len(vs.get('archetypes', [])),
        },
        'note': 'the surface the world touches. pages, feeds, stories.',
    }


def build_sap():
    """The sap — what flows through everything."""
    maturity = r('maturity.json')
    ent = r('entropy.json')

    return {
        'sigmoid': {
            'maturity': maturity.get('maturity', 0),
            'zone': maturity.get('zone', ''),
            'description': maturity.get('zone_description', ''),
        },
        'entropy': {
            'rate': ent.get('entropy_rate', 0),
            'negentropy': ent.get('negentropy', 0),
        },
        'metrics_at_shoulder': [
            item.get('metric', '') for item in maturity.get('at_shoulder', [])
        ],
        'leverage_points': [
            item.get('metric', '') for item in maturity.get('top_leverage', [])
        ],
        'note': 'sigmoid is the sap. it flows through every measurement.',
    }


def count_leaves(tree):
    """Count total taxonomy categories (leaves) across all branches."""
    count = 0
    branches = tree.get('branches', {})
    for branch_name, branch in branches.items():
        if branch_name == 'note':
            continue
        if isinstance(branch, dict):
            counts = branch.get('counts', {})
            if counts:
                count += len(counts)
            else:
                for k, v in branch.items():
                    if k in ('system', 'note', 'summary', 'gold_top_3'):
                        continue
                    if isinstance(v, (int, float)) and v > 0:
                        count += 1
    return count


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    roots = build_roots()
    trunk = build_trunk()
    branches = build_branches()
    canopy = build_canopy()
    sap = build_sap()

    tree = {
        'timestamp': now_iso,
        'name': 'Yggdrasil',
        'description': 'The tree of life. Everything is taxonomy. Everything classifies.',
        'roots': roots,
        'trunk': trunk,
        'branches': branches,
        'canopy': canopy,
        'sap': sap,
    }

    leaf_count = count_leaves(tree)

    tree['summary'] = {
        'root_depth': roots['depth'],
        'trunk_peers': trunk['mesh']['alive'],
        'branch_systems': len([k for k in branches if k != 'note']),
        'canopy_pages': canopy['site']['total_pages'],
        'canopy_feeds': canopy['feeds']['total'],
        'taxonomy_categories': leaf_count,
        'maturity': sap['sigmoid']['maturity'],
        'zone': sap['sigmoid']['zone'],
        'pi_ingress': ['banana (human)', 'connect (agent)', 'signal (discovery)'],
        'pi_egress': ['chipmunk/mcp (data)', 'detroit (evidence)', 'git (source)'],
        'doorbell_verified': trunk.get('doorbell', {}).get('verified', 0),
        'assumptions_tested': trunk.get('assumptions', {}).get('total', 0),
        'phylogeny': trunk.get('phylogeny', {}).get('closest', ''),
    }

    with open(OUTPUT, 'w') as f:
        json.dump(tree, f, indent=2)

    # Print the tree
    print()
    print("                    ⚘ YGGDRASIL ⚘")
    print("              the tree of life — taxonomy")
    print()

    # Canopy
    print("  ════════════════ CANOPY ════════════════")
    print("  %d pages across %d sections" % (
        canopy['site']['total_pages'], canopy['site']['section_count']))
    top_sections = sorted(canopy['site']['sections'].items(), key=lambda x: -x[1])[:5]
    for s, c in top_sections:
        bar = "█" * min(30, c // 8)
        print("    %-15s %3d %s" % (s, c, bar))
    print("  %d feeds (%d fresh, %d fossil)" % (
        canopy['feeds']['total'], canopy['feeds']['fresh'], canopy['feeds']['fossil']))
    print("  %d stories, %d visitors, %d archetypes" % (
        canopy['stories']['campfire'], canopy['stories']['visitors'], canopy['stories']['archetypes']))

    # Branches
    print()
    print("  ═══════════════ BRANCHES ═══════════════")
    b = branches
    print("  classification: %s" % b['classification']['counts'])
    print("    %d entities, %d methods, %.1f%% confidence" % (
        b['classification']['total'], b['classification']['methods'], b['classification']['confidence']*100))
    print("  fleet: %d entities" % b['fleet']['total'])
    for cls, cnt in sorted(b['fleet']['counts'].items(), key=lambda x: -x[1])[:4]:
        print("    %-12s %d" % (cls, cnt))
    print("  symbiosis: %d mutualists, %d parasites, %d pathogens" % (
        b['symbiosis']['mutualists'], b['symbiosis']['parasites'], b['symbiosis']['pathogens']))
    print("  tiers: %d gold (pi×10) — %s" % (
        b['tiers']['gold_count'], ', '.join(b['tiers']['gold_top_3'])))
    print("  leaven: %d🍞 %d🫧 %d🌾" % (
        b['leaven']['leavened'], b['leaven']['rising'], b['leaven']['raw']))
    print("  cooperation: %.1f%% (health %.3f)" % (
        b['cooperation']['membrane_cooperation']*100, b['cooperation']['membrane_health']))

    # Trunk
    print()
    print("  ════════════════ TRUNK ═════════════════")
    print("  mesh: %d/%d peers alive" % (trunk['mesh']['alive'], trunk['mesh']['total']))
    for p in trunk['mesh']['peers']:
        status = "●" if p.get('alive') else "○"
        print("    %s %s (%s)" % (status, p['name'], p['ip']))
    print("  wake: %.3f (%s, %.0f%% activation)" % (
        trunk['wake']['level'], trunk['wake']['phase'], trunk['wake']['activation']*100))
    blend = trunk['wake']['blend']
    if blend:
        parts = sorted(blend.items(), key=lambda x: -x[1])
        blend_str = " ".join("%s:%.0f%%" % (k, v*100) for k, v in parts if v > 0.01)
        print("    blend: %s" % blend_str)
    print("  braid: %d routes" % trunk['braid_routes'])

    # Roots
    print()
    print("  ═════════════════ ROOTS ════════════════")
    print("  fossils: %d total (%d ghosts, %d compost)" % (
        roots['fossils']['total'], roots['fossils']['ghosts'], roots['fossils']['compost']))
    print("  entropy: %.3f (negentropy %.3f, health %.3f)" % (
        roots['entropy']['rate'], roots['entropy']['negentropy'], roots['entropy']['health']))
    print("  diversity: feed %.0f%%, fleet H=%.2f, phase H=%.2f" % (
        roots['entropy']['feed_diversity']*100,
        roots['entropy']['fleet_shannon'],
        roots['entropy']['phase_shannon']))

    # Sap
    print()
    print("  ═══════════════════ SAP ════════════════")
    print("  maturity: %.1f%% — %s" % (sap['sigmoid']['maturity']*100, sap['sigmoid']['zone']))
    print("  %s" % sap['sigmoid']['description'])
    print("  leverage: %s" % ', '.join(sap['leverage_points'][:3]))
    print("  shoulder: %s" % ', '.join(sap['metrics_at_shoulder'][:3]))

    print()
    print("  %d taxonomy categories across %d branch systems" % (leaf_count, tree['summary']['branch_systems']))
    print("  %d pages, %d feeds, %d peers, %d fossils" % (
        tree['summary']['canopy_pages'], tree['summary']['canopy_feeds'],
        tree['summary']['trunk_peers'], tree['summary']['root_depth']))
    print()


if __name__ == '__main__':
    main()
