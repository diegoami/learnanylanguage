import re

import pytest

from lal import lesson, tracks

from conftest import REPO, TRACKS

FIXTURE = REPO / "tests" / "fixtures" / "learnukrainian_g2_blocks.md"


def norm(text: str) -> str:
    return " ".join(text.split())


def g2(mode: str) -> str:
    text = FIXTURE.read_text(encoding="utf-8")
    return "\n\n".join(
        re.search(rf"<!-- BEGIN {n} -->\n(.*?)\n<!-- END {n} -->", text, re.S).group(1)
        for n in ("COMMON", f"MODE {mode}", "CLOSE"))


def test_ukrainian_renders_word_for_word_as_learnukrainian_g2():
    """The original modes are unchanged since g2; only the version line moved on."""
    track = tracks.load(TRACKS / "uk-reactivation")
    version = f"Prompt version: {lesson.prompt_version()}"
    for mode in ("repetition", "guided", "free"):
        expected = g2(mode).replace("Prompt version: g2", version)
        assert norm(lesson.controller(track, mode)) == norm(expected), mode


@pytest.mark.parametrize("mode, channel, common, close", [
    ("grammar", "voice", "VOICE_SESSION_PACKAGE", "LESSON_REPORT"),
    ("grammar", "text", "TEXT_SESSION_PACKAGE", "LESSON_REPORT"),
    ("vocabulary", "text", "TEXT_SESSION_PACKAGE", "LESSON_REPORT"),
    ("writing", None, "TEXT_SESSION_PACKAGE", "LESSON_REPORT"),
    ("guided", None, "VOICE_SESSION_PACKAGE", "Then wait. If you are asked for a summary"),
])
def test_modes_pick_their_common_and_close_blocks(mode, channel, common, close):
    text = lesson.controller(tracks.load(TRACKS / "pl-first-steps"), mode, channel)
    assert text.startswith(common) and close in text
    assert "{{" not in text and "Polish" in text


def test_channels_are_limited_per_mode():
    track = tracks.load(TRACKS / "es-travel")
    with pytest.raises(ValueError, match="run in voice"):
        lesson.controller(track, "guided", "text")
    with pytest.raises(ValueError, match="run in text"):
        lesson.controller(track, "writing", "voice")


def test_text_rule_is_dropped_when_empty_and_kept_for_japanese():
    assert "kanji" in lesson.controller(tracks.load(TRACKS / "ja-first-steps"), "writing")
    spanish = lesson.controller(tracks.load(TRACKS / "es-travel"), "writing")
    assert "\n- \n" not in spanish and "stress" not in spanish


def test_spanish_controller_uses_spanish_phrases_and_drops_empty_rules():
    track = tracks.load(TRACKS / "es-travel")
    text = lesson.controller(track, "free")
    assert "short spoken Spanish lesson" in text
    assert "say «Empecemos»" in text
    assert "«La clase ha terminado.»" in text
    assert "«Muy bien», «Excelente», «Perfecto», «Genial»" in text
    assert "Russian" not in text and "stress" not in text
    assert "hides the meaning,\n" in text  # no interference clause
    assert "{{" not in text and "Ukrainian" not in text


def test_track_phrases_override_the_language_profile():
    formal = lesson.controller(tracks.load(TRACKS / "es-travel"), "repetition")
    informal = lesson.controller(tracks.load(TRACKS / "es-smalltalk"), "repetition")
    assert "«Escuche y repita.»" in formal and "«Repita, por favor.»" in formal
    assert "«Escucha y repite.»" in informal and "«Repite, por favor.»" in informal


def test_render_drops_only_lines_whose_placeholders_are_all_empty():
    out = lesson.render("a\n- {{x}}\nb {{y}}c\n{{x}}{{y}}", {"x": "", "y": "Y"})
    assert out == "a\nb Yc\nY"
