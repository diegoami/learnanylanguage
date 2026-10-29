import json
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from lal import gui, learner, lesson, progress, tracks

TRACKER_ROWS = """
| 1 — Introductions and small talk | Covered | 2026-10-20 | greetings | Free conversation |
| 2 — Fika, food and likes | In progress | 2026-10-25 | café | Guided 2B |
"""
VOCAB = "| granne | neighbour | 1 | independent |\n| kanelbulle | cinnamon bun | 2 | modelled; repeated |\n"
HISTORY = """
### 2026-10-20 — Session 1: Repetition

Mode: repetition (voice). Teacher: ChatGPT, prompt g3 — sessions/2026-10-20-session-1-repetition/
"""
REPORT = """
**Teacher** (text): LESSON_REPORT
Mode: grammar drill
Items:
- 1: independent — Jag åt middag.
Corrections:
- None
Words given by the teacher:
- None
END_LESSON_REPORT
"""


@pytest.fixture
def data(dev_cfg):
    track = tracks.find(dev_cfg, "sv-everyday")
    learner.start(dev_cfg, track)
    root = dev_cfg.data_dir
    path = root / "tracks" / "sv-everyday" / "TRACKER.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("| 1 — Introductions and small talk | Not started | — | — | Repetition |\n"
                        "| 2 — Fika, food and likes | Not started | — | — | — |\n", TRACKER_ROWS.lstrip())
    text = text.replace("| --- | --- | --- | --- |\n\n## Sentence", "| --- | --- | --- | --- |\n" + VOCAB + "\n## Sentence")
    path.write_text(text + HISTORY, encoding="utf-8")
    lesson.write_skeleton(dev_cfg, track, "repetition", 1, "", "2026-10-20")
    done = lesson.write_skeleton(dev_cfg, track, "grammar", 3, "", "2026-10-26", channel="text")
    transcript = done.parent / "transcript.md"
    transcript.write_text(transcript.read_text(encoding="utf-8") + "**Learner** (text): Nu börjar vi\n" + REPORT,
                          encoding="utf-8")
    (root / "teacher-runs.md").write_text(learner.RUNS_TEMPLATE + "| 2026-10-26 | sv-everyday | 3 | grammar drill | g3 | gpt | text | C19, C21 | — | x |\n"
                                          "| 2026-10-27 | sv-everyday | 1 | free conversation | g3 | gpt | voice | C5 | — | y |\n",
                                          encoding="utf-8")
    queue = root / "queues" / "sv.md"
    queue.write_text(queue.read_text(encoding="utf-8").replace(
        "| Target | Source and origin | Evidence so far | Status |\n| --- | --- | --- | --- |\n",
        "| Target | Source and origin | Evidence so far | Status |\n| --- | --- | --- | --- |\n"
        "| i lördags | Swedish everyday 3A | cued | **Active** |\n"), encoding="utf-8")
    return dev_cfg


def test_progress_reads_trackers_lessons_queues_and_runs(data):
    model = progress.load(data, data.data_dir)
    assert model["current"] == "sv-everyday" and model["git"] is None
    t = model["tracks"][0]
    assert (t["id"], t["covered"], t["in_progress"], t["session_count"]) == ("sv-everyday", 1, 1, 3)
    assert t["tracker"]["evidence"]["independent"] == 1 and t["tracker"]["evidence"]["repeated"] == 1
    assert t["tracker"]["history"] == [{"date": "2026-10-20", "title": "Session 1: Repetition", "mode": "repetition"}]
    by_mode = {l["mode"]: l for l in t["lessons"]}
    assert not by_mode["repetition"]["recorded"]
    assert by_mode["grammar"]["recorded"] and by_mode["grammar"]["report"] and by_mode["grammar"]["channel"] == "text"
    assert model["queues"]["sv"]["statuses"] == {"Active": 1}
    assert model["teacher"]["failed"] == {"g3": {"C19": 1, "C21": 1, "C5": 1}}


def test_git_history_appears_for_a_repository(data):
    root = data.data_dir
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "Record lesson"]):
        subprocess.run(["git", "-C", str(root), *args], check=True)
    info = progress.load(data, root)["git"]
    assert info["log"][0]["subject"] == "Record lesson" and info["uncommitted"] == 0


def test_read_file_stays_inside_the_learner_data(data):
    root = data.data_dir
    assert "Tracker" in progress.read_file(root, "tracks/sv-everyday/TRACKER.md")
    for bad in ("../../etc/passwd", "/etc/passwd", "state.toml/../../x.md"):
        with pytest.raises(PermissionError):
            progress.read_file(root, bad)


def test_gui_serves_the_page_and_the_api(data):
    server = ThreadingHTTPServer(("127.0.0.1", 0), gui.handler(data, data.data_dir, False))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert b"Learning Progress" in urllib.request.urlopen(base + "/").read()
        model = json.loads(urllib.request.urlopen(base + "/api/progress").read())
        assert model["tracks"][0]["id"] == "sv-everyday" and model["pullable"] is False
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base + "/api/file?path=../../secret.md")
        assert error.value.code == 403
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/api/pull")
    finally:
        server.shutdown()
        server.server_close()
