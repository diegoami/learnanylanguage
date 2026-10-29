import re
import shutil

from lal import companion, learner, lesson, tracks

from conftest import TRACKS


def fill(text):
    text = re.sub(r"<<FILL: optional.*?>>\n", "", text)
    text = re.sub(r"<<FILL: 3–6 lines.*?>>", "- A. → Line 1\n- B. → Line 2\n- C. → Line 3", text)
    return re.sub(r'<<FILL: "None".*?>>', "None", text)


def test_companion_lists_covered_lessons_transcripts_next_and_planned(dev_cfg):
    track = tracks.find(dev_cfg, "uk-elementary")
    learner.start(dev_cfg, track)
    done = lesson.write_skeleton(dev_cfg, track, "repetition", 1, "", "2026-10-28")
    done.write_text(fill(done.read_text(encoding="utf-8")), encoding="utf-8")
    transcript = done.parent / "transcript.md"
    transcript.write_text(transcript.read_text(encoding="utf-8") + "**Teacher** (voice): кит\n", encoding="utf-8")
    lesson.write_skeleton(dev_cfg, track, "grammar", 4, "", "2026-10-29")
    tracker = learner.track_dir(dev_cfg, "uk-elementary") / "TRACKER.md"
    tracker.write_text(tracker.read_text(encoding="utf-8").replace(
        "| 1 — Alphabet and sound distinctions | Not started | — | — | Repetition |",
        "| 1 — Alphabet and sound distinctions | Covered | 2026-10-28 | и/і pairs | — |"), encoding="utf-8")

    text = companion.markdown(companion.build(dev_cfg), today="2026-10-29")
    assert "## Ukrainian A1–A2 in 27 topics (current)" in text
    assert "| 1 — Alphabet and sound distinctions | phonetics | Covered | 2026-10-28 |" in text
    assert ("- 2026-10-28 · session 1 · repetition: 10 lines to repeat, from «кит — кіт» · "
            "[transcript](tracks/uk-elementary/sessions/2026-10-28-session-1-repetition/transcript.md)") in text
    assert "- 2026-10-29 · session 4 · grammar drill" in text and "**transcript missing**" in text
    assert "**Next lesson:** session 2, " in text and "(this session's focus suits: repetition)" in text
    assert "#### Session 4 — Getting to know someone (vocabulary, grammar, conversation)" in text
    assert "- [ ] Say your name, where you are from and where you live." in text
    assert "- Session 7 — Weekdays and weekends: **Vocabulary:** daily routine verbs" in text
    assert "## Review queue (uk)" in text and "Nothing waiting." in text

    path = companion.write(dev_cfg)
    assert path == dev_cfg.data_dir / "COMPANION.md" and path.read_text(encoding="utf-8").startswith("# Companion")


def test_a_track_that_is_not_installed_still_shows_its_lessons(dev_cfg, tmp_path):
    copy = tmp_path / "tracks" / "sv-everyday"
    shutil.copytree(TRACKS / "sv-everyday", copy)
    dev_cfg.track_path = [tmp_path / "tracks"]
    learner.start(dev_cfg, tracks.find(dev_cfg, "sv-everyday"))
    shutil.rmtree(copy)
    text = companion.markdown(companion.build(dev_cfg), today="2026-10-29")
    assert "not installed here" in text


def test_unknown_focus_is_refused(tmp_path):
    track = tmp_path / "uk-elementary"
    shutil.copytree(TRACKS / "uk-elementary", track)
    toml = track / "track.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('focus = ["phonetics"]', 'focus = ["spelling"]', 1),
                    encoding="utf-8")
    assert any("unknown focus spelling" in e for e in tracks.validate(track))
