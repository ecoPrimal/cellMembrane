"""maturity-sense.py — Where are we on the sigmoid?

The S-curve has three zones:
  toe      (0.00 - 0.20): foundation. building parts. slow.
  inflect  (0.20 - 0.80): rapid growth. everything connects. fast.
  shoulder (0.80 - 1.00): refinement. diminishing returns. stable.

This script reads every signal and computes where the organism
sits on its own growth curve.
"""
import json, os, time, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid, maturity_score, growth_curve

LIVE = '/opt/membrane/live-terminal'


def read_json(name, default=None):
    path = os.path.join(LIVE, name)
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default or {}


def gather_metrics():
    """Read current state and compute maturity metrics."""
    metrics = {}

    # === INFRASTRUCTURE ===
    wake = read_json('wake-cycle.json')
    wake_level = wake.get('wake_level', 0)
    # wake precision: check if wake-cycle has phase_activations (sigmoid blend)
    has_sigmoid = 'phase_activations' in wake
    has_activation = 'activation' in wake
    precision = 0
    if has_sigmoid:
        precision += 2  # sigmoid blend is the real precision
    if has_activation:
        precision += 1
    metrics['wake_sigmoid'] = (precision, 3)

    # chipmunk freshness
    chipmunk = read_json('chipmunk.json')
    ts = chipmunk.get('timestamp', '')
    if ts:
        try:
            from datetime import datetime
            clean_ts = ts.replace('Z', '').replace('+00:00', '')
            age = (datetime.utcnow() - datetime.fromisoformat(clean_ts)).total_seconds()
            freshness = min(1.0, max(0, 1.0 - age / 300))
        except:
            freshness = 0.0
    else:
        freshness = 0.0
    metrics['chipmunk_fresh'] = (freshness, 1.0)

    # === FEEDS ===
    feed_health = read_json('feed-health.json')
    summary = feed_health.get('summary', {})
    health_pct = summary.get('health_pct', 0)
    metrics['feed_health'] = (health_pct, 100.0)

    total_feeds = summary.get('total', 0)
    metrics['feed_count'] = (total_feeds, 100)  # target 100 feeds

    # === INTELLIGENCE ===
    sort = read_json('scan_sweep_sort.json')
    scan = sort.get('scan', {})
    entity_count = scan.get('entities_discovered', 0)
    method_count = scan.get('classification_methods', 0)
    avg_conf = scan.get('avg_confidence', 0)
    metrics['sort_entities'] = (entity_count, 500)
    metrics['sort_methods'] = (method_count, 50)
    metrics['sort_confidence'] = (avg_conf * 100, 85)

    # === BIOLOGY ===
    cv = read_json('cardiovascular.json')
    heart = cv.get('heart', {})
    bp = heart.get('blood_pressure', 0)
    # BP health: sigmoid — closer to 0.8-1.2 is ideal
    bp_health = max(0, bp) if bp else 0.0
    metrics['blood_pressure'] = (bp_health, 0.8)  # target: healthy BP above 0.8

    # === JOURNAL ===
    journal = read_json('journal.json')
    entries = journal.get('entries', [])
    metrics['journal_depth'] = (len(entries), 200)

    # === CRUSH (code absorption) ===
    crush = read_json('crush-manifest.json')
    ripe = crush.get('ripe', [])
    crushed = sum(1 for r in ripe if r.get('status') == 'crushed')
    metrics['crush_progress'] = (crushed, len(ripe) if ripe else 10)

    # === COMMUNITY ===
    commensals = read_json('commensals.json')
    commensal_count = commensals.get('total_organisms', 0)
    peers = commensals.get('peers', [])
    alive_peers = sum(1 for p in peers if isinstance(p, dict) and p.get('alive', False)) if isinstance(peers, list) else 0
    metrics['mesh_peers'] = (alive_peers, 5)  # 4 nodes in fleet, target 5

    sym = read_json('symbiosis.json')
    sym_summary = sym.get('summary', {})
    mutualist_count = sym_summary.get('mutualists', 0)
    total_coop = sym_summary.get('total_cooperations', 0)
    total_defect = sym_summary.get('total_defections', 0)
    coop_ratio = total_coop / max(1, total_coop + total_defect)
    metrics['mutualist_count'] = (mutualist_count, 10)
    metrics['cooperation_ratio'] = (coop_ratio, 0.6)  # target 60% cooperation

    # === STORIES ===
    stories = read_json('visitor-stories.json')
    visitor_count = stories.get('total_visitors', 0)
    archetype_count = len(stories.get('archetypes', []))
    metrics['visitor_archetypes'] = (archetype_count, 12)
    metrics['visitor_count'] = (visitor_count, 20)

    # === OBJECTS ===
    obj_engine = read_json('object-engine.json')
    pi_tier = int(3.14159 * 10)  # 31
    gold_count = len(obj_engine.get('gold', []))
    total_objects = obj_engine.get('total_objects', 0)
    cross_ref = sum(1 for o in obj_engine.get('gold', []) if o.get('source_count', 0) > 1)
    metrics['gold_objects'] = (gold_count, pi_tier)
    metrics['cross_reference'] = (cross_ref / max(1, gold_count), 0.8)


    # === DOORBELL (first contact) ===
    doorbell = read_json('doorbell.json')
    db_summary = doorbell.get('summary', {})
    verified_count = db_summary.get('verified', 0)
    knocking_count = db_summary.get('knocking', 0)
    # Target: at least 3 verified entities (doorbell rang)
    metrics['doorbell_rings'] = (verified_count + knocking_count, 10)

    # === ASSUMPTIONS (tested knowledge) ===
    assumptions = read_json('assumptions.json')
    a_summary = assumptions.get('summary', {})
    abstraction_rate = a_summary.get('abstraction_rate', 0)
    # Target: 30% abstraction rate (tested and confirmed)
    metrics['abstraction_rate'] = (abstraction_rate, 0.3)

    # === COOPERATION ===
    coop = read_json('cooperation.json')
    coop_summary = coop.get('summary', {})
    membrane_coop = coop_summary.get('membrane_cooperation', 0)
    metrics['cooperation'] = (membrane_coop, 0.8)

    # === LEAVEN (crush readiness) ===
    leaven = read_json('sourdough-leaven.json')
    leaven_summary = leaven.get('summary', {})
    leavened_count = leaven_summary.get('leavened', 0)
    metrics['scripts_leavened'] = (leavened_count, 10)

    # === FOSSILS ===
    compost = read_json('fossil-compost.json')
    compost_summary = compost.get('summary', {})
    compost_count = compost_summary.get('compost', 0)
    ghost_count = compost_summary.get('ghosts', 0)
    total_fossils = compost_summary.get('total_fossils', 0)
    if total_fossils > 0:
        compost_ratio = compost_count / total_fossils
    else:
        compost_ratio = 0
    metrics['fossil_composted'] = (compost_ratio, 0.5)  # target: half of fossils composted

    return metrics


def zone(maturity):
    """Classify maturity into sigmoid zone."""
    if maturity < 0.20:
        return 'toe'
    elif maturity < 0.80:
        return 'inflection'
    else:
        return 'shoulder'


def main():
    metrics = gather_metrics()
    overall, details = maturity_score(metrics)
    z = zone(overall)

    # Identify what pushes us up the curve (highest leverage)
    leverage = {}
    for name, score in details.items():
        current, target = metrics[name]
        gap = 1.0 - score
        leverage[name] = gap

    top_leverage = sorted(leverage.items(), key=lambda x: -x[1])[:5]
    at_shoulder = sorted(leverage.items(), key=lambda x: x[1])[:5]

    result = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'maturity': overall,
        'zone': z,
        'zone_description': {
            'toe': 'foundation phase — building parts, connections forming',
            'inflection': 'rapid growth — everything connects, momentum builds',
            'shoulder': 'refinement — stable, diminishing returns, maintain',
        }[z],
        'metrics': {},
        'top_leverage': [],
        'at_shoulder': [],
    }

    for name, score in sorted(details.items(), key=lambda x: x[1]):
        current, target = metrics[name]
        result['metrics'][name] = {
            'score': score,
            'current': current,
            'target': target,
            'ratio': round(current / max(1, target), 3),
        }

    for name, gap in top_leverage:
        current, target = metrics[name]
        result['top_leverage'].append({
            'metric': name,
            'gap': round(gap, 3),
            'action': 'focus here to climb the sigmoid',
            'current': current,
            'target': target,
        })

    for name, gap in at_shoulder:
        result['at_shoulder'].append({
            'metric': name,
            'score': details[name],
            'status': 'maintain',
        })

    out = os.path.join(LIVE, 'maturity.json')
    with open(out, 'w') as f:
        json.dump(result, f, indent=2)

    print("maturity: %.3f  zone: %s" % (overall, z))
    print("  leverage (focus here):")
    for item in result['top_leverage'][:3]:
        print("    %-20s gap=%.3f  (%s/%s)" % (
            item['metric'], item['gap'], item['current'], item['target']))
    print("  at shoulder (maintain):")
    for item in result['at_shoulder'][:3]:
        print("    %-20s score=%.3f" % (item['metric'], item['score']))


if __name__ == '__main__':
    main()
