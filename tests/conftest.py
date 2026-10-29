from pathlib import Path

import pytest

from lal import config

REPO = Path(__file__).resolve().parent.parent
TRACKS = REPO / "tracks"


@pytest.fixture
def cfg(tmp_path, monkeypatch) -> config.Config:
    """A config whose installed tracks and learner data live in tmp_path."""
    monkeypatch.setenv("LAL_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("LAL_DATA", raising=False)
    monkeypatch.delenv("LAL_TRACK_PATH", raising=False)
    monkeypatch.delenv("LAL_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    return config.load()


@pytest.fixture
def dev_cfg(cfg) -> config.Config:
    """Like cfg, but the repository's tracks are found without installing them."""
    cfg.track_path = [TRACKS]
    return cfg
