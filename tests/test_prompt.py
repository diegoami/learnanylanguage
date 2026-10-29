import re

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
    track = tracks.load(TRACKS / "uk-reactivation")
    for mode in lesson.MODES:
        assert norm(lesson.controller(track, mode)) == norm(g2(mode)), mode


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
