"""build-foreman.py — Architect -> Foreman -> Builder.

Mise en place. Before you build, check the kitchen:
  1. ARCHITECT: What needs building? What changed? What's the plan?
  2. FOREMAN:   Is there enough RAM? Is the repo clean? Can remotes reach?
  3. BUILDER:   Only if 1+2 pass, hand off to the actual build script.

Time is part of the calculation:
  - How long did the last build take?
  - How much RAM is available vs needed?
  - Is the build window big enough?
  - When is the next pulse? Will we finish in time?

Returns a verdict: BUILD, DEFER, or SKIP.
"""
import json, os, time, subprocess

LIVE = '/opt/membrane/live-terminal'

def cmd(c, timeout=10):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ''

def check_site(name, repo_path, state_file, build_script):
    """Architect + Foreman check for one site."""
    verdict = {'site': name, 'checks': [], 'verdict': 'SKIP', 'reason': ''}

    # --- ARCHITECT: What needs building? ---
    if not os.path.isdir(repo_path):
        verdict['verdict'] = 'SKIP'
        verdict['reason'] = 'repo not found: %s' % repo_path
        return verdict

    # northGate: fetch github before deciding SKIP. local HEAD matching
    # last-built is not "up to date" if github has moved.
    cmd('git -C %s fetch --depth=1 github main' % repo_path, timeout=20)
    head = cmd('git -C %s rev-parse HEAD' % repo_path)
    github = cmd('git -C %s rev-parse github/main' % repo_path)
    last = ''
    try:
        last = open(state_file).read().strip()
    except:
        pass

    if github and github != 'unknown' and github != head:
        verdict['checks'].append({
            'check': 'needs_build', 'pass': True,
            'note': 'northGate github ahead %s -> %s' % (head[:8], github[:8])
        })
        # fall through to RAM/clean checks
    elif head == last:
        verdict['verdict'] = 'SKIP'
        verdict['reason'] = 'HEAD matches last-built (%s)' % head[:8]
        verdict['checks'].append({'check': 'needs_build', 'pass': False, 'note': 'up to date'})
        return verdict
    else:
        verdict['checks'].append({
            'check': 'needs_build', 'pass': True,
            'note': '%s -> %s' % (last[:8] or 'none', head[:8])
        })

    # --- FOREMAN: Check conditions ---

    # RAM check
    mem_free = cmd("awk '/MemAvailable/ {print $2}' /proc/meminfo")
    try:
        mem_mb = int(mem_free) / 1024
    except:
        mem_mb = 0
    ram_ok = mem_mb > 200
    verdict['checks'].append({
        'check': 'ram', 'pass': ram_ok,
        'note': '%.0f MB available (need 200)' % mem_mb
    })

    # Repo clean?
    dirty = cmd('git -C %s status --porcelain | wc -l' % repo_path)
    try:
        dirty_count = int(dirty)
    except:
        dirty_count = 0
    clean_ok = dirty_count == 0
    verdict['checks'].append({
        'check': 'repo_clean', 'pass': clean_ok,
        'note': '%d dirty files' % dirty_count
    })

    # Build script exists?
    script_ok = os.path.isfile(build_script)
    verdict['checks'].append({
        'check': 'script', 'pass': script_ok,
        'note': build_script
    })

    # Disk space
    disk_raw = cmd("df -BM /opt | tail -1 | awk '{print $4}'")
    disk_mb = 0
    try:
        disk_mb = int(disk_raw.replace('M', ''))
    except:
        pass
    disk_ok = disk_mb > 500
    verdict['checks'].append({
        'check': 'disk', 'pass': disk_ok,
        'note': '%d MB free (need 500)' % disk_mb
    })

    # Estimate build time from page count
    page_count = cmd('find %s -name "*.md" -path "*/content/*" | wc -l' % repo_path)
    try:
        pages = int(page_count)
    except:
        pages = 0
    est_seconds = pages * 0.5  # ~0.5s per page on 2GB VPS
    verdict['checks'].append({
        'check': 'pages', 'pass': True,
        'note': '%d pages, est %.0fs build' % (pages, est_seconds)
    })

    # --- VERDICT ---
    all_pass = all(c['pass'] for c in verdict['checks'])
    if all_pass:
        verdict['verdict'] = 'BUILD'
        verdict['reason'] = 'all checks pass'
    else:
        failed = [c['check'] for c in verdict['checks'] if not c['pass']]
        if 'needs_build' in failed:
            verdict['verdict'] = 'SKIP'
            verdict['reason'] = 'up to date'
        else:
            verdict['verdict'] = 'DEFER'
            verdict['reason'] = 'failed: %s' % ', '.join(failed)

    return verdict


def main():
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    sites = [
        check_site('detroit',
            '/opt/ecoPrimals/detroit/worktree',
            '/run/membrane/detroit-last-built',
            '/opt/membrane/detroit-pull-build.sh'),
        check_site('tuebor',
            '/opt/ecoPrimals/tuebor-repo',
            '/run/membrane/tuebor-last-built',
            '/opt/membrane/tuebor-pull-build.sh'),
    ]

    plan = {
        'timestamp': now,
        'sites': sites,
        'summary': {
            'build': [s['site'] for s in sites if s['verdict'] == 'BUILD'],
            'defer': [s['site'] for s in sites if s['verdict'] == 'DEFER'],
            'skip':  [s['site'] for s in sites if s['verdict'] == 'SKIP'],
        }
    }

    with open(os.path.join(LIVE, 'build-plan.json'), 'w') as f:
        json.dump(plan, f, indent=2)

    for s in sites:
        v = s['verdict']
        icon = {'BUILD': '\U0001f528', 'DEFER': '\u23f8\ufe0f', 'SKIP': '\u23ed\ufe0f'}.get(v, '?')
        print('  %s %s: %s -- %s' % (icon, s['site'], v, s['reason']))
        for c in s['checks']:
            mark = 'Y' if c['pass'] else 'N'
            print('      %s %s: %s' % (mark, c['check'], c['note']))

if __name__ == '__main__':
    main()
