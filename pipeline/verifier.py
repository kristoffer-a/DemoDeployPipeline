"""Authenticated, read-only artifact verifier for C1/C2.

Run behind an approved HTTPS reverse proxy. The standalone server binds only to
localhost by default and has no tenant credentials or deployment privileges.
"""
import argparse
import base64
import binascii
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

from pipeline import artifacts

MAX_REQUEST_BYTES = 360 * 1024 * 1024


def verify_request(request):
    required = {"zipBase64", "manifest", "solution", "solutionVersion"}
    if not isinstance(request, dict) or set(request) not in (required, required | {"descriptor"}):
        raise ValueError("request must contain ZIP, manifest, solution and solutionVersion")
    try:
        content = base64.b64decode(request["zipBase64"], validate=True)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("invalid ZIP base64") from exc
    if not isinstance(request["solutionVersion"], str) or not request["solutionVersion"]:
        raise ValueError("an expected release version is required")
    if "descriptor" in request:
        descriptor = artifacts.verify_descriptor_bytes(content, request["manifest"], request["descriptor"],
                                                       request["solution"], request["solutionVersion"])
    else:
        descriptor = artifacts.verify_bytes(content, request["manifest"], request["solution"], request["solutionVersion"])
    return {"descriptor": descriptor, "zipBase64": base64.b64encode(content).decode("ascii")}


def handler(token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            # No request bodies, secrets or package contents are logged.
            pass

        def reply(self, status, value):
            data = json.dumps(value, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/verify":
                return self.reply(404, {"error": "not found"})
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                return self.reply(401, {"error": "unauthorized"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_REQUEST_BYTES:
                    return self.reply(413, {"error": "request exceeds size limit or is empty"})
                request = artifacts._json_load(self.rfile.read(size), "verification request")
                return self.reply(200, verify_request(request))
            except (ValueError, TypeError, KeyError) as exc:
                return self.reply(400, {"error": str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    token = os.environ.get("ALM_ARTIFACT_VERIFIER_TOKEN", "")
    if len(token) < 32:
        parser.error("ALM_ARTIFACT_VERIFIER_TOKEN must contain at least 32 characters")
    with HTTPServer((args.host, args.port), handler(token)) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
