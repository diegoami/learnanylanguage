import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from lal import cli, config, gui, learner, opener, tracks


@pytest.fixture
def launched(monkeypatch):
    calls = []
    monkeypatch.setattr(opener.subprocess, "Popen", lambda cmd, **kw: calls.append(cmd))
    return calls


def test_editor_comes_from_the_config_or_the_environment(cfg, monkeypatch, tmp_path, launched):
    (tmp_path / "lal.toml").write_text('editor = "code --reuse-window"\n', encoding="utf-8")
    loaded = config.load()
    assert opener.command(loaded) == ["code", "--reuse-window"]
    monkeypatch.setenv("LAL_EDITOR", "typora")
    loaded = config.load()
    note = tmp_path / "note.md"
    note.write_text("x", encoding="utf-8")
    assert opener.open_file(loaded, note) == ["typora", str(note)] and launched == [["typora", str(note)]]
    with pytest.raises(FileNotFoundError):
        opener.open_file(loaded, tmp_path / "missing.md")


def test_without_an_editor_the_system_opener_is_used(cfg, monkeypatch):
    monkeypatch.setattr(opener.shutil, "which", lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None)
    assert opener.command(cfg) == ["xdg-open"]
    monkeypatch.setattr(opener.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="editor"):
        opener.command(cfg)


def test_lal_open_companion_writes_and_opens_it(dev_cfg, monkeypatch, launched):
    monkeypatch.setenv("LAL_EDITOR", "code")
    monkeypatch.setenv("LAL_DATA", str(dev_cfg.data_dir))
    monkeypatch.setenv("LAL_TRACK_PATH", str(dev_cfg.track_path[0]))
    learner.start(dev_cfg, tracks.find(dev_cfg, "sv-everyday"))
    assert cli.main(["open"]) == 0
    assert launched[-1] == ["code", str((dev_cfg.data_dir / "COMPANION.md").resolve())]
    assert cli.main(["open", "tracker"]) == 0
    assert launched[-1][-1].endswith("tracks/sv-everyday/TRACKER.md")


def test_the_progress_page_opens_learner_files_only_for_itself(dev_cfg, monkeypatch, launched):
    monkeypatch.setenv("LAL_EDITOR", "code")
    dev_cfg.editor = "code"
    learner.start(dev_cfg, tracks.find(dev_cfg, "sv-everyday"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), gui.handler(dev_cfg, dev_cfg.data_dir, False))
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    server.RequestHandlerClass = gui.handler(dev_cfg, dev_cfg.data_dir, False, origin)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def ask(path, sender):
        request = urllib.request.Request(origin + "/api/open", json.dumps({"path": path}).encode(),
                                         {"Content-Type": "application/json", "Origin": sender}, method="POST")
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    try:
        assert ask("tracks/sv-everyday/TRACKER.md", origin)["opened"][0] == "code"
        for path, sender in (("tracks/sv-everyday/TRACKER.md", "https://evil.example"), ("../../etc/passwd", origin)):
            with pytest.raises(urllib.error.HTTPError) as error:
                ask(path, sender)
            assert error.value.code == 403
        assert len(launched) == 1
    finally:
        server.shutdown()
        server.server_close()
