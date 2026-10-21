"""taxonomy-braid.py — Cross-reference every branch of Yggdrasil.

The sieve. The maze. The contradiction detector.
Zero contradictions means you're not looking hard enough.

ELEMENTAL TIERS:
  Gold (Au)    — highest value, cross-referenced, confident
  Silver (Ag)  — strong, well-classified
  Bronze (Cu)  — solid, known
  Iron (Fe)    — useful, structural, workhorses
  Carbon (C)   — the mixer, bonds everything, appears everywhere
  Lead (Pb)    — toxic detritus, vuln scanners, .env probers
  Arsenic (As) — poison, active attacks, credential harvesting
  Null (∅)     — genuinely unknown. not bad, not good. grey.

CONTRADICTION DETECTION:
  topology says X is "null" but symbiosis says "pathogen"?
  → THAT'S the interesting data. The boundary. The sieve.
"""
import json, os, time, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
DETROIT = '/opt/ecoPrimals/detroit/public'
OUTPUT = os.path.join(LIVE, 'taxonomy-braid.json')


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def polarity(cls):
    """Map any classification to positive/negative/neutral/toxic."""
    if not cls:
        return 'null'
    c = str(cls).lower().replace('-', '_')
    if c in ('self', 'mutualist', 'commensal', 'human', 'cooperate', 'gold'):
        return 'positive'
    if c in ('non_self', 'parasite', 'defect'):
        return 'negative'
    if c in ('pathogen', 'stealth'):
        return 'toxic'
    if c in ('null', 'unknown', '', 'none'):
        return 'null'
    return 'neutral'


def elemental_tier(entity_data):
    """Assign elemental tier based on all available signals."""
    polarities = [v.get('polarity', 'null') for v in entity_data.values()]
    classes = [v.get('class', '') for v in entity_data.values()]
    system_count = len(entity_data)

    # Toxic detection: any system says toxic → Lead or Arsenic
    if 'toxic' in polarities:
        # Check if actively attacking (vuln probes, credential harvesting)
        for v in entity_data.values():
            if v.get('vuln_probes') or 'scanner' in str(v.get('class', '')).lower():
                return 'arsenic'
        return 'lead'

    # All negative → Lead
    if all(p == 'negative' for p in polarities) and system_count >= 2:
        return 'lead'

    # All null → genuinely null (grey)
    if all(p == 'null' for p in polarities):
        return 'null'

    # Mixed signals → Carbon (the mixer, the interesting ones)
    unique = set(polarities) - {'null'}
    if len(unique) > 1:
        return 'carbon'

    # All positive, high confidence → Gold/Silver/Bronze
    if all(p in ('positive', 'null') for p in polarities):
        if system_count >= 3:
            return 'gold'
        elif system_count >= 2:
            return 'silver'
        else:
            return 'bronze'

    # Single system, positive → Bronze
    if 'positive' in polarities:
        return 'bronze'

    # Single system, negative → Iron (still useful, just opposing)
    if 'negative' in polarities:
        return 'iron'

    return 'iron'


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # Load ALL taxonomy sources with correct field names
    # 1. Detroit classification
    cls_data = r(os.path.join(DETROIT, 'classification.json'))
    cls_entities = cls_data.get('entities', {})

    # 2. Topology (has symbiotic_class for each entity)
    topo = r(os.path.join(LIVE, 'topology.json'))
    topo_entities = topo.get('entities', [])
    topo_lookup = {}
    if isinstance(topo_entities, list):
        for ent in topo_entities:
            if isinstance(ent, dict):
                name = ent.get('entity', '')
                if name:
                    topo_lookup[name] = {
                        'symbiotic_class': ent.get('symbiotic_class', ''),
                        'fleet_confidence': ent.get('fleet_confidence', 0),
                        'vitality': ent.get('vitality', 0),
                        'is_fleet': ent.get('is_fleet', False),
                        'is_honest': ent.get('is_honest', False),
                        'vuln_probes': ent.get('vuln_probes', []),
                    }

    # 3. Symbiosis (has relationship for each entity)
    sym = r(os.path.join(LIVE, 'symbiosis.json'))
    sym_entities = sym.get('entities', [])
    sym_lookup = {}
    if isinstance(sym_entities, list):
        for ent in sym_entities:
            if isinstance(ent, dict):
                name = ent.get('entity', '')
                if name:
                    sym_lookup[name] = {
                        'relationship': ent.get('relationship', ''),
                        'cooperations': ent.get('ledger', {}).get('cooperations', 0),
                        'defections': ent.get('ledger', {}).get('defections', 0),
                    }

    # 4. Object engine (has tier for top objects)
    obj = r(os.path.join(LIVE, 'object-engine.json'))
    gold_names = set(g.get('name', '') for g in obj.get('gold', []))

    # Build unified entity map
    all_entities = {}

    # From classification
    for name, data in cls_entities.items():
        if not isinstance(data, dict):
            continue
        if name not in all_entities:
            all_entities[name] = {}
        all_entities[name]['classification'] = {
            'class': data.get('classification', 'unknown'),
            'polarity': polarity(data.get('classification', '')),
            'confidence': data.get('confidence', 0),
        }

    # From topology
    for name, data in topo_lookup.items():
        if name not in all_entities:
            all_entities[name] = {}
        # Adjust polarity: mutualist with many vuln probes is carbon, not positive
        topo_class = data['symbiotic_class']
        topo_polarity = polarity(topo_class)
        probe_count = len(data.get('vuln_probes', []))
        if topo_polarity == 'positive' and probe_count > 5:
            topo_polarity = 'neutral'  # contradiction: "good" entity probing
        if topo_class in ('commensal', '') and probe_count > 10:
            topo_polarity = 'neutral'  # commensal with attack tools
        if data.get('is_honest') and data['vitality'] < 0.01 and data['fleet_confidence'] > 90:
            topo_polarity = 'neutral'  # claims honest but dead fleet

        all_entities[name]['topology'] = {
            'class': topo_class,
            'polarity': topo_polarity,
            'fleet_confidence': data['fleet_confidence'],
            'vitality': data['vitality'],
            'is_honest': data['is_honest'],
            'vuln_probes': data.get('vuln_probes', []),
            'probe_count': probe_count,
        }

    # From symbiosis
    for name, data in sym_lookup.items():
        if name not in all_entities:
            all_entities[name] = {}
        all_entities[name]['symbiosis'] = {
            'class': data['relationship'],
            'polarity': polarity(data['relationship']),
            'cooperations': data['cooperations'],
            'defections': data['defections'],
        }

    # From object engine
    for name in gold_names:
        if name in all_entities:
            all_entities[name]['tier'] = {
                'class': 'gold',
                'polarity': 'positive',
            }

    # === THE SIEVE: find contradictions ===
    contradictions = []
    convergent = []
    boundaries = []
    null_grey = []

    elemental_counts = {}

    for name, systems in all_entities.items():
        if len(systems) < 2:
            # Single system — can't contradict
            element = elemental_tier(systems)
            elemental_counts[element] = elemental_counts.get(element, 0) + 1
            continue

        polarities = {sn: sd.get('polarity', 'null') for sn, sd in systems.items()}
        classes = {sn: sd.get('class', '?') for sn, sd in systems.items()}
        unique_p = set(polarities.values()) - {'null'}

        element = elemental_tier(systems)
        elemental_counts[element] = elemental_counts.get(element, 0) + 1

        entry = {
            'name': name,
            'systems': len(systems),
            'element': element,
            'polarities': polarities,
            'classes': classes,
        }

        # CONTRADICTION: positive and negative/toxic disagree
        has_positive = 'positive' in polarities.values()
        has_negative = 'negative' in polarities.values() or 'toxic' in polarities.values()
        has_null = 'null' in polarities.values()

        if has_positive and has_negative:
            entry['type'] = 'contradiction'
            contradictions.append(entry)
        elif has_positive and has_null and len(systems) >= 2:
            entry['type'] = 'partial_null'
            boundaries.append(entry)
        elif has_negative and has_null and len(systems) >= 2:
            entry['type'] = 'negative_null'
            boundaries.append(entry)
        elif len(unique_p) == 1 and len(systems) >= 2:
            entry['type'] = 'convergent'
            convergent.append(entry)
        elif all(p == 'null' for p in polarities.values()):
            entry['type'] = 'null_grey'
            null_grey.append(entry)
        else:
            entry['type'] = 'boundary'
            boundaries.append(entry)

    # Summary
    total = len(all_entities)
    multi = sum(1 for v in all_entities.values() if len(v) >= 2)

    result = {
        'timestamp': now_iso,
        'name': 'taxonomy-braid',
        'description': 'the sieve — contradictions ARE the data',
        'elemental_tiers': {
            'Au_gold': elemental_counts.get('gold', 0),
            'Ag_silver': elemental_counts.get('silver', 0),
            'Cu_bronze': elemental_counts.get('bronze', 0),
            'Fe_iron': elemental_counts.get('iron', 0),
            'C_carbon': elemental_counts.get('carbon', 0),
            'Pb_lead': elemental_counts.get('lead', 0),
            'As_arsenic': elemental_counts.get('arsenic', 0),
            'null': elemental_counts.get('null', 0),
        },
        'summary': {
            'total_entities': total,
            'multi_system': multi,
            'contradictions': len(contradictions),
            'convergent': len(convergent),
            'boundaries': len(boundaries),
            'null_grey': len(null_grey),
            'braid_strength': round(sigmoid(multi / max(1, total), 0.3, 8), 3),
        },
        'contradictions': sorted(contradictions, key=lambda x: -x['systems']),
        'convergent': sorted(convergent, key=lambda x: -x['systems'])[:15],
        'boundaries': sorted(boundaries, key=lambda x: -x['systems'])[:15],
        'null_grey': sorted(null_grey, key=lambda x: -x['systems'])[:10],
        'note': '0 contradictions = not looking hard enough. contradictions ARE the interesting data.',
    }

    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    # Print
    print("=== TAXONOMY BRAID — THE SIEVE ===\n")

    print("ELEMENTAL TIERS:")
    for symbol, name, count in [
        ('Au', 'gold', elemental_counts.get('gold', 0)),
        ('Ag', 'silver', elemental_counts.get('silver', 0)),
        ('Cu', 'bronze', elemental_counts.get('bronze', 0)),
        ('Fe', 'iron', elemental_counts.get('iron', 0)),
        ('C ', 'carbon (mixer)', elemental_counts.get('carbon', 0)),
        ('Pb', 'lead (detritus)', elemental_counts.get('lead', 0)),
        ('As', 'arsenic (toxic)', elemental_counts.get('arsenic', 0)),
        ('∅ ', 'null (grey)', elemental_counts.get('null', 0)),
    ]:
        bar = "█" * min(30, count)
        print("  [%s] %-18s %3d %s" % (symbol, name, count, bar))

    s = result['summary']
    print("\n  total: %d entities, %d multi-system" % (s['total_entities'], s['multi_system']))
    print("  braid strength: %.3f" % s['braid_strength'])

    print("\nCONTRADICTIONS (%d) — the sieve catches these:" % s['contradictions'])
    for c in contradictions[:10]:
        print("  ⚡ %-30s %s" % (c['name'][:30], c['classes']))

    print("\nBOUNDARIES (%d) — straddling categories:" % s['boundaries'])
    for b in boundaries[:10]:
        print("  ◐ %-30s %s → %s" % (b['name'][:30], b['classes'], b['type']))

    if null_grey:
        print("\nNULL/GREY (%d) — genuinely unknown:" % s['null_grey'])
        for n in null_grey[:5]:
            print("  ∅ %-30s %s" % (n['name'][:30], n['classes']))

    if convergent:
        print("\nCONVERGENT (%d) — all systems agree:" % s['convergent'])
        for c in convergent[:5]:
            print("  ✓ %-30s %s" % (c['name'][:30], c['classes']))


if __name__ == '__main__':
    main()
