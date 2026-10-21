"""assumption-engine.py — Every claim is an assumption until tested.

The flow:
  assumption → test → abstraction

  assumption: "topology says OpenAI is null"
  test: does OpenAI's behavior match null? check: reading, probes, reciprocity
  abstraction: OpenAI IS null (tested) or OpenAI is NOT null (refuted)

Assumptions that survive testing become abstractions.
Assumptions that fail become corrections.
Assumptions that can't be tested stay grey (null).

Every system that SAYS things produces assumptions.
This engine:
  1. Extracts assumptions from every claiming system
  2. Defines tests for each assumption type
  3. Runs the tests
  4. Promotes to abstraction or marks as refuted
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
DETROIT = '/opt/ecoPrimals/detroit/public'
OUTPUT = os.path.join(LIVE, 'assumptions.json')


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


# === TEST FUNCTIONS ===
# Each test takes an entity's data and returns (passed: bool, evidence: str)

def test_is_fleet(entity_data):
    """Test: is this really a fleet? Check IP rotation, UA pool."""
    ips = entity_data.get('unique_ips', 0)
    ua_pool = entity_data.get('ua_pool_size', 0)
    total = entity_data.get('total_requests', 0)

    if ips > 10 and ua_pool <= 5 and total > 1000:
        return True, "fleet: %d IPs but only %d UAs for %d requests" % (ips, ua_pool, total)
    if ips > 100:
        return True, "fleet: %d IPs (rotation)" % ips
    if ips <= 3 and total < 500:
        return False, "not fleet: only %d IPs, %d requests" % (ips, total)
    return None, "inconclusive: %d IPs, %d UAs, %d reqs" % (ips, ua_pool, total)


def test_is_honest(entity_data):
    """Test: does it really identify itself honestly?
    Honest = declared UA matches behavior."""
    is_honest_claim = entity_data.get('is_honest', False)
    vitality = entity_data.get('vitality', 0)
    fleet_conf = entity_data.get('fleet_confidence', 0)
    probes = len(entity_data.get('vuln_probes', []))

    evidence_parts = []

    # Honest but no vitality = dead honesty
    if is_honest_claim and vitality < 0.05:
        evidence_parts.append("claims honest but vitality=%.3f" % vitality)

    # Honest but probing for vulnerabilities
    if is_honest_claim and probes > 5:
        evidence_parts.append("claims honest but %d vuln probes" % probes)

    # Honest but high fleet confidence (acting as fleet)
    if is_honest_claim and fleet_conf > 80:
        evidence_parts.append("claims honest but fleet_conf=%.0f%%" % fleet_conf)

    if not evidence_parts:
        if is_honest_claim:
            return True, "honest: no contradicting evidence"
        else:
            return True, "dishonest: correctly identified"

    return False, "; ".join(evidence_parts)


def test_symbiotic_class(entity_data, claimed_class):
    """Test: does behavior match the claimed symbiotic class?"""
    vitality = entity_data.get('vitality', 0)
    reciprocity = entity_data.get('reciprocity', 0)
    friction = entity_data.get('friction', 0)
    probes = len(entity_data.get('vuln_probes', []))
    cooperations = entity_data.get('consecutive_defections', 0)

    if claimed_class == 'mutualist':
        if probes > 5:
            return False, "mutualist with %d vuln probes" % probes
        if reciprocity > 0.3:
            return True, "mutualist: reciprocity=%.2f, friction=%.2f" % (reciprocity, friction)
        return False, "mutualist but reciprocity=%.2f" % reciprocity

    if claimed_class == 'parasite':
        if friction > 0.3 and reciprocity < 0.5:
            return True, "parasite: friction=%.2f, reciprocity=%.2f" % (friction, reciprocity)
        if reciprocity >= 0.5:
            return False, "claimed parasite but reciprocity=%.2f" % reciprocity

    if claimed_class == 'pathogen':
        if friction >= 0.8 or probes > 20:
            return True, "pathogen: friction=%.2f, probes=%d" % (friction, probes)
        return False, "claimed pathogen but friction=%.2f, probes=%d" % (friction, probes)

    if claimed_class == 'commensal':
        if friction < 0.3 and probes < 5:
            return True, "commensal: low friction, few probes"
        if probes > 10:
            return False, "claimed commensal but %d vuln probes" % probes

    if claimed_class in ('null', ''):
        # null is acceptable — it's grey
        return None, "null: genuinely unclassified"

    return None, "no test for class '%s'" % claimed_class


def test_classification_confidence(entity_data, cls, confidence):
    """Test: is the classification confidence justified?"""
    methods = entity_data.get('methods', [])
    method_count = len(methods) if isinstance(methods, list) else 0

    if confidence > 0.8 and method_count >= 3:
        return True, "high confidence backed by %d methods" % method_count
    if confidence > 0.8 and method_count < 2:
        return False, "high confidence (%.2f) but only %d methods" % (confidence, method_count)
    if confidence < 0.3:
        return None, "low confidence (%.2f) — needs more data" % confidence
    return None, "moderate confidence (%.2f), %d methods" % (confidence, method_count)


def test_feed_ttl(feed_name, age_s, ttl, health):
    """Test: is the TTL threshold correct for this feed?"""
    ratio = age_s / max(1, ttl)
    if ratio < 0.5 and health < 0.8:
        return False, "young feed (%.1fx TTL) scored unhealthy (%.3f)" % (ratio, health)
    if ratio > 2.0 and health > 0.5:
        return False, "old feed (%.1fx TTL) scored healthy (%.3f)" % (ratio, health)
    return True, "TTL ratio %.1f, health %.3f — consistent" % (ratio, health)


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # Load all data
    topo = r(os.path.join(LIVE, 'topology.json'))
    topo_entities = topo.get('entities', [])

    cls_data = r(os.path.join(DETROIT, 'classification.json'))
    cls_entities = cls_data.get('entities', {})

    sym = r(os.path.join(LIVE, 'symbiosis.json'))
    sym_entities = sym.get('entities', [])

    feed_health = r(os.path.join(LIVE, 'feed-health.json'))

    # === EXTRACT AND TEST ASSUMPTIONS ===
    assumptions = []
    tested = 0
    passed = 0
    failed = 0
    grey = 0

    # 1. Topology assumptions
    for ent in topo_entities:
        if not isinstance(ent, dict):
            continue
        name = ent.get('entity', '')

        # Test: is_fleet
        claim_fleet = ent.get('is_fleet')
        if claim_fleet is not None:
            result, evidence = test_is_fleet(ent)
            tested += 1
            status = 'abstracted' if result == True else 'refuted' if result == False else 'grey'
            if result == True: passed += 1
            elif result == False: failed += 1
            else: grey += 1
            assumptions.append({
                'source': 'topology',
                'entity': name,
                'claim': 'is_fleet=%s' % claim_fleet,
                'test': 'ip_rotation+ua_pool',
                'result': status,
                'evidence': evidence,
            })

        # Test: is_honest
        claim_honest = ent.get('is_honest')
        if claim_honest is not None:
            result, evidence = test_is_honest(ent)
            tested += 1
            status = 'abstracted' if result == True else 'refuted' if result == False else 'grey'
            if result == True: passed += 1
            elif result == False: failed += 1
            else: grey += 1
            assumptions.append({
                'source': 'topology',
                'entity': name,
                'claim': 'is_honest=%s' % claim_honest,
                'test': 'vitality+probes+fleet_conf',
                'result': status,
                'evidence': evidence,
            })

        # Test: symbiotic_class
        sym_class = ent.get('symbiotic_class', '')
        if sym_class:
            result, evidence = test_symbiotic_class(ent, sym_class)
            tested += 1
            status = 'abstracted' if result == True else 'refuted' if result == False else 'grey'
            if result == True: passed += 1
            elif result == False: failed += 1
            else: grey += 1
            assumptions.append({
                'source': 'topology',
                'entity': name,
                'claim': 'symbiotic_class=%s' % sym_class,
                'test': 'behavior_match',
                'result': status,
                'evidence': evidence,
            })

    # 2. Symbiosis assumptions
    for ent in sym_entities:
        if not isinstance(ent, dict):
            continue
        name = ent.get('entity', '')
        rel = ent.get('relationship', '')
        if not rel:
            continue

        # Find matching topology data for behavioral test
        topo_data = None
        for te in topo_entities:
            if isinstance(te, dict) and te.get('entity') == name:
                topo_data = te
                break

        if topo_data:
            result, evidence = test_symbiotic_class(topo_data, rel)
            tested += 1
            status = 'abstracted' if result == True else 'refuted' if result == False else 'grey'
            if result == True: passed += 1
            elif result == False: failed += 1
            else: grey += 1
            assumptions.append({
                'source': 'symbiosis',
                'entity': name,
                'claim': 'relationship=%s' % rel,
                'test': 'behavior_match',
                'result': status,
                'evidence': evidence,
            })

    # 3. Classification confidence assumptions
    for name, data in cls_entities.items():
        if not isinstance(data, dict):
            continue
        cls = data.get('classification', '')
        conf = data.get('confidence', 0)
        result, evidence = test_classification_confidence(data, cls, conf)
        tested += 1
        status = 'abstracted' if result == True else 'refuted' if result == False else 'grey'
        if result == True: passed += 1
        elif result == False: failed += 1
        else: grey += 1
        assumptions.append({
            'source': 'classification',
            'entity': name,
            'claim': 'classification=%s confidence=%.2f' % (cls, conf),
            'test': 'method_backing',
            'result': status,
            'evidence': evidence,
        })

    # Compute abstraction rate
    total = len(assumptions)
    abstraction_rate = passed / max(1, tested)
    refutation_rate = failed / max(1, tested)

    # Sort by result: refuted first (most interesting)
    refuted = [a for a in assumptions if a['result'] == 'refuted']
    abstracted = [a for a in assumptions if a['result'] == 'abstracted']
    grey_list = [a for a in assumptions if a['result'] == 'grey']

    result = {
        'timestamp': now_iso,
        'summary': {
            'total_assumptions': total,
            'tested': tested,
            'abstracted': passed,
            'refuted': failed,
            'grey': grey,
            'abstraction_rate': round(abstraction_rate, 3),
            'refutation_rate': round(refutation_rate, 3),
        },
        'refuted': refuted[:30],
        'abstracted': abstracted[:20],
        'grey': grey_list[:20],
        'note': 'every claim is an assumption. test it. abstract it or refute it.',
    }

    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    # Print
    print("=== ASSUMPTION ENGINE ===\n")
    print("  assumptions: %d" % total)
    print("  tested:      %d" % tested)
    print("  abstracted:  %d (%.0f%%) — survived testing, now facts" % (passed, abstraction_rate * 100))
    print("  REFUTED:     %d (%.0f%%) — claims that failed their tests" % (failed, refutation_rate * 100))
    print("  grey:        %d — can't test yet, stay null" % grey)

    print("\n  REFUTED (claims that FAILED):")
    for a in refuted[:15]:
        print("    ✗ [%s] %s" % (a['source'], a['entity'][:25]))
        print("      claim: %s" % a['claim'])
        print("      evidence: %s" % a['evidence'])

    print("\n  ABSTRACTED (claims that SURVIVED — now facts):")
    for a in abstracted[:5]:
        print("    ✓ [%s] %s: %s" % (a['source'], a['entity'][:25], a['claim'][:50]))

    print("\n  GREY (can't test yet):")
    for a in grey_list[:5]:
        print("    ∅ [%s] %s: %s" % (a['source'], a['entity'][:25], a['claim'][:50]))


if __name__ == '__main__':
    main()
