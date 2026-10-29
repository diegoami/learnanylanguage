from pathlib import Path

from lal import config


def test_the_users_own_config_is_never_used(cfg, tmp_path):
    assert cfg.file is None
    assert tmp_path in cfg.data_dir.parents


def test_environment_paths_are_relative_to_the_working_directory(cfg, tmp_path, monkeypatch):
    elsewhere = tmp_path / "user" / ".config" / "learnanylanguage"
    elsewhere.mkdir(parents=True)
    (elsewhere / "lal.toml").write_text('data_dir = "data"\ntrack_path = ["mine"]\n', encoding="utf-8")
    monkeypatch.setenv("LAL_TRACK_PATH", "tracks")
    loaded = config.load()
    assert loaded.file == elsewhere / "lal.toml"
    assert loaded.data_dir == elsewhere / "data"
    assert loaded.track_path == [Path.cwd() / "tracks", elsewhere / "mine"]
    monkeypatch.setenv("LAL_DATA", "here")
    assert config.load().data_dir == Path.cwd() / "here"
