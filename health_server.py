#!/usr/bin/env python3
"""Lightweight HTTP health wrapper for DeepCloak PoC validation.

Exposes CLI tool checks as HTTP endpoints for Kubernetes health probes
and PoC test scenarios.
"""
import json
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "healthy", "service": "deepcloak"})
        elif self.path == "/version":
            self._version_check()
        elif self.path == "/cli-check":
            self._cli_check()
        elif self.path == "/import-check":
            self._import_check()
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _version_check(self):
        try:
            from deepcloak import __version__
            self._respond(200, {
                "version": f"deepcloak {__version__}",
                "exit_code": 0,
            })
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _cli_check(self):
        try:
            from deepcloak.cli import build_parser
            parser = build_parser()
            help_text = parser.format_help()
            self._respond(200, {
                "help_output": help_text,
                "exit_code": 0,
            })
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _import_check(self):
        modules = [
            "deepcloak",
            "deepcloak.cli",
            "deepcloak.config",
            "deepcloak.evidence",
            "deepcloak.bot_wall_detector",
            "deepcloak.fetch_router",
            "deepcloak.mcp_server",
            "deepcloak.progress",
            "deepcloak.research_core",
        ]
        results = {}
        for mod in modules:
            try:
                __import__(mod)
                results[mod] = "ok"
            except Exception as e:
                results[mod] = f"error: {e}"
        all_ok = all(v == "ok" for v in results.values())
        self._respond(200, {
            "modules": results,
            "all_ok": all_ok,
        })

    def log_message(self, format, *args):
        # Suppress default logging
        pass


if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"DeepCloak health server listening on port {port}", flush=True)
    server.serve_forever()
