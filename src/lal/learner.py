"""The learner's own data, kept apart from tracks and the engine.

    <data_dir>/
      profile.toml              who the learner is (see PROFILE_TEMPLATE)
      state.toml                the current track
      teacher-runs.md           one row per lesson: how the teacher followed the prompt
      queues/<language>.md      shared repetition queue for all tracks of a language
      tracks/<track-id>/
        TRACKER.md              progress in that track (copied from the track)
        sessions/<date>-session-<N><part>-<mode>/package.md, transcript.md

Point $LAL_DATA (or `data_dir` in lal.toml) at a private git repository to
keep this history under version control.
"""

from __future__ import annotations

import datetime as dt
import shutil
import tomllib
from pathlib import Path

from .config import Config
from .tracks import Track

PROFILE_TEMPLATE = """\
# Who the learner is. The voice teacher sees one "Learner:" line built from
# the spoken name and notes for the lesson's language, then `about`.
name = ""
about = ""

# One table per language, keyed by language code.
# [languages.uk]
# spoken_name = "Діє́го"
# notes = "Uses masculine forms (я хоті́в би, я переду́мав)."
"""

QUEUE_TEMPLATE = """\
# Shared review queue — {language}

Last updated: {today}

Vocabulary and sentence patterns that need another natural turn, shared by
every {language} track. Each row keeps the track and lesson where it arose
and every later track that practised it. Include at most one or two active
targets in a lesson, and only where they fit.

Evidence (transcript-observable only): **modelled**, **repeated**, **cued**,
**independent**, **corrected and repeated**, **needs another turn**.
Status: **Active**, **Practised**, **Retired** (keep the row and its history).

## Active targets

| Target | Source and origin | Evidence so far | Status |
| --- | --- | --- | --- |

## Repetition history

| Date | Target | Practised in | Evidence |
| --- | --- | --- | --- |
"""

RUNS_TEMPLATE = """\
# Teacher runs

One row per recorded lesson, applying the adherence checklist in the engine's
`prompt/ITERATIONS.md` to the teacher's turns. Teacher behaviour only, never
learner scores.

| Date | Track | Lesson | Mode | Prompt | Model | Input mode | Failed checks | Notes | Folder |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""


def profile(cfg: Config) -> dict:
    path = cfg.data_dir / "profile.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def learner_line(cfg: Config, language: str) -> str:
    data = profile(cfg)
    lang = data.get("languages", {}).get(language, {})
    name = lang.get("spoken_name") or data.get("name")
    if not name:
        return ("<<FILL: the learner's name, forms and background; better, fill in "
                "profile.toml in the learner data and rebuild>>")
    parts = [f"{name}.", lang.get("notes", ""), data.get("about", "")]
    return " ".join(p.strip() for p in parts if p and p.strip())


def track_dir(cfg: Config, track_id: str) -> Path:
    return cfg.data_dir / "tracks" / track_id


def sessions_dir(cfg: Config, track_id: str) -> Path:
    return track_dir(cfg, track_id) / "sessions"


def queue_path(cfg: Config, language: str) -> Path:
    return cfg.data_dir / "queues" / f"{language}.md"


def current(cfg: Config) -> str | None:
    path = cfg.data_dir / "state.toml"
    if not path.is_file():
        return None
    return tomllib.loads(path.read_text(encoding="utf-8")).get("current_track")


def set_current(cfg: Config, track_id: str) -> None:
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    (cfg.data_dir / "state.toml").write_text(f'current_track = "{track_id}"\n', encoding="utf-8")


def start(cfg: Config, track: Track) -> list[Path]:
    """Create whatever the learner's data for this track still lacks."""
    created = []
    lang = track.language

    def write(path: Path, text: str) -> None:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            created.append(path)

    write(cfg.data_dir / "profile.toml", PROFILE_TEMPLATE)
    write(cfg.data_dir / "teacher-runs.md", RUNS_TEMPLATE)
    write(queue_path(cfg, lang.code),
          QUEUE_TEMPLATE.format(language=lang.name, today=dt.date.today().isoformat()))
    tracker = track_dir(cfg, track.id) / "TRACKER.md"
    if not tracker.exists():
        tracker.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(track.dir / "TRACKER.md", tracker)
        created.append(tracker)
    sessions_dir(cfg, track.id).mkdir(parents=True, exist_ok=True)
    set_current(cfg, track.id)
    return created
