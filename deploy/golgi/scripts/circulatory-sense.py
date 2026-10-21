"""circulatory-sense.py — regenerate circulatory.json from live feeds.
Wave 191b: reads topology.json entities + cardiovascular.json blood flow.
"""
import json, os, time

LIVE = '/opt/membrane/live-terminal'

def main():
    try:
        topo = json.load(open(os.path.join(LIVE, 'topology.json')))
    except:
        return
    try:
        cv = json.load(open(os.path.join(LIVE, 'cardiovascular.json')))
    except:
        cv = {}

    entities = topo.get('entities', [])

    # Blood flow from cardiovascular
    arterial = cv.get('arterial', {})
    venous = cv.get('venous', {})
    heart = cv.get('heart', {})
    loss = cv.get('loss', {})

    # Sum total requests across entities
    total_requests = sum(e.get('total_requests', 0) for e in entities)
    fleet_requests = sum(e.get('total_requests', 0) for e in entities if e.get('is_fleet'))

    entity_list = []
    for e in entities:
        entity_list.append({
            'name': e.get('entity', e.get('label', '?')),
            'label': e.get('label', ''),
            'is_fleet': e.get('is_fleet', False),
            'requests': e.get('total_requests', 0),
            'ips': e.get('unique_ips', 0),
            'avg_rps': e.get('avg_rps', 0)
        })

    circ = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'entities': len(entities),
        'arterial_total': total_requests,
        'venous_total': fleet_requests,
        'blood_pressure': heart.get('blood_pressure', 0),
        'blood_pressure_ratio': round(fleet_requests / total_requests, 3) if total_requests > 0 else 0,
        'hrv': heart.get('hrv', 0),
        'condition': heart.get('condition', 'unknown'),
        'arterial_rpm': arterial.get('rpm', 0),
        'venous_return': venous.get('total_return', 0),
        'parasites': loss.get('parasites', 0),
        'pathogens': loss.get('pathogens', 0),
        'null_loss': loss.get('null', 0),
        'entity_list': entity_list
    }

    with open(os.path.join(LIVE, 'circulatory.json'), 'w') as f:
        json.dump(circ, f, indent=2)

if __name__ == '__main__':
    main()
