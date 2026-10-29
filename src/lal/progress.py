"""Read the learner data into one structure for `lal gui`: trackers, lessons,
queues, teacher runs, and the git history when the folder is a repository.

Read-only. Progress here means exposure and transcript coverage, as in the
trackers: the model counts sessions, lessons and evidence labels, and never
computes a score.

The data can be a directory, a git repository (a directory with history), or
a git URL, which is cloned once into `<home>/remote/` and pulled on request.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

from . import report, tracks
from .config import Config

EVIDENCE = ("modelled", "repeated", "cued", "independent", "corrected and repeated", "needs another turn")
FOLDER = re.compile(r"^(\d{4}-\d{2}-\d{2})-session-(\d+)([A-Z]?)-([a-z]+?)(?:-(text))?$")
READABLE = {".md", ".toml", ".txt"}


# --- Markdown helpers ---------------------------------------------------------

def section(text: str, heading: str) -> str:
    """The body under `## heading` (any level), up to the next heading of the same or higher level."""
    match = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.M)
    if not match:
        return ""
    level = len(match.group(1))
    rest = text[match.end():]
    end = re.search(rf"^#{{1,{level}}} ", rest, re.M)
    return rest[: end.start()] if end else rest


def table(text: str) -> list[dict[str, str]]:
    """The first Markdown table in text, as rows keyed by header; placeholder rows dropped."""
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []

    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip("|").split("|")]

    header = cells(lines[0])
    rows = []
    for line in lines[2:]:
        values = cells(line)
        row = dict(zip(header, values + [""] * (len(header) - len(values))))
        if any(v and v not in ("—", "-") for v in values):
            rows.append(row)
    return rows


def evidence_counts(rows: list[dict[str, str]], column: str = "Evidence") -> dict[str, int]:
    counts = dict.fromkeys(EVIDENCE, 0)
    for row in rows:
        value = row.get(column, "").lower()
        for label in sorted(EVIDENCE, key=len, reverse=True):
            if label in value:
                counts[label] += 1
                value = value.replace(label, "")
    return counts


# --- the parts of the learner data ---------------------------------------------

def tracker(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sessions = table(section(text, "Current position"))
    vocabulary = table(section(text, "Vocabulary encountered"))
    sentences = table(section(text, "Sentence practice"))
    history = []
    entries = section(text, "Practice history")
    for match in re.finditer(r"^### (\d{4}-\d{2}-\d{2}) — (.+)$", entries, re.M):
        following = re.split(r"^### ", entries[match.end():], maxsplit=1, flags=re.M)[0]
        mode = re.search(r"^Mode: ([^.(\n]+)", following, re.M)
        history.append({"date": match.group(1), "title": match.group(2).strip(),
                        "mode": mode.group(1).strip() if mode else ""})
    updated = re.search(r"^Last updated: (.+)$", text, re.M)
    return {
        "updated": updated.group(1).strip() if updated else "",
        "sessions": sessions,
        "vocabulary": vocabulary,
        "sentences": sentences,
        "history": history,
        "evidence": evidence_counts(vocabulary + sentences),
    }


def recorded(transcript: Path) -> bool:
    """True once a conversation sits below the template's `---` line."""
    if not transcript.is_file():
        return False
    text = transcript.read_text(encoding="utf-8")
    _, sep, after = text.partition("\n---\n")
    return bool(sep and after.strip())


def lessons(sessions_dir: Path, root: Path) -> list[dict]:
    out = []
    if not sessions_dir.is_dir():
        return out
    for folder in sorted(sessions_dir.iterdir()):
        match = FOLDER.match(folder.name)
        if not folder.is_dir() or not match:
            continue
        transcript = folder / "transcript.md"
        has_report = transcript.is_file() and report.extract(transcript.read_text(encoding="utf-8")) is not None
        out.append({
            "folder": folder.name,
            "date": match.group(1),
            "session": int(match.group(2)),
            "part": match.group(3),
            "mode": match.group(4),
            "channel": match.group(5) or ("text" if match.group(4) == "writing" else "voice"),
            "recorded": recorded(transcript),
            "report": has_report,
            "files": [str(p.relative_to(root)) for p in sorted(folder.iterdir()) if p.suffix in READABLE],
        })
    return out


def queue(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    active = table(section(text, "Active targets"))
    statuses: dict[str, int] = {}
    for row in active:
        status = re.sub(r"[*_]", "", row.get("Status", "")).strip() or "—"
        statuses[status] = statuses.get(status, 0) + 1
    return {"targets": active, "statuses": statuses,
            "history": table(section(text, "Repetition history"))}


def teacher_runs(path: Path) -> dict:
    if not path.is_file():
        return {"runs": [], "failed": {}}
    runs = table(path.read_text(encoding="utf-8"))
    failed: dict[str, dict[str, int]] = {}
    for run in runs:
        version = run.get("Prompt", "?") or "?"
        for check in re.findall(r"\bC\d+\b", run.get("Failed checks", "")):
            failed.setdefault(version, {}).setdefault(check, 0)
            failed[version][check] += 1
    return {"runs": runs, "failed": failed}


def git_info(root: Path) -> dict | None:
    def git(*args: str) -> str | None:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None

    if git("rev-parse", "--is-inside-work-tree") != "true":
        return None
    log = git("log", "-n", "40", "--date=short", "--format=%h%x09%ad%x09%s") or ""
    counts = git("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
    behind, ahead = (int(x) for x in counts.split()) if counts else (None, None)
    return {
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "remote": git("remote", "get-url", "origin"),
        "uncommitted": len((git("status", "--porcelain") or "").splitlines()),
        "ahead": ahead,
        "behind": behind,
        "log": [dict(zip(("hash", "date", "subject"), line.split("\t", 2))) for line in log.splitlines()],
    }


# --- the whole picture ------------------------------------------------------------

def is_url(source: str) -> bool:
    return bool(re.match(r"^(https?://|git@|ssh://)", source)) or source.endswith(".git")


def resolve(cfg: Config, source: str | None, pull: bool = False) -> Path:
    """The folder to read: the configured data, a given directory, or a clone of a git URL."""
    if not source:
        return cfg.data_dir
    if not is_url(source):
        return Path(source).expanduser().resolve()
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", source.rstrip("/").removesuffix(".git").split("/")[-1])
    target = cfg.home / "remote" / f"{name}-{hashlib.sha1(source.encode()).hexdigest()[:8]}"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", source, str(target)], check=True)
    elif pull:
        subprocess.run(["git", "-C", str(target), "pull", "--quiet", "--ff-only"], check=True)
    return target


def load(cfg: Config, root: Path) -> dict:
    if not root.is_dir():
        raise FileNotFoundError(f"no learner data at {root}")
    profile_path = root / "profile.toml"
    state_path = root / "state.toml"
    try:
        profile = tomllib.loads(profile_path.read_text(encoding="utf-8")) if profile_path.is_file() else {}
    except tomllib.TOMLDecodeError:
        profile = {}
    current = (tomllib.loads(state_path.read_text(encoding="utf-8")).get("current_track")
               if state_path.is_file() else None)
    installed = {t.id: t for t in tracks.installed(cfg)}
    track_list = []
    tracks_dir = root / "tracks"
    for folder in sorted(tracks_dir.iterdir()) if tracks_dir.is_dir() else []:
        if not (folder / "TRACKER.md").is_file():
            continue
        info = tracker(folder / "TRACKER.md")
        meta = installed.get(folder.name)
        statuses = [re.sub(r"[*_]", "", s.get("Status", "")).strip() for s in info["sessions"]]
        track_list.append({
            "id": folder.name,
            "title": meta.title if meta else folder.name,
            "language": meta.language_code if meta else "",
            "version": meta.version if meta else "",
            "installed": meta is not None,
            "covered": statuses.count("Covered"),
            "in_progress": statuses.count("In progress"),
            "session_count": len(meta.sessions) if meta else len(info["sessions"]),
            "tracker": info,
            "tracker_file": str((folder / "TRACKER.md").relative_to(root)),
            "lessons": lessons(folder / "sessions", root),
        })
    queues = {}
    for path in sorted((root / "queues").glob("*.md")) if (root / "queues").is_dir() else []:
        queues[path.stem] = {**queue(path), "file": str(path.relative_to(root))}
    return {
        "root": str(root),
        "learner": {"name": profile.get("name", ""), "about": profile.get("about", ""),
                    "languages": sorted(profile.get("languages", {}))},
        "current": current,
        "tracks": track_list,
        "queues": queues,
        "teacher": teacher_runs(root / "teacher-runs.md"),
        "git": git_info(root),
    }


def inside(root: Path, relative: str) -> Path:
    """A Markdown, TOML or text file inside the learner data; refuses anything outside it."""
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or path.suffix not in READABLE or not path.is_file():
        raise PermissionError(f"not a readable learner-data file: {relative}")
    return path


def read_file(root: Path, relative: str) -> str:
    return inside(root, relative).read_text(encoding="utf-8")
