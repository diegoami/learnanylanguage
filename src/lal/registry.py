"""Publish tracks as release assets and install them from releases.

A *source* publishes `tracks-index.json` next to one `<id>-<version>.tar.gz`
per track, normally as assets of a GitHub release (the workflow in
`.github/workflows/release-tracks.yml` does this). A source is written as:

    owner/repo             latest release: https://github.com/owner/repo/releases/latest/download/tracks-index.json
    owner/repo@TAG         that release:  .../releases/download/TAG/tracks-index.json
    https://.../index.json any index URL (archives are resolved relative to it)
    /path/to/dist          a local folder or index file (testing, offline use)

Every archive is checked against the index's SHA-256, unpacked with tarfile's
"data" filter, must contain exactly one track folder named after its id, and
is validated like a local track before it replaces the installed copy.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import shutil
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from . import tracks
from .config import Config

INDEX_NAME = "tracks-index.json"
INDEX_FORMAT = 1
USER_AGENT = "learnanylanguage"


# --- publishing -----------------------------------------------------------

def pack(directory: Path, out_dir: Path) -> Path:
    """Write a reproducible `<id>-<version>.tar.gz` of a valid track."""
    errors = tracks.validate(directory)
    if errors:
        raise ValueError(f"{directory}: " + "; ".join(errors))
    track = tracks.load(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{track.id}-{track.version}.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            data = path.read_bytes()
            info = tarfile.TarInfo(f"{track.id}/{path.relative_to(directory).as_posix()}")
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
    archive.write_bytes(gzip.compress(buffer.getvalue(), mtime=0))
    return archive


def build_index(dist: Path) -> Path:
    """Describe every archive in `dist` in `dist/tracks-index.json`."""
    entries = []
    for archive in sorted(dist.glob("*.tar.gz")):
        with tempfile.TemporaryDirectory() as tmp:
            track = tracks.load(_unpack(archive.read_bytes(), Path(tmp)))
        entries.append({
            "id": track.id,
            "version": track.version,
            "language": track.language_code,
            "title": track.title,
            "description": track.description,
            "sessions": len(track.sessions),
            "archive": archive.name,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "size": archive.stat().st_size,
        })
    index = dist / INDEX_NAME
    index.write_text(json.dumps({"format": INDEX_FORMAT, "tracks": entries}, indent=2,
                                ensure_ascii=False) + "\n", encoding="utf-8")
    return index


# --- fetching -------------------------------------------------------------

def index_url(source: str) -> str:
    local = Path(source).expanduser()
    if local.exists():
        local = local.resolve()
        return (local / INDEX_NAME if local.is_dir() else local).as_uri()
    if "://" in source:
        return source
    repo, _, tag = source.partition("@")
    if repo.count("/") != 1:
        raise ValueError(f"source {source!r}: use owner/repo[@tag], an index URL, or a local path")
    base = f"https://github.com/{repo}/releases"
    return f"{base}/download/{tag}/{INDEX_NAME}" if tag else f"{base}/latest/download/{INDEX_NAME}"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_index(source: str) -> tuple[str, list[dict]]:
    url = index_url(source)
    data = json.loads(_get(url))
    if data.get("format") != INDEX_FORMAT:
        raise ValueError(f"{url}: unsupported index format {data.get('format')!r}")
    return url, data["tracks"]


def available(sources: list[str]) -> list[tuple[str, dict]]:
    """(source, entry) for every track every source offers."""
    out = []
    for source in sources:
        _, entries = fetch_index(source)
        out.extend((source, e) for e in entries)
    return out


# --- installing -----------------------------------------------------------

def _unpack(data: bytes, into: Path) -> Path:
    """Unpack a track archive into `into` and return the track folder."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = tar.getmembers()
        roots = {m.name.split("/", 1)[0] for m in members}
        if len(roots) != 1:
            raise ValueError(f"archive must contain one track folder, found {sorted(roots)}")
        for m in members:
            if not (m.isfile() or m.isdir()):
                raise ValueError(f"archive member is not a plain file: {m.name}")
            if m.isfile() and Path(m.name).suffix not in tracks.ALLOWED_SUFFIXES:
                raise ValueError(f"file type not allowed in a track: {m.name}")
        tar.extractall(into, filter="data")
    folder = into / roots.pop()
    track = tracks.load(folder)
    if folder.name != track.id:
        raise ValueError(f"archive folder {folder.name!r} does not match track id {track.id!r}")
    return folder


def _place(folder: Path, cfg: Config) -> tracks.Track:
    errors = tracks.validate(folder)
    if errors:
        raise ValueError("track is invalid: " + "; ".join(errors))
    track = tracks.load(folder)
    cfg.tracks_dir.mkdir(parents=True, exist_ok=True)
    target = cfg.tracks_dir / track.id
    staging = cfg.tracks_dir / f".{track.id}.new"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(folder, staging)
    shutil.rmtree(target, ignore_errors=True)
    staging.rename(target)
    return tracks.load(target)


def install(cfg: Config, spec: str, sources: list[str] | None = None) -> tracks.Track:
    """Install `id` or `id@version` from the first source that offers it."""
    track_id, _, version = spec.partition("@")
    tried = []
    for source in sources or cfg.sources:
        url, entries = fetch_index(source)
        tried.append(source)
        matches = [e for e in entries if e["id"] == track_id and (not version or e["version"] == version)]
        if not matches:
            continue
        entry = matches[-1]
        data = _get(urllib.parse.urljoin(url, entry["archive"]))
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"{entry['archive']}: SHA-256 {digest} does not match the index")
        with tempfile.TemporaryDirectory() as tmp:
            return _place(_unpack(data, Path(tmp)), cfg)
    raise LookupError(f"{spec} not found in: {', '.join(tried)}")


def install_from(cfg: Config, location: str, sha256: str | None = None) -> tracks.Track:
    """Install from a track folder, a .tar.gz path, or a .tar.gz URL."""
    local = Path(location).expanduser()
    if local.is_dir():
        return _place(local, cfg)
    data = local.read_bytes() if local.is_file() else _get(location)
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError(f"{location}: SHA-256 does not match {sha256}")
    with tempfile.TemporaryDirectory() as tmp:
        return _place(_unpack(data, Path(tmp)), cfg)


def remove(cfg: Config, track_id: str) -> Path:
    target = cfg.tracks_dir / track_id
    if not (target / "track.toml").is_file():
        raise LookupError(f"{track_id} is not installed in {cfg.tracks_dir}")
    shutil.rmtree(target)
    return target
