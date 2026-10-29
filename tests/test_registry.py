import hashlib
import io
import json
import tarfile

import pytest

from lal import registry, tracks

from conftest import TRACKS


@pytest.fixture
def dist(tmp_path):
    out = tmp_path / "dist"
    for t in TRACKS.iterdir():
        registry.pack(t, out)
    registry.build_index(out)
    return out


def test_pack_is_reproducible(tmp_path):
    a = registry.pack(TRACKS / "es-travel", tmp_path / "a")
    b = registry.pack(TRACKS / "es-travel", tmp_path / "b")
    assert a.name == "es-travel-1.0.0.tar.gz" and a.read_bytes() == b.read_bytes()


def test_index_lists_every_track(dist):
    index = json.loads((dist / "tracks-index.json").read_text(encoding="utf-8"))
    assert {e["id"] for e in index["tracks"]} == {"uk-reactivation", "es-travel", "es-smalltalk"}
    for e in index["tracks"]:
        assert hashlib.sha256((dist / e["archive"]).read_bytes()).hexdigest() == e["sha256"]


def test_install_from_a_release_index(cfg, dist):
    track = registry.install(cfg, "es-smalltalk@1.0.0", [str(dist)])
    assert track.dir == cfg.tracks_dir / "es-smalltalk"
    assert [t.id for t in tracks.installed(cfg)] == ["es-smalltalk"]
    registry.install(cfg, "uk-reactivation", [(dist / "tracks-index.json").as_uri()])
    assert {t.id for t in tracks.installed(cfg)} == {"es-smalltalk", "uk-reactivation"}
    registry.remove(cfg, "es-smalltalk")
    assert [t.id for t in tracks.installed(cfg)] == ["uk-reactivation"]


def test_install_rejects_a_tampered_archive(cfg, dist):
    archive = dist / "es-travel-1.0.0.tar.gz"
    archive.write_bytes(archive.read_bytes() + b"\0")
    with pytest.raises(ValueError, match="SHA-256"):
        registry.install(cfg, "es-travel", [str(dist)])


def test_missing_track_or_version(cfg, dist):
    with pytest.raises(LookupError):
        registry.install(cfg, "es-travel@9.9.9", [str(dist)])


def _archive(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.mark.parametrize("members, message", [
    ({"es-travel/track.toml": b"", "es-travel/run.py": b"x"}, "not allowed"),
    ({"a/track.toml": b"", "b/track.toml": b""}, "one track folder"),
    ({"../evil/track.toml": b""}, None),
])
def test_install_from_rejects_unsafe_archives(cfg, tmp_path, members, message):
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(_archive(members))
    with pytest.raises((ValueError, tarfile.TarError, OSError), match=message):
        registry.install_from(cfg, str(bad))
    assert not (tmp_path / "evil").exists()


def test_install_from_a_folder(cfg):
    assert registry.install_from(cfg, str(TRACKS / "es-travel")).id == "es-travel"


def test_github_source_urls():
    assert registry.index_url("diegoami/learnanylanguage") == \
        "https://github.com/diegoami/learnanylanguage/releases/latest/download/tracks-index.json"
    assert registry.index_url("someone/tracks@tracks-2026.10") == \
        "https://github.com/someone/tracks/releases/download/tracks-2026.10/tracks-index.json"
    with pytest.raises(ValueError):
        registry.index_url("not-a-source")
