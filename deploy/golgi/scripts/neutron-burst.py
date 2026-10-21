#!/usr/bin/env python3
"""neutron-burst: trusted write pore for the mesh.

Selective permeability:
  DNA  — opsonize discuss store (nucleus). Not rewritten here.
  RNA  — this pore. Mesh IPs (10.13.37.*) and localhost may transcribe.
  Protein — public neutron.json channel summaries only. No full bodies.

Writes go to opsonize (8097) so they enter the real channels.
A private sidecar (neutron-burst.json) keeps the audit trail.
Never mutate public neutron.json.
"""

import json, time, os, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

FEED_DIR = "/opt/membrane/live-terminal"
PRIVATE_DIR = "/opt/membrane/private"
PRIVATE = os.path.join(PRIVATE_DIR, "neutron-burst.json")
DISCUSS_API = "http://127.0.0.1:8097/api/discuss"

ALLOWED = {
    "127.0.0.1",
    "10.13.37.1",
    "10.13.37.2",
    "10.13.37.3",
    "10.13.37.5",
    "10.13.37.14",
    "10.13.37.16",
}

CHANNEL_PAGE = {
    "inbox": "neutron-inbox",
    "notes": "neutron-notes",
    "reminders": "neutron-reminders",
    "chat": "neutron-chat",
}


def _load_private():
    try:
        return json.load(open(PRIVATE))
    except Exception:
        return {"messages": []}


def _save_private(d):
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(PRIVATE, "w") as f:
        json.dump(d, f, indent=2)


def _post_opsonize(channel, text, author):
    payload = json.dumps({
        "page": CHANNEL_PAGE.get(channel, "neutron-notes"),
        "author": author,
        "body": text,
    }).encode()
    req = urllib.request.Request(
        DISCUSS_API,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "neutron-burst/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


class BurstHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        ip = self.client_address[0]
        if ip not in ALLOWED:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"not trusted","note":"selective permeability - mesh only"}')
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        channel = body.get("channel", "notes")
        if channel not in CHANNEL_PAGE:
            channel = "notes"
        text = body.get("body", "")
        author = body.get("author", "membrane-lens")

        if not text:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error":"empty body"}')
            return

        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entry = {"channel": channel, "body": text, "author": author, "timestamp": ts, "from": ip}

        d = _load_private()
        d.setdefault("messages", []).append(entry)
        d["messages"] = d["messages"][-100:]
        d["last_updated"] = ts
        _save_private(d)

        opsonize = _post_opsonize(channel, text, author)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "ok": True,
            "channel": channel,
            "pore": "burst",
            "opsonize": opsonize,
        }).encode())

    def do_GET(self):
        ip = self.client_address[0]
        if ip not in ALLOWED:
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        d = _load_private()
        msgs = d.get("messages", [])[-20:]
        self.wfile.write(json.dumps({
            "messages": msgs,
            "note": "private pore. full bodies do not cross to public neutron.json",
        }).encode())


if __name__ == "__main__":
    # Bind mesh+loopback only. UFW already drops 8098 from WAN; this is the second membrane.
    server = HTTPServer(("0.0.0.0", 8098), BurstHandler)
    print("neutron-burst listening on 0.0.0.0:8098 (mesh allowlist + UFW)")
    server.serve_forever()
