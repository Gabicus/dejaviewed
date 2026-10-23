#!/usr/bin/env python3
"""Local preview server for site/ that mimics Cloudflare Pages clean URLs.

Internal links are root-absolute clean URLs (/catalog, /e/<id>, /guides/), which neither
file:// nor `python -m http.server` resolve. This server does:

    /x            -> site/x.html          (or site/x/index.html when x is a directory)
    /dir/         -> site/dir/index.html
    /x.html       -> 308 to /x            (like Cloudflare; pass --no-redirect to serve directly)
    /go/<slug>    -> 302 per site/_redirects
    miss          -> site/404.html with status 404

Usage:
    python3 scripts/serve.py              # http://127.0.0.1:8000/
    python3 scripts/serve.py 8080 --host 0.0.0.0
"""
from __future__ import annotations

import argparse
import http.server
import os
from functools import partial
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parent.parent / "site"


def load_redirects() -> dict[str, tuple[str, int]]:
    out = {}
    f = SITE / "_redirects"
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith("#"):
                code = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 302
                out[parts[0].rstrip("/") or "/"] = (parts[1], code)
    return out


class CleanURLHandler(http.server.SimpleHTTPRequestHandler):
    redirect_html = True

    def _send_redirect(self, location: str, code: int) -> None:
        self.send_response(code)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _route(self) -> bool:
        """Handle redirects / rewrite self.path. Returns False when a response was already sent."""
        sp = urlsplit(self.path)
        path = unquote(sp.path)
        tail = ("?" + sp.query) if sp.query else ""
        rule = load_redirects().get(path.rstrip("/") or "/")
        if rule:
            self._send_redirect(rule[0], rule[1])
            return False
        if self.redirect_html and path.endswith(".html"):
            clean = path[: -len("index.html")] if path.endswith("/index.html") or path == "/index.html" else path[:-5]
            self._send_redirect((clean or "/") + tail, 308)
            return False
        disk = SITE / path.lstrip("/")
        if path.endswith("/") or disk.is_dir():
            if disk.is_dir() and not path.endswith("/"):
                self._send_redirect(path + "/" + tail, 308)
                return False
            target = disk / "index.html"
        elif disk.is_file():
            return True
        else:
            target = disk.with_name(disk.name + ".html")
        if target.is_file():
            self.path = "/" + str(target.relative_to(SITE)) + tail
            return True
        self.send_404()
        return False

    def send_404(self) -> None:
        page = SITE / "404.html"
        body = page.read_bytes() if page.is_file() else b"404 Not Found"
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self._route():
            super().do_GET()

    def do_HEAD(self):  # noqa: N802
        if self._route():
            super().do_HEAD()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-redirect", action="store_true", help="serve /x.html directly instead of 308 -> /x")
    a = ap.parse_args()
    CleanURLHandler.redirect_html = not a.no_redirect
    handler = partial(CleanURLHandler, directory=os.fspath(SITE))
    with http.server.ThreadingHTTPServer((a.host, a.port), handler) as srv:
        print(f"serving {SITE} at http://{a.host}:{a.port}/  (clean URLs, Ctrl-C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
