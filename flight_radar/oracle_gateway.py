"""Tiny read-only Oracle API: serves only public market snapshots and local city art."""
from __future__ import annotations
import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

DATA_ROOT = Path("/var/lib/flight-radar")
MAX_JSON = 1024 * 1024

class Handler(BaseHTTPRequestHandler):
    server_version = "FlightRadar/0.3"

    def respond(self, code: int, payload: bytes, mime: str, cache: str = "no-store"):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            body = json.dumps({"ok": True, "service": "flight-radar", "storage": "oracle"}).encode()
            return self.respond(200, body, "application/json")
        if path in ("/api/deals", "/api/market"):
            file = DATA_ROOT / "data" / "market.json"
            try:
                size = file.stat().st_size
                if size > MAX_JSON:
                    raise ValueError("snapshot over max size")
                data = file.read_bytes()
                json.loads(data)
                return self.respond(200, data, "application/json; charset=utf-8", "public, max-age=90")
            except (OSError, ValueError, json.JSONDecodeError):
                return self.respond(503, b'{"status":"pending","offers":[]}', "application/json")
        code = re.fullmatch(r"/images/destinations/([A-Z]{3})\.svg", path)
        if code:
            art = DATA_ROOT / "images" / "destinations" / (code.group(1) + ".svg")
            try:
                if art.stat().st_size > 250_000:
                    raise ValueError("asset too large")
                return self.respond(200, art.read_bytes(), "image/svg+xml", "public, max-age=86400")
            except (OSError, ValueError):
                pass
        self.respond(404, b'{"error":"not_found"}', "application/json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        parser.error("Oracle gateway must bind to IPv4 loopback only")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
