#!/usr/bin/env python3
"""gate-relay — inter-gate message passing through golgi
HTTP endpoints:
  POST /api/gate-msg   {"from":"northGate","to":"sporeGate","body":"..."}
  GET  /api/gate-msg?gate=sporeGate  → returns pending messages
  GET  /api/gate-msg?all=1           → returns all recent messages

Messages persist in a JSON file. Max 200 messages kept.
Runs as a unix socket, Caddy reverse_proxies to it.
"""
import json, os, time, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver

MSG_FILE = "/opt/membrane/live-terminal/gate-messages.json"
MAX_MSGS = 200

def load_msgs():
    try:
        with open(MSG_FILE) as f:
            return json.load(f)
    except:
        return []

def save_msgs(msgs):
    msgs = msgs[-MAX_MSGS:]
    with open(MSG_FILE + ".tmp", "w") as f:
        json.dump(msgs, f, indent=2)
    os.rename(MSG_FILE + ".tmp", MSG_FILE)

class GateHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/gate-msg":
            self.send_response(404)
            self.end_headers()
            return
        qs = parse_qs(parsed.query)
        msgs = load_msgs()
        gate = qs.get("gate", [None])[0]
        if gate:
            filtered = [m for m in msgs if m.get("to") == gate and not m.get("read")]
            # mark as read
            for m in msgs:
                if m.get("to") == gate:
                    m["read"] = True
            save_msgs(msgs)
            result = filtered
        elif qs.get("all"):
            result = msgs[-50:]
        else:
            result = msgs[-20:]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"messages": result, "count": len(result)}, indent=2).encode())

    def do_POST(self):
        if self.path == "/chipmunk/note":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            note = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "session": body.get("session", "?"),
                    "note": body.get("note", ""),
                    "context": body.get("context", {})}
            notes_path = "/opt/membrane/live-terminal/human-notes.json"
            try:
                notes = json.load(open(notes_path))
                if not isinstance(notes, list): notes = []
            except: notes = []
            notes.append(note)
            notes = notes[-200:]
            with open(notes_path + ".tmp", "w") as f:
                json.dump(notes, f, indent=2)
            os.rename(notes_path + ".tmp", notes_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            return
        if self.path != "/api/gate-msg":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        if not body.get("from") or not body.get("body"):
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "need from + body"}).encode())
            return
        msg = {
            "id": int(time.time() * 1000),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "from": body["from"],
            "to": body.get("to", "all"),
            "body": body["body"],
            "read": False
        }
        msgs = load_msgs()
        msgs.append(msg)
        save_msgs(msgs)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "id": msg["id"]}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

if __name__ == "__main__":
    port = 9761
    server = HTTPServer(("127.0.0.1", port), GateHandler)
    print(f"gate-relay listening on 127.0.0.1:{port}")
    server.serve_forever()
