#!/usr/bin/env python3
"""neutron-cache-sense.py — pre-fetch neutron channels into a single cache file.

The elaston: absorbs rate-limit pressure by bouncing with the pulse beat.
MCP tools read this cache instead of making 4 live API calls per request.
Refreshes every pulse cycle (~2 min).
"""
import json, time, urllib.request, os

NEUTRON = "http://127.0.0.1:8097"
CACHE_PATH = "/opt/membrane/live-terminal/neutron-cache.json"
CHANNELS = ["neutron-inbox", "neutron-notes", "neutron-reminders", "neutron-chat"]
FRIENDLY = {"neutron-inbox": "inbox", "neutron-notes": "notes",
            "neutron-reminders": "reminders", "neutron-chat": "chat"}
LAST_N = 20  # keep last 20 per channel in cache

def fetch_channel(page):
    try:
        url = f"{NEUTRON}/api/discuss?page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "neutron-cache/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e), "comments": [], "total": 0}

def sense():
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cache = {
        "timestamp": ts,
        "type": "neutron-cache",
        "description": "Pre-fetched neutron channels — the elaston bounces with the beat",
        "channels": {}
    }
    
    total_all = 0
    for page in CHANNELS:
        friendly = FRIENDLY[page]
        data = fetch_channel(page)
        comments = data.get("comments", [])
        total = data.get("total", len(comments))
        total_all += total
        
        # Keep last N messages, most recent first
        recent = comments[-LAST_N:] if len(comments) > LAST_N else comments
        recent.reverse()
        
        msgs = []
        for c in recent:
            msgs.append({
                "time": c.get("ts", ""),
                "author": c.get("badge", "anon"),
                "body": c.get("body", ""),
                "badge": c.get("badge", ""),
            })
        
        cache["channels"][friendly] = {
            "total": total,
            "messages": msgs,
            "latest": msgs[0]["body"][:100] if msgs else "",
            "latest_time": msgs[0]["time"] if msgs else "",
        }
    
    cache["total_messages"] = total_all
    
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    
    print(f"[neutron-cache] {total_all} messages across {len(CHANNELS)} channels -> {CACHE_PATH}")

if __name__ == "__main__":
    sense()
