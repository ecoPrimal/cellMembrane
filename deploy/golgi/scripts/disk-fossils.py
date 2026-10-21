#!/usr/bin/env python3
"""disk-fossils.py — Fossilize disk pressure before it lithifies.

Disk pressure rises silently: logs accumulate, git objects pack,
build artifacts pile up. Without cleaning, they lithify into stone
that fills the basin.

This script is the colon — it processes waste and expels what the
organism doesn't need. Runs as a MOTOR tier stop on the bus.

Thresholds:
  GREEN:  < 70%  (healthy)
  YELLOW: 70-80% (fossilize aggressively)
  RED:    > 80%  (emergency: truncate logs, vacuum git, clean tmp)
"""

import json, os, subprocess, time, shutil

LIVE = "/opt/membrane/live-terminal"


def disk_usage():
    st = os.statvfs("/")
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    used = total - free
    pct = (used / total) * 100
    return {"total_gb": total / 1e9, "free_gb": free / 1e9, "used_pct": round(pct, 1)}


def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except:
        return ""


def fossilize_logs(aggressive=False):
    """Rotate and compress logs."""
    actions = []

    # Caddy access log — the biggest eater
    caddy_log = "/var/log/caddy/access.log"
    if os.path.exists(caddy_log):
        size = os.path.getsize(caddy_log)
        if size > 50_000_000 or aggressive:  # 50MB or aggressive mode
            # Caddy handles its own rotation, but if it's huge, truncate
            if size > 100_000_000:
                os.truncate(caddy_log, 0)
                actions.append(f"truncated caddy access.log ({size // 1_000_000}MB)")
            elif aggressive:
                os.truncate(caddy_log, 0)
                actions.append(f"aggressive: truncated caddy access.log ({size // 1_000_000}MB)")

    # Membrane logs — truncate any over 10MB
    membrane_dir = "/var/log/membrane"
    if os.path.isdir(membrane_dir):
        for f in os.listdir(membrane_dir):
            path = os.path.join(membrane_dir, f)
            if os.path.isfile(path):
                size = os.path.getsize(path)
                threshold = 5_000_000 if aggressive else 10_000_000
                if size > threshold:
                    os.truncate(path, 0)
                    actions.append(f"truncated {f} ({size // 1_000_000}MB)")

    # Old rotated logs
    for d in ["/var/log/caddy", "/var/log/membrane"]:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".gz") or f.endswith(".1") or f.endswith(".2"):
                    path = os.path.join(d, f)
                    os.remove(path)
                    actions.append(f"removed {f}")

    return actions


def vacuum_git():
    """Garbage collect git repos."""
    actions = []
    repos = [
        "/opt/membrane",
        "/opt/ecoPrimals/infra/wateringHole",
    ]
    for repo in repos:
        git_dir = os.path.join(repo, ".git")
        if os.path.isdir(git_dir):
            before = run(f"du -sm {git_dir}")
            run(f"cd {repo} && git gc --auto --quiet")
            after = run(f"du -sm {git_dir}")
            actions.append(f"gc {repo}: {before.split()[0] if before else '?'}MB → {after.split()[0] if after else '?'}MB")
    return actions


def clean_tmp():
    """Remove old /tmp files."""
    actions = []
    now = time.time()
    tmp_dir = "/tmp"
    for f in os.listdir(tmp_dir):
        path = os.path.join(tmp_dir, f)
        try:
            if os.path.isfile(path) and (now - os.path.getmtime(path)) > 86400:
                os.remove(path)
                actions.append(f"removed /tmp/{f}")
        except:
            pass
    return actions


def vacuum_journal():
    """Vacuum systemd journal."""
    run("journalctl --vacuum-size=30M")
    return ["journal vacuumed to 30M max"]


def main():
    disk = disk_usage()
    pct = disk["used_pct"]

    status = "GREEN"
    actions = []

    if pct >= 80:
        status = "RED"
        actions += fossilize_logs(aggressive=True)
        actions += vacuum_git()
        actions += clean_tmp()
        actions += vacuum_journal()
    elif pct >= 70:
        status = "YELLOW"
        actions += fossilize_logs(aggressive=False)
        actions += clean_tmp()
    else:
        # GREEN — still check for oversized logs
        caddy_log = "/var/log/caddy/access.log"
        if os.path.exists(caddy_log) and os.path.getsize(caddy_log) > 100_000_000:
            actions += fossilize_logs(aggressive=False)

    disk_after = disk_usage()

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": "disk_fossils",
        "before": disk,
        "after": disk_after,
        "status": status,
        "actions": actions,
        "reclaimed_mb": round((disk_after["free_gb"] - disk["free_gb"]) * 1000, 1),
    }

    with open(os.path.join(LIVE, "disk-fossils.json"), "w") as f:
        json.dump(result, f, indent=2)

    print(f"DISK: {disk_after['used_pct']}% ({status}) | actions: {len(actions)} | reclaimed: {result['reclaimed_mb']}MB")
    for a in actions[:5]:
        print(f"  → {a}")


if __name__ == "__main__":
    main()
