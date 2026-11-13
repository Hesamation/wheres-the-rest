"""Integration tests for app.server HTTP API and static file serving."""
import json
import http.client
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.server import make_server


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def test_server():
    port = find_free_port()
    server = make_server("127.0.0.1", port)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    base_url = f"http://127.0.0.1:{port}"

    try:
        # 1. GET /api/examples
        req = urllib.request.Request(f"{base_url}/api/examples")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert len(data) == 3
            ids = [x["id"] for x in data]
            assert "qa1" in ids and "qa2" in ids and "prod_control" in ids

        # 2. POST /api/report - saved QA1
        payload = json.dumps({"mode": "saved", "exampleId": "qa1"}).encode()
        req = urllib.request.Request(
            f"{base_url}/api/report",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 200
            report = json.loads(resp.read().decode())
            assert report["schemaVersion"] == "1"
            assert report["summary"]["overallCode"] == "MISMATCH"
            assert len(report["rows"]) >= 1

        # 3. POST /api/report - invalid example
        payload = json.dumps({"mode": "saved", "exampleId": "bogus"}).encode()
        req = urllib.request.Request(
            f"{base_url}/api/report",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "Expected 400 for bogus example"
        except urllib.error.HTTPError as e:
            assert e.code == 400

        # Reject negative sizes before reading; read(-1) waits for an EOF.
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        connection.request("POST", "/api/report", headers={"Content-Length": "-1"})
        response = connection.getresponse()
        assert response.status == 400
        response.read()
        connection.close()

        # A sibling with the same path prefix is still outside static/.
        with urllib.request.urlopen(base_url + "/style.css", timeout=2) as response:
            assert response.status == 200
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        connection.request("GET", "/../static-private/nonexistent.txt")
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        connection.close()

        # 4. POST /api/report - malformed JSON
        req = urllib.request.Request(
            f"{base_url}/api/report",
            data=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "Expected 400 for malformed JSON"
        except urllib.error.HTTPError as e:
            assert e.code == 400

        # 5. POST /api/report - invalid live request (missing signer)
        payload = json.dumps({
            "mode": "live",
            "txHash": "FD7gA9L45Btw79YvGL49km9nwgWcDJS4QjTid9G4CZFu",
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/api/report",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "Expected 400 for missing signer"
        except urllib.error.HTTPError as e:
            assert e.code == 400

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    test_server()
    print("test_api_server PASSED")
