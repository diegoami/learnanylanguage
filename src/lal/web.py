"""`lal web`: the lesson client, served on 127.0.0.1.

The page (`web/index.html`, `web/app.js`, `web/core.js`) runs a lesson
package with the teacher chosen per lesson:

- **ChatGPT**: the page copies the package; the learner pastes it into
  ChatGPT (Voice or typed), shares the chat and pastes the share link back.
  This server reads the link (`share.py`, which a browser page cannot do:
  share pages send no CORS header) and writes the transcript.
- **Own keys**: the page itself calls OpenRouter or Gemini (typed), plus
  ElevenLabs speech-to-text and voice (voice), with the learner's keys,
  which stay in the browser and never reach this server.

The server lists prepared lessons in the learner data and writes transcripts
into their folders. It binds to 127.0.0.1 only and accepts writes only from
its own page (same Origin, JSON body), so other sites cannot post to it.
Standard library only.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, companion, learner, opener, progress, share
from .config import Config

STATIC = Path(__file__).resolve().parent / "web"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".json": "application/manifest+json", ".svg": "image/svg+xml"}
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
MAX_BODY = 2_000_000


def language_of(package: str) -> str:
    match = re.search(r"^Language: (\S+)", package, re.M)
    return match.group(1) if match else ""


def lessons(cfg: Config) -> list[dict]:
    """Every lesson folder with a package, newest first, unrecorded ones marked."""
    out = []
    root = cfg.data_dir / "tracks"
    for track_dir in sorted(root.iterdir()) if root.is_dir() else []:
        for item in progress.lessons(track_dir / "sessions", cfg.data_dir):
            package = track_dir / "sessions" / item["folder"] / "package.md"
            if not package.is_file():
                continue
            out.append({**item, "track": track_dir.name,
                        "language": language_of(package.read_text(encoding="utf-8"))})
    out.sort(key=lambda x: (x["date"], x["folder"]), reverse=True)
    return sorted(out, key=lambda x: x["recorded"])  # unrecorded first, newest first within each


def folder(cfg: Config, track: str, name: str) -> Path:
    if not NAME.match(track or "") or not progress.FOLDER.match(name or ""):
        raise PermissionError("not a lesson folder")
    path = learner.sessions_dir(cfg, track) / name
    if not (path / "package.md").is_file():
        raise FileNotFoundError(f"no package in {track}/{name}")
    return path


def write_transcript(path: Path, body: str, model: str = "") -> None:
    """Put the conversation below the template's `---`; refuse to overwrite a recorded lesson."""
    transcript = path / "transcript.md"
    if progress.recorded(transcript):
        raise FileExistsError(f"{transcript} already holds a conversation")
    text = transcript.read_text(encoding="utf-8") if transcript.is_file() else "# Transcript\n\n---\n"
    if model:
        text = re.sub(r"^- Model:[ \t]*$", f"- Model: {model}", text, count=1, flags=re.M)
    if "\n---\n" not in text:
        text = text.rstrip("\n") + "\n\n---\n"
    transcript.write_text(text.rstrip("\n") + "\n\n" + body.strip() + "\n", encoding="utf-8", newline="\n")


def handler(cfg: Config, origin: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; connect-src 'self' https://openrouter.ai "
                             "https://generativelanguage.googleapis.com https://api.elevenlabs.io; "
                             "media-src 'self' blob:; img-src 'self' data:; style-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)

        def json(self, data: object, status: int = 200) -> None:
            self.send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                      "application/json; charset=utf-8")

        def fail(self, error: Exception) -> None:
            status = {PermissionError: 403, FileNotFoundError: 404, FileExistsError: 409}.get(type(error), 400)
            self.json({"error": str(error)}, status)

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            url = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(url.query)
            try:
                if url.path == "/api/info":
                    self.json({"server": "lal", "version": __version__, "data": str(cfg.data_dir)})
                elif url.path == "/api/lessons":
                    self.json(lessons(cfg))
                elif url.path == "/api/companion":
                    self.json({"markdown": companion.markdown(companion.build(cfg))})
                elif url.path == "/api/file":
                    text = progress.read_file(cfg.data_dir, query.get("path", [""])[0])
                    self.send(200, text.encode("utf-8"), "text/plain; charset=utf-8")
                elif url.path == "/api/lesson":
                    path = folder(cfg, query.get("track", [""])[0], query.get("folder", [""])[0])
                    transcript = path / "transcript.md"
                    self.json({"package": (path / "package.md").read_text(encoding="utf-8"),
                               "recorded": progress.recorded(transcript)})
                else:
                    name = "index.html" if url.path in ("/", "") else url.path.lstrip("/")
                    file = (STATIC / name).resolve()
                    if STATIC not in file.parents or not file.is_file():
                        raise FileNotFoundError(url.path)
                    self.send(200, file.read_bytes(), TYPES.get(file.suffix, "application/octet-stream"))
            except (PermissionError, FileNotFoundError, OSError, ValueError) as error:
                self.fail(error)

        def do_POST(self) -> None:  # noqa: N802
            if self.headers.get("Origin") != origin or "application/json" not in self.headers.get("Content-Type", ""):
                self.json({"error": "only this page may write"}, 403)
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self.json({"error": "request too large"}, 413)
                return
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                url = urllib.parse.urlparse(self.path).path
                if url == "/api/transcript":
                    path = folder(cfg, data.get("track", ""), data.get("folder", ""))
                    write_transcript(path, str(data.get("body", "")), str(data.get("model", "")))
                    companion.write(cfg)
                    self.json({"saved": str(path.relative_to(cfg.data_dir) / "transcript.md")})
                elif url == "/api/open":
                    self.json({"opened": opener.open_file(cfg, progress.inside(cfg.data_dir, str(data.get("path", ""))))})
                elif url == "/api/share":
                    link = str(data.get("url", ""))
                    if not re.match(r"^https://(chatgpt\.com|chat\.openai\.com)/share/[\w-]+$", link):
                        raise ValueError("not a ChatGPT share link (https://chatgpt.com/share/…)")
                    path = folder(cfg, data["track"], data["folder"]) if data.get("folder") else None
                    pasted = path / "shared-package.md" if path else None
                    text = share.read(link, None, pasted)
                    saved = None
                    if path:
                        write_transcript(path, f"Share link: {link}\n\n{text}", "ChatGPT (from the share link)")
                        saved = str(path.relative_to(cfg.data_dir) / "transcript.md")
                        companion.write(cfg)
                    self.json({"transcript": text, "saved": saved})
                else:
                    self.json({"error": "not found"}, 404)
            except (PermissionError, FileNotFoundError, FileExistsError, OSError, ValueError, KeyError,
                    RuntimeError) as error:
                self.fail(error)

        def log_message(self, *args) -> None:
            pass

    return Handler


def serve(cfg: Config, port: int = 8772, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(cfg, ""))
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    server.RequestHandlerClass = handler(cfg, origin)
    url = origin + "/"
    print(f"Lessons from {cfg.data_dir}\nOpen {url} (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
