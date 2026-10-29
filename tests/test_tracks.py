import shutil

import pytest

from lal import tracks

from conftest import TRACKS


@pytest.mark.parametrize("name", sorted(p.name for p in TRACKS.iterdir()))
def test_repository_tracks_are_valid(name):
    assert tracks.validate(TRACKS / name) == []


def test_two_languages_and_three_tracks_ship_with_the_repository():
    loaded = [tracks.load(p) for p in TRACKS.iterdir()]
    assert {t.language_code for t in loaded} == {"uk", "es"}
    assert len(loaded) >= 3


def test_validation_rejects_code_and_mismatched_titles(tmp_path):
    track = tmp_path / "es-travel"
    shutil.copytree(TRACKS / "es-travel", track)
    (track / "evil.py").write_text("print('hi')")
    text = (track / "track.toml").read_text(encoding="utf-8")
    (track / "track.toml").write_text(text.replace("Café, food and paying", "Café"), encoding="utf-8")
    errors = tracks.validate(track)
    assert any("evil.py" in e for e in errors)
    (track / "evil.py").unlink()
    errors = tracks.validate(track)
    assert any("differs from track.toml" in e for e in errors)


def test_unknown_language_needs_a_bundled_profile(tmp_path):
    track = tmp_path / "xx-demo"
    shutil.copytree(TRACKS / "es-travel", track)
    text = (track / "track.toml").read_text(encoding="utf-8")
    (track / "track.toml").write_text(text.replace('language = "es"', 'language = "it"')
                                      .replace('id = "es-travel"', 'id = "xx-demo"'), encoding="utf-8")
    assert any("no language profile for 'it'" in e for e in tracks.validate(track))
    profile = (TRACKS.parent / "src/lal/languages/es.toml").read_text(encoding="utf-8")
    (track / "language.toml").write_text(profile.replace('code = "es"', 'code = "it"'), encoding="utf-8")
    assert tracks.validate(track) == []
    lang = tracks.load(track).language
    assert lang.code == "it" and lang.checks == []  # bundled profiles never bring checks


def test_search_path_wins_over_installed(dev_cfg):
    assert tracks.find(dev_cfg, "es-travel").dir == TRACKS / "es-travel"
    with pytest.raises(LookupError):
        tracks.find(dev_cfg, "no-such-track")
