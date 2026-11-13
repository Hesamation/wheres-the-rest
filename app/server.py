"""Standard-library HTTP server for payout-reader web UI and API.

Serves:
- Static assets (index.html, style.css, app.js) from static/
- GET /api/examples -> metadata for saved examples
- POST /api/report -> runs reconciliation worker (isolated subprocess, busy lock)

Default host: 127.0.0.1, default port: 8765 (overridable).
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adapter import SAVED_EXAMPLES_META  # noqa: E402
from app.runner import BusyError, run_worker  # noqa: E402
from app.validation import MAX_REQUEST_BYTES, validate_report_request  # noqa: E402


class PayoutRequestHandler(BaseHTTPRequestHandler):
    server_version = "PayoutReaderServer/1.0"

    def log_message(self, format: str, *args) -> None:
        """Clean custom request logging."""
        if len(args) >= 3:
            sys.stderr.write(f"[{self.log_date_time_string()}] {args[0]} {args[1]} -> {args[2]}\n")
        elif args:
            sys.stderr.write(f"[{self.log_date_time_string()}] {' '.join(str(a) for a in args)}\n")
        else:
            sys.stderr.write(f"[{self.log_date_time_string()}] {format}\n")

    def _send_json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def do_OPTIONS(self) -> None:
        """CORS pre-flight support."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self) -> None:
        """Handle HEAD requests for healthchecks and probes."""
        path = self.path.split("?")[0]
        if path in ("/healthz", "/api/health", "/api/examples", "/", "/index.html"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8" if path in ("/", "/index.html") else "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path in ("/healthz", "/api/health"):
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "payout-reader"})
            return

        if path == "/api/examples":
            examples_list = list(SAVED_EXAMPLES_META.values())
            # Return cleaned metadata list without internal fixture paths
            clean_list = [
                {
                    "id": ex["id"],
                    "label": ex["label"],
                    "txHash": ex["txHash"],
                    "signerId": ex["signerId"],
                    "capturedAt": ex["capturedAt"],
                    "summary": ex["summary"],
                }
                for ex in examples_list
            ]
            self._send_json(HTTPStatus.OK, clean_list)
            return

        # Static assets
        if path in ("/", "/index.html"):
            file_path = STATIC_DIR / "index.html"
        else:
            rel = path.lstrip("/")
            file_path = (STATIC_DIR / rel).resolve()
            # Prevent directory traversal outside STATIC_DIR
            if not file_path.is_relative_to(STATIC_DIR.resolve()):
                self._send_error(HTTPStatus.FORBIDDEN, "Access forbidden")
                return

        if not file_path.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        if "text" in content_type or "javascript" in content_type or "json" in content_type:
            content_type += "; charset=utf-8"

        try:
            content = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Failed to read file")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path != "/api/report":
            self._send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        # Bounded read
        content_length_header = self.headers.get("Content-Length")
        if not content_length_header:
            self._send_error(HTTPStatus.BAD_REQUEST, "Missing Content-Length header")
            return

        try:
            length = int(content_length_header)
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
            return

        if length < 0 or length > MAX_REQUEST_BYTES:
            self._send_error(
                HTTPStatus.BAD_REQUEST,
                f"Content-Length must be between 0 and {MAX_REQUEST_BYTES} bytes",
            )
            return

        try:
            body_bytes = self.rfile.read(length)
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            self._send_error(HTTPStatus.BAD_REQUEST, "Malformed JSON request body")
            return

        is_valid, err_msg, sanitized = validate_report_request(payload)
        if not is_valid:
            self._send_error(HTTPStatus.BAD_REQUEST, err_msg)
            return

        mode = sanitized["mode"]
        example_id = sanitized.get("exampleId")
        tx_hash = sanitized.get("txHash")
        signer_id = sanitized.get("signerId")

        try:
            envelope = run_worker(
                mode=mode,
                example_id=example_id,
                tx_hash=tx_hash,
                signer_id=signer_id,
            )
            self._send_json(HTTPStatus.OK, envelope)
        except BusyError as be:
            self._send_error(HTTPStatus.TOO_MANY_REQUESTS, str(be))
        except Exception as exc:
            self._send_error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"Reconciliation error: {type(exc).__name__}",
            )


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create a configured ThreadingHTTPServer instance."""
    server_address = (host, port)
    return ThreadingHTTPServer(server_address, PayoutRequestHandler)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run server until interrupted."""
    server = make_server(host, port)
    print(f"Payout Reader server running at http://{host}:{port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    port_arg = int(os.environ.get("PORT", "8765"))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    run_server(port=port_arg)
