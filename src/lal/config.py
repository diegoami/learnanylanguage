"""Where things live: installed tracks, learner data, and track sources.

Resolution order for the config file: $LAL_CONFIG, ./lal.toml,
~/.config/learnanylanguage/lal.toml. Every key is optional:

    home = "~/.local/share/learnanylanguage"   # also $LAL_HOME
    data_dir = "<home>/learner"                # also $LAL_DATA
    tracks_dir = "<home>/tracks"               # where `lal track install` puts tracks
    track_path = ["tracks"]                    # extra track folders, searched first (development)
    sources = ["diegoami/learnanylanguage"]    # GitHub repos (or index URLs) that publish tracks

Relative paths in the file are relative to the file's directory.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SOURCE = "diegoami/learnanylanguage"


@dataclass
class Config:
    home: Path
    data_dir: Path
    tracks_dir: Path
    track_path: list[Path] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: [DEFAULT_SOURCE])
    file: Path | None = None


def _config_file() -> Path | None:
    candidates = [
        os.environ.get("LAL_CONFIG"),
        "lal.toml",
        Path.home() / ".config" / "learnanylanguage" / "lal.toml",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    return None


def load() -> Config:
    file = _config_file()
    raw = tomllib.loads(file.read_text(encoding="utf-8")) if file else {}
    base = file.parent if file else Path.cwd()

    def path(value: str | None, default: Path) -> Path:
        if not value:
            return default
        p = Path(value).expanduser()
        return p if p.is_absolute() else (base / p).resolve()

    home = path(os.environ.get("LAL_HOME") or raw.get("home"),
                Path.home() / ".local" / "share" / "learnanylanguage")
    data_dir = path(os.environ.get("LAL_DATA") or raw.get("data_dir"), home / "learner")
    tracks_dir = path(raw.get("tracks_dir"), home / "tracks")
    env_path = [p for p in os.environ.get("LAL_TRACK_PATH", "").split(os.pathsep) if p]
    track_path = [path(p, Path(p)) for p in env_path + list(raw.get("track_path", []))]
    sources = list(raw.get("sources") or [DEFAULT_SOURCE])
    return Config(home, data_dir, tracks_dir, track_path, sources, file)
