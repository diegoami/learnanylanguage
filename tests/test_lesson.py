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


FILLS = {
    "grammar": [
        (r"Pattern: <<FILL.*?>>", "Pattern: present tense to past tense."),
        (r"Instruction: <<FILL.*?>>", "Instruction: Proszę powiedzieć to w czasie przeszłym."),
        (r"Example: <<FILL.*?>>", "Example: Czytam. → Czytałem."),
        (r"<<FILL: 6–10 numbered.*?>>", "\n".join(f"{i}. Cue {i}. → Answer {i}." for i in range(1, 7))),
    ],
    "vocabulary": [
        (r"<<FILL: 6–10 numbered.*?>>", "\n".join(f"{i}. prompt {i} → word{i}" for i in range(1, 9))),
    ],
    "writing": [
        (r"Task: <<FILL.*?>>", "Task: Proszę napisać pięć zdań o swoim mieście."),
        (r"<<FILL: at most 8 lines.*?>>", "- mieszkam w … — I live in …\n- jest tu … — there is … here"),
        (r"Focus: <<FILL.*?>>", "Focus: locative after w and na."),
        (r"Follow-up task: <<FILL.*?>>", "Follow-up task: Proszę dodać dwa zdania o pogodzie."),
    ],
}


def fill(text: str, mode: str) -> str:
    for pattern, value in FILLS[mode]:
        text = re.sub(pattern, value, text, count=1)
    return re.sub(r'<<FILL: "None".*?>>', "None", text)


@pytest.mark.parametrize("mode, channel, folder", [
    ("grammar", None, "2026-10-29-session-1-grammar"),
    ("grammar", "text", "2026-10-29-session-1-grammar-text"),
    ("vocabulary", "voice", "2026-10-29-session-1-vocabulary"),
    ("writing", None, "2026-10-29-session-1-writing"),
])
def test_new_modes_build_fill_and_check(started, mode, channel, folder):
    learner.start(started, tracks.find(started, "pl-first-steps"))
    track = tracks.find(started, "pl-first-steps")
    path = lesson.write_skeleton(started, track, mode, 1, "", "2026-10-29", channel=channel)
    assert path.parent.name == folder
    text = path.read_text(encoding="utf-8")
    assert ("Channel: text" in text) == (channel == "text" or mode == "writing")
    assert "LESSON_REPORT" in (path.parent / "transcript.md").read_text(encoding="utf-8")
    path.write_text(fill(text, mode), encoding="utf-8")
    errors, _, summary = lesson.check(started, path)
    assert errors == [], errors
    assert summary.startswith(f"pl-first-steps, prompt {lesson.prompt_version()}, {lesson.MODES[mode]}")

    lesson.refresh(started, path)
    assert lesson.check(started, path)[0] == []


def test_grammar_items_must_be_numbered_pairs(started):
    track = tracks.find(started, "es-travel")
    path = lesson.write_skeleton(started, track, "grammar", 2, "", "2026-10-29")
    text = fill(path.read_text(encoding="utf-8"), "grammar").replace("3. Cue 3. → Answer 3.", "3. Cue 3.")
    path.write_text(text.replace("Example: Czytam. → Czytałem.", "Example: Czytam."), encoding="utf-8")
    errors, _, _ = lesson.check(started, path)
    assert any("not a \"cue → answer\" line: 3. Cue 3." in e for e in errors)
    assert any("Example" in e for e in errors)


def test_a_channel_the_mode_does_not_allow_is_refused(started):
    track = tracks.find(started, "es-travel")
    path = lesson.write_skeleton(started, track, "vocabulary", 1, "", "2026-10-29", channel="text")
    text = fill(path.read_text(encoding="utf-8"), "vocabulary")
    path.write_text(text.replace("Mode: vocabulary drill", "Mode: writing"), encoding="utf-8")
    errors, _, _ = lesson.check(started, path)
    assert errors  # a writing controller is not in the package
