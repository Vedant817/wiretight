"""The demo server: serves the labelled demo page and its payload.

``DEMO_MODE=video`` is required - demo mode is a deliberate act, not an
accident. The server never contacts Airwallex and refuses to start if
Airwallex credentials are visible in its environment, so nobody can mistake
a mocked demo for a sandbox run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from app.config import AIRWALLEX_SECRET_VARS
from tests.support.recording.page import render_page
from tests.support.recording.seed import build_demo_payload

_OK = 200
_SERVER_ERROR = 500


class _DemoHandler(BaseHTTPRequestHandler):
    payload: dict[str, object]
    page: bytes

    def do_GET(self) -> None:
        try:
            if urlsplit(self.path).path in {"/", "/index.html"}:
                self.send_response(_OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(self.page)))
                self.end_headers()
                self.wfile.write(self.page)
            elif self.path == "/api/demo.json":
                body = json.dumps(self.payload, ensure_ascii=True).encode("utf-8")
                self.send_response(_OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()
        except BrokenPipeError:
            pass

    def log_message(self, format: str, *args: object) -> None:
        # Quiet by default; the demo is recorded, not logged.
        if os.environ.get("DEMO_MODE") == "video":
            return
        sys.stderr.write(f"{self.address_string()} - {format % args}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests.support.recording.server",
        description="Serve the labelled demo mode (DEMO_MODE=video).",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    demo_mode = os.environ.get("DEMO_MODE")
    if demo_mode != "video":
        print(
            "Refusing to start: demo mode must be chosen deliberately. "
            "Set DEMO_MODE=video to serve the simulated demo.",
            file=sys.stderr,
        )
        return 2

    leaked = [name for name in AIRWALLEX_SECRET_VARS if os.environ.get(name)]
    if leaked:
        print(
            f"Refusing to start: the demo server can see {', '.join(leaked)}. "
            "The demo never talks to Airwallex; unset the credentials.",
            file=sys.stderr,
        )
        return 2

    payload = build_demo_payload()
    _DemoHandler.page = render_page(payload).encode("utf-8")
    _DemoHandler.payload = payload

    server = ThreadingHTTPServer((args.host, args.port), _DemoHandler)
    print(
        f"Demo mode (simulated) on http://{args.host}:{args.port} - "
        "all data synthetic, Airwallex calls mocked.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
