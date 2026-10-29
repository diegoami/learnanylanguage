import re

import pytest

from lal import learner, lesson, tracks


@pytest.fixture
def started(dev_cfg):
    for track_id in ("uk-reactivation", "es-travel", "es-smalltalk"):
        learner.start(dev_cfg, tracks.find(dev_cfg, track_id))
    (dev_cfg.data_dir / "profile.toml").write_text(
        'name = "Diego"\nabout = "From Italy."\n[languages.uk]\nspoken_name = "Діє́го"\n'
        'notes = "Uses masculine forms."\n', encoding="utf-8")
    return dev_cfg


def fill_repetition(text: str) -> str:
    text = re.sub(r"<<FILL: optional.*?>>\n", "", text)
    text = re.sub(r"<<FILL: 3–6 lines.*?>>", "- Prompt one. → Line 1\n- Prompt two. → Line 2\n"
                  "- Prompt three. → Line 3", text)
    return re.sub(r'<<FILL: "None".*?>>', "None", text)


def test_start_creates_learner_data_and_switches_track(started):
    data = started.data_dir
    assert (data / "queues" / "uk.md").is_file() and (data / "queues" / "es.md").is_file()
    assert (data / "tracks" / "es-travel" / "TRACKER.md").is_file()
    assert learner.current(started) == "es-smalltalk"


def test_learner_line_is_per_language(started):
    assert learner.learner_line(started, "uk") == "Діє́го. Uses masculine forms. From Italy."
    assert learner.learner_line(started, "es") == "Diego. From Italy."


@pytest.mark.parametrize("track_id, session", [("uk-reactivation", 2), ("es-travel", 1), ("es-smalltalk", 2)])
def test_filled_repetition_package_passes_and_alterations_fail(started, track_id, session):
    track = tracks.find(started, track_id)
    path = lesson.write_skeleton(started, track, "repetition", session, "", "2026-10-29")
    assert path.parent.name == f"2026-10-29-session-{session}-repetition"
    errors, _, _ = lesson.check(started, path)
    assert any("<<FILL" in e for e in errors)

    path.write_text(fill_repetition(path.read_text(encoding="utf-8")), encoding="utf-8")
    errors, _, summary = lesson.check(started, path)
    assert errors == [], errors
    assert track_id in summary

    _, _, lines = track.opening(session)
    path.write_text(path.read_text(encoding="utf-8").replace(lines[0], lines[0] + " x"), encoding="utf-8")
    errors, _, _ = lesson.check(started, path)
    assert any("opening line 1" in e for e in errors)


def test_refresh_restores_the_controller(started):
    track = tracks.find(started, "es-travel")
    path = lesson.write_skeleton(started, track, "repetition", 1, "", "2026-10-29")
    path.write_text(fill_repetition(path.read_text(encoding="utf-8")).replace("Empecemos", "Vamos"),
                    encoding="utf-8")
    assert lesson.check(started, path)[0]
    lesson.refresh(started, path)
    assert lesson.check(started, path)[0] == []


def test_guided_needs_a_valid_part(started):
    track = tracks.find(started, "es-travel")
    with pytest.raises(ValueError, match="needs a part"):
        lesson.skeleton(started, track, "guided", 1, "")
    with pytest.raises(ValueError, match="parts A, B"):
        lesson.skeleton(started, track, "guided", 1, "C")
    assert "Lesson part: 1B" in lesson.skeleton(started, track, "guided", 1, "B")


def test_skeleton_refuses_to_overwrite(started):
    track = tracks.find(started, "es-travel")
    lesson.write_skeleton(started, track, "free", 2, "", "2026-10-29")
    with pytest.raises(FileExistsError):
        lesson.write_skeleton(started, track, "free", 2, "", "2026-10-29")


def test_an_empty_profile_leaves_the_learner_line_to_fill(dev_cfg):
    learner.start(dev_cfg, tracks.find(dev_cfg, "es-travel"))
    assert learner.learner_line(dev_cfg, "es").startswith("<<FILL")
