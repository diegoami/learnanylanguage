"""`lal gui`: a local, read-only web page for reading and evaluating progress.

Serves `gui/index.html` and two JSON endpoints on 127.0.0.1:

    /api/progress          the whole picture (progress.load), rebuilt per request
    /api/file?path=REL     one Markdown/TOML file inside the learner data
    /api/pull              `git pull --ff-only` for data cloned from a URL

Standard library only; nothing is written to the learner data.
"""

from __future__ import annotations

import json
import subprocess
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import opener, progress
from .config import Config

PAGE = Path(__file__).resolve().parent / "gui" / "index.html"


def handler(cfg: Config, root: Path, pullable: bool, origin: str = "") -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def json(self, data: object, status: int = 200) -> None:
            self.send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                      "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            url = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(url.query)
            try:
                if url.path in ("/", "/index.html"):
                    self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
                elif url.path == "/api/progress":
                    self.json({**progress.load(cfg, root), "pullable": pullable})
                elif url.path == "/api/file":
                    text = progress.read_file(root, query.get("path", [""])[0])
                    self.send(200, text.encode("utf-8"), "text/plain; charset=utf-8")
                elif url.path == "/api/pull" and pullable:
                    result = subprocess.run(["git", "-C", str(root), "pull", "--ff-only"],
                                            capture_output=True, text=True)
                    self.json({"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()})
                else:
                    self.json({"error": "not found"}, 404)
            except PermissionError as error:
                self.json({"error": str(error)}, 403)
            except (OSError, ValueError) as error:
                self.json({"error": str(error)}, 500)

        def do_POST(self) -> None:  # noqa: N802
            """Open a learner-data file in the configured editor; only from this page."""
            if (not origin or self.headers.get("Origin") != origin
                    or "application/json" not in self.headers.get("Content-Type", "")):
                self.json({"error": "only this page may ask"}, 403)
                return
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                if urllib.parse.urlparse(self.path).path != "/api/open":
                    self.json({"error": "not found"}, 404)
                    return
                self.json({"opened": opener.open_file(cfg, progress.inside(root, str(data.get("path", ""))))})
            except PermissionError as error:
                self.json({"error": str(error)}, 403)
            except (OSError, ValueError, RuntimeError) as error:
                self.json({"error": str(error)}, 400)

        def log_message(self, *args) -> None:  # keep the terminal quiet
            pass

    return Handler


def serve(cfg: Config, source: str | None, port: int = 8770, open_browser: bool = True,
          pull: bool = False) -> None:
    root = progress.resolve(cfg, source, pull)
    progress.load(cfg, root)  # fail early on a missing folder
    pullable = bool(source and progress.is_url(source)) or pull
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(cfg, root, pullable))
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    server.RequestHandlerClass = handler(cfg, root, pullable, url.rstrip("/"))
    print(f"Reading {root}\nOpen {url} (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
