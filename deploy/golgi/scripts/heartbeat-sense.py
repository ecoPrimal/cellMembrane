"""heartbeat-sense.py — regenerate heartbeat.json from live feeds.
Wave 191b: reads dashboard + cardiovascular + passage-totality.
"""
import json, os, time

LIVE = '/opt/membrane/live-terminal'

def main():
    try:
        dash = json.load(open(os.path.join(LIVE, 'dashboard.json')))
    except:
        return
    try:
        cv = json.load(open(os.path.join(LIVE, 'cardiovascular.json')))
    except:
        cv = {}
    try:
        pt = json.load(open(os.path.join(LIVE, 'passage-totality.json')))
    except:
        pt = {}

    trajectory = dash.get('trajectory', {})
    observers = pt.get('observers', {})
    heart = cv.get('heart', pt.get('heart', {}))
    pore = pt.get('the_pore', {})
    pi_obj = pt.get('pi', {})

    heartbeat = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'human_ips': dash.get('human_ips', observers.get('human_ips', 0)),
        'total_ips': observers.get('total_ips', 0),
        'breadth': observers.get('avg_breadth', trajectory.get('avg_breadth', 0)),
        'max_breadth': observers.get('max_breadth', trajectory.get('max_breadth', 0)),
        'dwell_minutes': trajectory.get('total_dwell_minutes', 0),
        'orbits': trajectory.get('orbital_compression', {}).get('families', 0),
        'walkers': observers.get('multi_host', trajectory.get('multi_host_ips', 0)),
        'passages': pt.get('totality', 0),
        'pi': pi_obj.get('journey_pi', 0),
        'hrv': heart.get('hrv', 0),
        'blood_pressure': heart.get('blood_pressure', 0),
        'condition': heart.get('condition', 'unknown'),
        'pore': pore.get('status', 'unknown'),
        'bell': pore.get('bell', 'silent'),
        'tense': pt.get('tense', {})
    }

    with open(os.path.join(LIVE, 'heartbeat.json'), 'w') as f:
        json.dump(heartbeat, f, indent=2)

if __name__ == '__main__':
    main()
