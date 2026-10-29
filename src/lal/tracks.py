"""Tracks: pluggable, data-only lesson content for one language.

A track is a folder (or a release archive of one) with:

    track.toml     id, version, language, title, source, learner_context, [[sessions]]
    README.md      what the track is for and how to study it
    OPENINGS.md    per session: `## Teacher introduction` (blockquote) and
                   `## Opening review` (bullets), under `# Session N — Title`
    MATERIAL.md    the learner's preparation material, `# Session N — Title`
    PLAN.md        session targets and coverage criteria
    TRACKER.md     the empty progress tracker copied to the learner's data
    language.toml  optional: a language profile, if the engine has none

`[phrases]` in track.toml may override the language profile's classroom
phrases for this track (for example the informal «Repite, por favor.»).

Only Markdown, TOML, JSON and plain-text files are allowed: tracks never carry
code.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import languages
from .config import Config

REQUIRED_FILES = ("track.toml", "README.md", "OPENINGS.md", "MATERIAL.md", "PLAN.md", "TRACKER.md")
ALLOWED_SUFFIXES = {".md", ".toml", ".json", ".txt"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass
class Session:
    number: int
    title: str
    parts: list[str]


@dataclass
class Track:
    dir: Path
    id: str
    version: str
    language_code: str
    title: str
    description: str
    source: str
    learner_context: str
    sessions: list[Session]
    phrases: dict[str, str]

    @property
    def language(self) -> languages.Language:
        lang = languages.for_track(self.language_code, self.dir)
        lang.phrases.update(self.phrases)
        return lang

    def session(self, number: int) -> Session:
        for s in self.sessions:
            if s.number == number:
                return s
        valid = ", ".join(str(s.number) for s in self.sessions)
        raise ValueError(f"{self.id} has no session {number} (sessions: {valid})")

    def read(self, name: str) -> str:
        return (self.dir / name).read_text(encoding="utf-8").replace("\r\n", "\n")

    def opening(self, number: int) -> tuple[str, str, list[str]]:
        """(title, teacher introduction, opening lines) of a session."""
        title, body = section(self.read("OPENINGS.md"), "#", number)
        intro = [line[1:].strip() for line in subsection(body, "Teacher introduction").splitlines()
                 if line.startswith(">")]
        lines = [line[2:].strip() for line in subsection(body, "Opening review").splitlines()
                 if line.startswith("- ")]
        if not intro or not lines:
            raise ValueError(f"{self.id}: session {number} opening script is incomplete")
        return title, " ".join(intro), lines


def section(text: str, level: str, number: int) -> tuple[str, str]:
    """Return (title, body) of the `<level> Session N — Title` section."""
    match = re.search(rf"^{level} Session {number} — (.+)$", text, re.M)
    if not match:
        raise ValueError(f"Session {number} heading not found")
    rest = text[match.end():]
    end = re.search(rf"^{level} Session \d+ — ", rest, re.M)
    return match.group(1).strip(), rest[: end.start()] if end else rest


def subsection(body: str, heading: str) -> str:
    match = re.search(rf"^#+ {heading}\s*$", body, re.M)
    if not match:
        return ""
    rest = body[match.end():]
    end = re.search(r"^(#+ |---\s*$)", rest, re.M)
    return (rest[: end.start()] if end else rest).strip()


def load(directory: Path) -> Track:
    raw = tomllib.loads((directory / "track.toml").read_text(encoding="utf-8"))
    missing = [k for k in ("id", "version", "language", "title", "source", "learner_context", "sessions")
               if k not in raw]
    if missing:
        raise ValueError(f"{directory}/track.toml lacks {', '.join(missing)}")
    sessions = [Session(int(s["number"]), s["title"], [p.upper() for p in s.get("parts", [])])
                for s in raw["sessions"]]
    phrases = dict(raw.get("phrases", {}))
    unknown = sorted(set(phrases) - set(languages.PHRASES))
    if unknown:
        raise ValueError(f"{directory}/track.toml: unknown [phrases] keys {', '.join(unknown)}")
    return Track(directory.resolve(), raw["id"], raw["version"], raw["language"], raw["title"],
                 raw.get("description", ""), raw["source"], raw["learner_context"], sessions, phrases)


def validate(directory: Path) -> list[str]:
    """Every problem that would make the track unusable or unsafe to publish."""
    errors = [f"missing {name}" for name in REQUIRED_FILES if not (directory / name).is_file()]
    for path in directory.rglob("*"):
        if path.is_symlink():
            errors.append(f"symbolic link not allowed: {path.relative_to(directory)}")
        elif path.is_file() and path.suffix not in ALLOWED_SUFFIXES:
            errors.append(f"file type not allowed in a track: {path.relative_to(directory)}")
    if errors:
        return errors
    try:
        track = load(directory)
    except (ValueError, KeyError, tomllib.TOMLDecodeError) as error:
        return [str(error)]
    if not ID_RE.match(track.id):
        errors.append(f"id {track.id!r}: use lowercase letters, digits and hyphens")
    if not VERSION_RE.match(track.version):
        errors.append(f"version {track.version!r}: use MAJOR.MINOR.PATCH")
    if not track.sessions:
        errors.append("no [[sessions]]")
    try:
        track.language
    except ValueError as error:
        errors.append(str(error))
    material = track.read("MATERIAL.md")
    for s in track.sessions:
        try:
            title, _, _ = track.opening(s.number)
        except ValueError as error:
            errors.append(f"OPENINGS.md: {error}")
            continue
        if title != s.title:
            errors.append(f"session {s.number}: OPENINGS.md title {title!r} differs from track.toml {s.title!r}")
        if not re.search(rf"^# Session {s.number} — ", material, re.M):
            errors.append(f"MATERIAL.md has no '# Session {s.number} — ...' section")
    return errors


def search_dirs(cfg: Config) -> list[Path]:
    return [*cfg.track_path, cfg.tracks_dir]


def installed(cfg: Config) -> list[Track]:
    """Every track found, the first of each id winning (track_path before tracks_dir)."""
    seen: dict[str, Track] = {}
    for base in search_dirs(cfg):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if (child / "track.toml").is_file():
                try:
                    track = load(child)
                except (ValueError, KeyError, tomllib.TOMLDecodeError):
                    continue
                seen.setdefault(track.id, track)
    return list(seen.values())


def find(cfg: Config, track_id: str) -> Track:
    for track in installed(cfg):
        if track.id == track_id:
            return track
    raise LookupError(f"track {track_id!r} is not installed (try: lal track install {track_id})")
