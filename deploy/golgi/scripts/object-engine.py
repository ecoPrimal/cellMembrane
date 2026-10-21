"""object-engine.py — Unified object system across all sources.

Pi x 10 = 31 objects max in gold tier.
Every object lives in one place, cross-referenced everywhere.

SOURCES:
  - detroit classification (entities, methods, confidence)
  - detroit biosphere (nodes, edges, types)
  - detroit landmarks (geographic/legal nodes)
  - detroit desk (front_and_center priorities)
  - detroit identity (@graph)
  - detroit spotlight (evidence, legal)
  - symbiosis (fleet organisms)
  - topology (membrane structure)
  - campfire (stories, culture)
  - page-stories (touch patterns)

TIERS:
  Gold:   pi x 10 = 31 (highest scored, most cross-referenced)
  Silver: next 31
  Bronze: next 31
  Iron:   remainder

SORT: confidence x methods x source_count x freshness
      → unified into one score → sigmoid normalized
"""
import json, os, time, math, sys

sys.path.insert(0, '/opt/membrane')
from sigmoid import sigmoid

LIVE = '/opt/membrane/live-terminal'
DETROIT = '/opt/ecoPrimals/detroit/public'
OUTPUT = os.path.join(LIVE, 'object-engine.json')

PI = math.pi
MAX_PER_TIER = int(PI * 10)  # 31


def r(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}


def collect_objects():
    """Pull objects from every source and merge."""
    objects = {}

    # 1. DETROIT CLASSIFICATION — primary source
    cls = r(os.path.join(DETROIT, 'classification.json'))
    for name, data in cls.get('entities', {}).items():
        if not isinstance(data, dict):
            continue
        methods = data.get('methods', [])
        objects[name] = {
            'name': name,
            'sources': ['detroit-classification'],
            'classification': data.get('classification', 'unknown'),
            'confidence': float(data.get('confidence', 0)),
            'method_count': len(methods) if isinstance(methods, list) else 0,
            'methods': methods if isinstance(methods, list) else [],
            'style': {},
            'geo': {},
            'legal': {},
            'stories': [],
        }

    # 2. BIOSPHERE — type, role in ecosystem
    bio = r(os.path.join(DETROIT, 'biosphere.json'))
    for node in bio.get('nodes', []):
        if not isinstance(node, dict):
            continue
        name = node.get('id', node.get('name', ''))
        if not name:
            continue
        if name in objects:
            objects[name]['sources'].append('biosphere')
            objects[name]['bio_type'] = node.get('type', '')
        else:
            objects[name] = {
                'name': name,
                'sources': ['biosphere'],
                'classification': 'biosphere',
                'confidence': 0,
                'method_count': 0,
                'methods': [],
                'bio_type': node.get('type', ''),
                'style': {},
                'geo': {},
                'legal': {},
                'stories': [],
            }

    # 3. LANDMARKS — geographic/legal significance
    lm = r(os.path.join(DETROIT, 'landmarks.json'))
    for node in lm.get('nodes', []):
        if not isinstance(node, dict):
            continue
        name = node.get('id', node.get('name', ''))
        if not name:
            continue
        if name in objects:
            objects[name]['sources'].append('landmarks')
            objects[name]['geo'] = {
                'type': node.get('type', ''),
                'lat': node.get('lat'),
                'lng': node.get('lng'),
            }
        else:
            objects[name] = {
                'name': name,
                'sources': ['landmarks'],
                'classification': 'landmark',
                'confidence': 0,
                'method_count': 0,
                'methods': [],
                'style': {},
                'geo': {'type': node.get('type', '')},
                'legal': {},
                'stories': [],
            }

    # 4. DESK — priority objects from front_and_center
    desk = r(os.path.join(DETROIT, 'desk.json'))
    the_pattern = desk.get('the_pattern', {})
    if the_pattern:
        subject = the_pattern.get('subject', '')
        if subject:
            name_key = subject.lower().replace(' ', '_')
            if name_key in objects:
                objects[name_key]['sources'].append('desk-pattern')
                objects[name_key]['legal'] = {
                    'convictions': the_pattern.get('convictions'),
                    'credential': the_pattern.get('teaching_credential'),
                    'revenue_extraction': the_pattern.get('revenue_extraction'),
                }
            else:
                # Map to existing object by partial match
                for obj_name in list(objects.keys()):
                    if 'banks' in obj_name and 'strategy' not in obj_name and 'living' not in obj_name:
                        objects[obj_name]['sources'].append('desk-pattern')
                        objects[obj_name]['legal'] = {
                            'convictions': the_pattern.get('convictions'),
                            'credential': the_pattern.get('teaching_credential'),
                        }
                        break

    # 5. SPOTLIGHT — evidence, legal filings
    spot = r(os.path.join(DETROIT, 'spotlight.json'))
    smoking = spot.get('smoking_guns', {})
    if isinstance(smoking, dict):
        for k, v in smoking.items():
            for obj_name in objects:
                if k.lower().replace('_', '') in obj_name.replace('_', ''):
                    if 'spotlight' not in objects[obj_name]['sources']:
                        objects[obj_name]['sources'].append('spotlight')

    # 6. IDENTITY — @graph
    ident = r(os.path.join(DETROIT, 'identity.json'))
    for node in ident.get('@graph', []):
        if not isinstance(node, dict):
            continue
        name = node.get('@id', node.get('name', ''))
        if name and name in objects:
            objects[name]['sources'].append('identity')

    # 7. SYMBIOSIS — fleet organisms
    sym = r(os.path.join(LIVE, 'symbiosis.json'))
    for ent in sym.get('entities', []):
        if not isinstance(ent, dict):
            continue
        name = ent.get('id', ent.get('name', ''))
        if not name:
            continue
        if name in objects:
            objects[name]['sources'].append('symbiosis')
        else:
            objects[name] = {
                'name': name,
                'sources': ['symbiosis'],
                'classification': ent.get('classification', ''),
                'confidence': 0,
                'method_count': 0,
                'methods': [],
                'style': {},
                'geo': {},
                'legal': {},
                'stories': [],
            }

    # 8. SITE PAGES — cross-reference entities to actual pages
    pages_dir = '/opt/ecoPrimals/detroit/worktree/site/content'
    if os.path.isdir(pages_dir):
        page_list = []
        for root, dirs, files in os.walk(pages_dir):
            for f in files:
                if not f.endswith('.md'):
                    continue
                path = os.path.join(root, f)
                rel = os.path.relpath(path, pages_dir)
                section = rel.split('/')[0] if '/' in rel else '_root'
                slug = rel.replace('.md', '').replace('/', '_').replace('-', '_').lower()
                sz = os.path.getsize(path)
                page_list.append({'path': rel, 'section': section, 'slug': slug, 'size': sz})

        for obj_name in list(objects.keys()):
            name_parts = [p for p in obj_name.lower().split('_') if len(p) > 3]
            if not name_parts:
                continue
            matched_pages = []
            for page in page_list:
                if any(part in page['slug'] for part in name_parts):
                    matched_pages.append(page['path'])
            if matched_pages:
                objects[obj_name]['sources'].append('site-pages')
                objects[obj_name]['page_count'] = len(matched_pages)
                objects[obj_name]['pages'] = matched_pages[:5]

    # 9. PAGE STORIES — touch patterns
    stories = r(os.path.join(LIVE, 'page-stories.json'))
    surfaces = stories.get('surfaces', {})
    if isinstance(surfaces, dict):
        for surface_name, surface_data in surfaces.items():
            clean = surface_name.lower().replace('/', '').replace('-', '_')
            for obj_name in objects:
                if obj_name in clean or clean in obj_name:
                    if 'page-stories' not in objects[obj_name]['sources']:
                        objects[obj_name]['sources'].append('page-stories')

    return objects


def score_object(obj):
    """Score an object using sigmoid-weighted factors."""
    # Base: classification confidence
    conf = float(obj.get('confidence', 0))

    # Methods: more methods = more thoroughly analyzed
    methods = obj.get('method_count', 0)
    method_score = sigmoid(methods, 3, 1.5)  # peak around 3 methods

    # Source count: more sources = more cross-referenced
    source_count = len(obj.get('sources', []))
    source_score = sigmoid(source_count, 2, 2)  # peak around 2 sources

    # Has legal data: big signal
    legal_bonus = 1.0 if obj.get('legal') and any(obj['legal'].values()) else 0.0

    # Has site pages: content signal
    page_count = obj.get('page_count', 0)
    page_score = sigmoid(page_count, 5, 0.5)  # lots of pages = important object

    # Classification quality
    cls = obj.get('classification', '')
    cls_bonus = {
        'self': 0.5, 'non-self': 0.5, 'partial': 0.3,
        'other': 0.2, 'null': 0.1, 'unknown': 0.0,
        'biosphere': 0.3, 'landmark': 0.3,
    }.get(cls, 0.1)

    # Weighted sum
    raw = (conf * 2.0 + method_score * 1.5 + source_score * 1.0 +
           cls_bonus * 1.0 + legal_bonus * 2.0 + page_score * 1.5)

    # Normalize to 0-1 via sigmoid
    normalized = sigmoid(raw, 4.0, 0.8)

    return round(normalized, 4), {
        'confidence': round(conf, 3),
        'method_score': round(method_score, 3),
        'source_score': round(source_score, 3),
        'cls_bonus': round(cls_bonus, 3),
        'legal_bonus': legal_bonus,
        'page_score': round(page_score, 3),
        'raw': round(raw, 3),
    }


def classify_tier(rank):
    """Tier from rank using pi x 10."""
    if rank < MAX_PER_TIER:
        return 'gold'
    elif rank < MAX_PER_TIER * 2:
        return 'silver'
    elif rank < MAX_PER_TIER * 3:
        return 'bronze'
    else:
        return 'iron'


def main():
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    objects = collect_objects()

    # Score all objects
    scored = []
    for name, obj in objects.items():
        score, breakdown = score_object(obj)
        obj['score'] = score
        obj['score_breakdown'] = breakdown
        scored.append((name, obj, score))

    # Sort by score descending
    scored.sort(key=lambda x: -x[2])

    # Assign tiers
    tiers = {'gold': [], 'silver': [], 'bronze': [], 'iron': []}
    for rank, (name, obj, score) in enumerate(scored):
        tier = classify_tier(rank)
        obj['tier'] = tier
        obj['rank'] = rank + 1
        tiers[tier].append(obj)

    # Summary stats
    tier_stats = {}
    for tier_name, tier_objects in tiers.items():
        if tier_objects:
            scores = [o['score'] for o in tier_objects]
            classifications = {}
            source_counts = {}
            for o in tier_objects:
                c = o.get('classification', '?')
                classifications[c] = classifications.get(c, 0) + 1
                for s in o.get('sources', []):
                    source_counts[s] = source_counts.get(s, 0) + 1
            tier_stats[tier_name] = {
                'count': len(tier_objects),
                'avg_score': round(sum(scores) / len(scores), 4),
                'min_score': round(min(scores), 4),
                'max_score': round(max(scores), 4),
                'classifications': classifications,
                'source_coverage': source_counts,
            }

    # Build output
    gold_objects = []
    for obj in tiers['gold']:
        gold_objects.append({
            'rank': obj['rank'],
            'name': obj['name'],
            'score': obj['score'],
            'tier': 'gold',
            'classification': obj.get('classification', ''),
            'sources': obj.get('sources', []),
            'source_count': len(obj.get('sources', [])),
            'confidence': obj.get('confidence', 0),
            'methods': obj.get('methods', []),
            'legal': obj.get('legal', {}),
            'stories': obj.get('stories', []),
        })

    result = {
        'timestamp': now_iso,
        'pi_factor': round(PI, 6),
        'max_per_tier': MAX_PER_TIER,
        'total_objects': len(objects),
        'tier_summary': tier_stats,
        'gold': gold_objects,
        'note': 'pi x 10 = 31. the golden ratio of objects.',
    }

    with open(OUTPUT, 'w') as f:
        json.dump(result, f, indent=2)

    # Print
    print("OBJECT ENGINE — pi x 10 = %d" % MAX_PER_TIER)
    print("Total: %d objects from %d sources\n" % (len(objects), len(set(s for o in objects.values() for s in o.get('sources', [])))))

    print("=== GOLD TIER (%d) ===" % len(tiers['gold']))
    for obj in tiers['gold']:
        src = ','.join(obj.get('sources', []))[:30]
        print("  %2d. [%.3f] %-35s %-10s  %s" % (
            obj['rank'], obj['score'], obj['name'][:35],
            obj.get('classification', '?')[:10], src))

    print("\n=== TIER SUMMARY ===")
    for tier_name in ['gold', 'silver', 'bronze', 'iron']:
        ts = tier_stats.get(tier_name, {})
        print("  %-7s %3d objects  avg=%.3f  range=[%.3f, %.3f]" % (
            tier_name.upper(), ts.get('count', 0), ts.get('avg_score', 0),
            ts.get('min_score', 0), ts.get('max_score', 0)))

    # Cross-reference density
    total_sources = sum(len(o.get('sources', [])) for o in objects.values())
    avg_sources = total_sources / max(1, len(objects))
    multi_source = sum(1 for o in objects.values() if len(o.get('sources', [])) > 1)
    print("\n=== CROSS-REFERENCE ===")
    print("  avg sources/object: %.2f" % avg_sources)
    print("  multi-source objects: %d / %d (%.0f%%)" % (
        multi_source, len(objects), multi_source / max(1, len(objects)) * 100))


if __name__ == '__main__':
    main()
