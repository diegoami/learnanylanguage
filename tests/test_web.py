import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from lal import learner, lesson, share, tracks, web


@pytest.fixture
def site(dev_cfg):
    track = tracks.find(dev_cfg, "pl-first-steps")
    learner.start(dev_cfg, track)
    path = lesson.write_skeleton(dev_cfg, track, "grammar", 1, "", "2026-10-29", channel="text")
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.handler(dev_cfg, ""))
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    server.RequestHandlerClass = web.handler(dev_cfg, origin)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield origin, path.parent
    server.shutdown()
    server.server_close()


def get(url):
    with urllib.request.urlopen(url) as response:
        return response.headers, response.read()


def post(url, data, origin):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(url, json.dumps(data).encode(), headers, method="POST")
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def status(call):
    with pytest.raises(urllib.error.HTTPError) as error:
        call()
    return error.value.code


def test_page_and_lessons(site):
    origin, folder = site
    headers, page = get(origin + "/")
    assert b"Language lessons" in page and "connect-src 'self' https://openrouter.ai" in headers["Content-Security-Policy"]
    lessons = json.loads(get(origin + "/api/lessons")[1])
    assert [(l["track"], l["folder"], l["language"], l["recorded"]) for l in lessons] == [
        ("pl-first-steps", folder.name, "pl", False)]
    data = json.loads(get(f"{origin}/api/lesson?track=pl-first-steps&folder={folder.name}")[1])
    assert data["package"].startswith("TEXT_SESSION_PACKAGE")
    assert status(lambda: get(origin + "/../pyproject.toml")) == 404
    assert status(lambda: get(f"{origin}/api/lesson?track=pl-first-steps&folder=..")) == 403


def test_transcripts_are_written_once_and_only_by_the_page(site):
    origin, folder = site
    body = {"track": "pl-first-steps", "folder": folder.name, "body": "**Learner** (text): Zaczynamy", "model": "m1"}
    assert status(lambda: post(origin + "/api/transcript", body, None)) == 403
    assert status(lambda: post(origin + "/api/transcript", body, "https://evil.example")) == 403
    assert post(origin + "/api/transcript", body, origin)["saved"].endswith("transcript.md")
    text = (folder / "transcript.md").read_text(encoding="utf-8")
    assert text.rstrip().endswith("**Learner** (text): Zaczynamy") and "- Model: m1" in text
    assert status(lambda: post(origin + "/api/transcript", body, origin)) == 409


def test_share_links_are_read_by_the_server(site, monkeypatch):
    origin, folder = site
    assert status(lambda: post(origin + "/api/share", {"url": "https://example.com/x"}, origin)) == 400
    monkeypatch.setattr(share, "read", lambda url, html, out: "<!-- 2 messages -->\n\n**Teacher** (voice): Lekcja skończona.")
    link = "https://chatgpt.com/share/abc-123"
    result = post(origin + "/api/share", {"url": link, "track": "pl-first-steps", "folder": folder.name}, origin)
    assert "Lekcja skończona." in result["transcript"] and result["saved"]
    text = (folder / "transcript.md").read_text(encoding="utf-8")
    assert f"Share link: {link}" in text and "- Model: ChatGPT (from the share link)" in text
