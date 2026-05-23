#!/usr/bin/env python3
"""Serve the browser demo for the cron model."""

import argparse
import http.server
import os
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GGUF_SOURCE = PROJECT_ROOT / "output/cron-model/final-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf"
GGUF_TARGET = PROJECT_ROOT / "demo/models/model-00001-of-00001.gguf"


def find_free_port(start: int = 8000, max_attempts: int = 10) -> int:
    """Find an available port starting from *start*."""
    for offset in range(max_attempts):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start


def ensure_model_symlink() -> None:
    """Create a symlink to the GGUF model inside demo/models/ if missing."""
    if GGUF_TARGET.exists():
        return

    if not GGUF_SOURCE.exists():
        print(
            f"Warning: GGUF model not found at {GGUF_SOURCE.relative_to(PROJECT_ROOT)}. "
            "The demo will start but inference won't work."
        )
        return

    GGUF_TARGET.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(os.path.relpath(GGUF_SOURCE, GGUF_TARGET.parent), GGUF_TARGET)
    print(
        f"Linked model: {GGUF_TARGET.relative_to(PROJECT_ROOT)} -> {GGUF_SOURCE.relative_to(PROJECT_ROOT)}"
    )


def main() -> None:
    """CLI entry point for the cron demo server."""
    parser = argparse.ArgumentParser(description="Serve the cron-expression browser demo.")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)",
    )
    parser.add_argument(
        "--bind",
        "-b",
        default="",
        help="Address to bind to (default: all interfaces)",
    )
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    ensure_model_symlink()
    os.chdir(PROJECT_ROOT / "demo")

    port = find_free_port(args.port)
    bind = args.bind or "localhost"

    handler = http.server.SimpleHTTPRequestHandler
    with http.server.HTTPServer((bind, port), handler) as httpd:
        url = f"http://localhost:{port}/"
        print(f"Serving the cron demo at {url}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
