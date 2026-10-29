"""The companion: one page of what has been covered and what comes next.

`lal companion` writes `<data>/COMPANION.md` from the learner data and the
installed tracks, whatever route the lessons took (ChatGPT by copy and
paste, `lal web` with ChatGPT or own keys): every started track's position,
every lesson with what it practised and a link to its transcript (or how to
supply a missing one), the next lesson and sessions, sessions planned but
not written yet, and the review queue. Links are relative, so the file reads
the same on GitHub, in Obsidian, in `lal web` and in an editor.

Read-only over the trackers and lessons; it writes only COMPANION.md. Like
the trackers it describes exposure, never mastery or scores.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from . import learner, progress, tracks
from .config import Config

FILE = "COMPANION.md"
MODE_FOR_FOCUS = {"phonetics": "repetition", "vocabulary": "vocabulary drill", "grammar": "grammar drill",
                  "conversation": "guided and free conversation", "writing": "writing"}


def _brief(package: str) -> str:
    match = re.search(r"^SESSION_BRIEF$", package, re.M)
    return package[match.start():] if match else ""


def _after(brief: str, label: str) -> list[str]:
    """The `- ` or numbered lines under a `Label:` line of the brief, up to the next label."""
    match = re.search(rf"^{re.escape(label)}[^\n]*\n(.*?)(?=^[A-Z][A-Za-z ()0-9-]*:|\Z)", brief, re.M | re.S)
    lines = match.group(1).splitlines() if match else []
    return [re.sub(r"^(\d+\.|-)\s*", "", line).strip() for line in lines if re.match(r"^(\d+\.|-)\s", line)]


def _line(brief: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)} (.+)$", brief, re.M)
    return match.group(1).strip() if match else ""


def practised(package: str) -> str:
    """One line saying what a lesson package practised, from its brief."""
    brief = _brief(package)
    mode = _line(brief, "Mode:")
    if mode == "repetition":
        lines = _after(brief, "Lines (")
        return f"{len(lines)} lines to repeat, from «{lines[0]}»" if lines else "repetition"
    if mode == "guided conversation":
        return _line(brief, "Main goal:") or _line(brief, "Lesson part:")
    if mode == "free conversation":
        return _line(brief, "Topic:")
    if mode == "grammar drill":
        return _line(brief, "Pattern:")
    if mode == "vocabulary drill":
        words = [item.split(" → ")[-1] for item in _after(brief, "Word set:") if " → " in item]
        return "words: " + ", ".join(words) if words else "vocabulary"
    if mode == "writing":
        return _line(brief, "Task:")
    return mode


def _sessions_in_plan(plan: str) -> dict[int, tuple[str, str]]:
    """Every `## Session N — Title` in PLAN.md: {N: (title, body)}."""
    found = {}
    for match in re.finditer(r"^#{1,3} Session (\d+) — (.+)$", plan, re.M):
        rest = plan[match.end():]
        end = re.search(r"^#{1,3} ", rest, re.M)
        found[int(match.group(1))] = (match.group(2).strip(), (rest[: end.start()] if end else rest).strip())
    return found


def _plan_points(body: str) -> list[str]:
    return [re.sub(r"\s+", " ", m.group(1)).strip()
            for m in re.finditer(r"^- (.+?)(?=^- |^\s*$|\Z)", body, re.M | re.S)]


def _can_do(track: tracks.Track, number: int) -> list[str]:
    try:
        _, body = tracks.section(track.read("MATERIAL.md"), "#", number)
    except ValueError:
        return []
    items = tracks.subsection(body, "You should be able to")
    return [re.sub(r"^- \[[ x]\] ", "", line).strip() for line in items.splitlines() if line.startswith("- [")]


def track_view(cfg: Config, track_id: str) -> dict:
    root = cfg.data_dir
    info = progress.tracker(learner.track_dir(cfg, track_id) / "TRACKER.md")
    try:
        track = tracks.find(cfg, track_id)
    except LookupError:
        track = None
    status = {}
    for row in info["sessions"]:
        number = re.match(r"\s*(\d+)", row.get("Session", ""))
        if number:
            status[int(number.group(1))] = row
    lessons = []
    for item in reversed(progress.lessons(learner.sessions_dir(cfg, track_id), root)):
        folder = learner.sessions_dir(cfg, track_id) / item["folder"]
        package = (folder / "package.md").read_text(encoding="utf-8") if (folder / "package.md").is_file() else ""
        lessons.append({**item, "mode": _line(_brief(package), "Mode:") or item["mode"],
                        "practised": practised(package),
                        "transcript": str((folder / "transcript.md").relative_to(root)) if item["recorded"] else None,
                        "package": str((folder / "package.md").relative_to(root)) if package else None})
    sessions, planned = [], []
    if track:
        written = {s.number for s in track.sessions}
        plan = _sessions_in_plan(track.read("PLAN.md"))
        for s in track.sessions:
            row = status.get(s.number, {})
            sessions.append({"number": s.number, "title": s.title, "focus": s.focus,
                             "status": re.sub(r"[*_]", "", row.get("Status", "Not started")).strip() or "Not started",
                             "last": row.get("Last practice", "—"), "next": row.get("Next", "—"),
                             "points": _plan_points(plan.get(s.number, ("", ""))[1]),
                             "can_do": _can_do(track, s.number)})
        planned = [{"number": n, "title": title, "points": _plan_points(body)}
                   for n, (title, body) in sorted(plan.items()) if n not in written]
    return {"id": track_id, "title": track.title if track else track_id,
            "language": track.language_code if track else "", "installed": track is not None,
            "sessions": sessions, "planned": planned, "lessons": lessons}


def build(cfg: Config) -> dict:
    root = cfg.data_dir
    profile = learner.profile(cfg)
    started = sorted(p.name for p in (root / "tracks").iterdir()
                     if (p / "TRACKER.md").is_file()) if (root / "tracks").is_dir() else []
    current = learner.current(cfg)
    views = [track_view(cfg, t) for t in sorted(started, key=lambda t: (t != current, t))]
    queues = {}
    for lang in sorted({v["language"] for v in views if v["language"]}):
        path = learner.queue_path(cfg, lang)
        if path.is_file():
            queues[lang] = {**progress.queue(path), "file": str(path.relative_to(root))}
    return {"name": profile.get("name", ""), "current": current, "tracks": views, "queues": queues}


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def markdown(model: dict, today: str | None = None) -> str:
    today = today or dt.date.today().isoformat()
    who = f" — {model['name']}" if model["name"] else ""
    out = [f"# Companion{who}", "",
           f"What has been covered and what comes next, in every started track. Written by "
           f"`lal companion` on {today} from the trackers and lesson folders; regenerate it any time. "
           "It describes exposure seen in the transcripts, not mastery.", ""]
    if not model["tracks"]:
        out += ["No track started yet: `lal start <track>`.", ""]
    for view in model["tracks"]:
        mark = " (current)" if view["id"] == model["current"] else ""
        out += [f"## {view['title']}{mark}", "", f"`{view['id']}` · language `{view['language'] or '?'}`", ""]
        if view["sessions"]:
            out += ["### Where you are", "", "| Session | Focus | Status | Last practice | Next |", "| --- | --- | --- | --- | --- |"]
            out += [f"| {s['number']} — {_cell(s['title'])} | {', '.join(s['focus']) or '—'} | {_cell(s['status'])} | "
                    f"{_cell(s['last'])} | {_cell(s['next'])} |" for s in view["sessions"]]
            out.append("")
        out += ["### Lessons so far", ""]
        if not view["lessons"]:
            out.append("None yet.")
        for lesson in view["lessons"]:
            head = (f"- {lesson['date']} · session {lesson['session']}{lesson['part']} · {lesson['mode']}"
                    f"{' (text)' if lesson['channel'] == 'text' else ''}")
            what = f": {lesson['practised']}" if lesson["practised"] else ""
            if lesson["transcript"]:
                link = f" · [transcript]({lesson['transcript']})"
            else:
                link = (" · **transcript missing**: paste the ChatGPT share link (or the conversation) in "
                        "`lal web`, or give it to the agent to record")
            out.append(head + what + link)
        out.append("")
        upcoming = [s for s in view["sessions"] if s["status"] != "Covered"]
        out += ["### Coming next", ""]
        if not view["sessions"]:
            out += ["The track is not installed here, so its plan cannot be shown.", ""]
        elif not upcoming:
            out += ["Every written session is covered.", ""]
        else:
            first = upcoming[0]
            hint = first["next"] if first["next"] not in ("", "—") else "Repetition"
            modes = [MODE_FOR_FOCUS[f] for f in first["focus"] if f in MODE_FOR_FOCUS]
            out.append(f"**Next lesson:** session {first['number']}, {hint}"
                       + (f" (this session's focus suits: {', '.join(modes)})" if modes else "") + ".")
            out.append("")
            for s in upcoming:
                focus = f" ({', '.join(s['focus'])})" if s["focus"] else ""
                out.append(f"#### Session {s['number']} — {s['title']}{focus}")
                out.append("")
                out += [f"- {point}" for point in s["points"]]
                if s["can_do"]:
                    out += ["", "You should be able to:"] + [f"- [ ] {item}" for item in s["can_do"]]
                out.append("")
        if view["planned"]:
            out += ["### Planned, not written yet", ""]
            for s in view["planned"]:
                summary = "; ".join(s["points"][:2])
                out.append(f"- Session {s['number']} — {s['title']}" + (f": {summary}" if summary else ""))
            out.append("")
    for lang, queue in model["queues"].items():
        active = [r for r in queue["targets"] if "retired" not in r.get("Status", "").lower()]
        out += [f"## Review queue ({lang})", "", f"[Open the queue]({queue['file']})", ""]
        if active:
            out += ["| Target | From | Evidence so far | Status |", "| --- | --- | --- | --- |"]
            out += [f"| {_cell(r.get('Target', ''))} | {_cell(r.get('Source and origin', ''))} | "
                    f"{_cell(r.get('Evidence so far', ''))} | {_cell(r.get('Status', ''))} |" for r in active]
        else:
            out.append("Nothing waiting.")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write(cfg: Config) -> Path:
    path = cfg.data_dir / FILE
    path.write_text(markdown(build(cfg)), encoding="utf-8", newline="\n")
    return path
