"""Build and check one-mode voice lesson packages for any track.

The parts of a VOICE_SESSION_PACKAGE that must be copied exactly (the
controller blocks, rendered for the track's language, the opening lines and
the teacher introduction) are copied mechanically by `skeleton`. The coding
agent then fills only the fields marked <<FILL: ...>>, and `check` verifies
that nothing copied was altered and that the brief respects its mode's limits.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import learner, tracks
from .config import Config
from .languages import Language

CONTROLLER_FILE = Path(__file__).resolve().parent / "prompt" / "CONTROLLER.md"
FILL = "<<FILL"
MODES = {
    "repetition": "repetition",
    "guided": "guided conversation",
    "free": "free conversation",
}
MAX_WEAK = 2
MAX_EXTRA_LINES = 2
RECALL_RANGE = (3, 6)
ACTIVE_RANGE = (4, 6)
MAX_GUIDED_STEPS = 10
MAX_VOCABULARY = 12
LENGTH = {
    "repetition": "{lines} Lines, then {recall} Recall prompts. Roughly 5–8 minutes.",
    "guided": "At most 10 Guided steps. Roughly 8–10 minutes.",
    "free": "About 15 learner turns. Roughly 8–10 minutes.",
}

TRANSCRIPT_TEMPLATE = """\
# Transcript — {track}, Session {label}, {mode}

Preferred: share the ChatGPT chat and give the link to the record workflow
(`workflows/record.md`), which fills this file from it. If pasting by hand,
include everything from the "Ready for voice" reply to the closing sentence,
unedited; it is the evidence.

## Test settings

- Mode: {mode} (voice | text dry run)
- Prompt version: {version}
- Model:
- Voice language setting: {language}
- Input mode: push-to-talk | hands-free
- Voice:
- Device:
- Notes (anything that sounded wrong, e.g. stress, speed, cut-offs):

---

"""


def _controller_text() -> str:
    return CONTROLLER_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")


def prompt_version() -> str:
    match = re.search(r"^Prompt version: (\S+)", _controller_text(), re.M)
    if not match:
        raise ValueError(f"Prompt version not found in {CONTROLLER_FILE}")
    return match.group(1)


def render(template: str, values: dict[str, str]) -> str:
    """Fill {{name}} placeholders; drop a line whose only content was an empty one."""
    out = []
    for line in template.split("\n"):
        names = re.findall(r"\{\{(\w+)\}\}", line)
        for name in names:
            if name not in values:
                raise KeyError(f"no value for placeholder {{{{{name}}}}}")
        if names and re.fullmatch(r"\s*-?\s*", re.sub(r"\{\{\w+\}\}", "", line)) \
                and not any(values[n] for n in names):
            continue
        out.append(re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], line))
    return "\n".join(out)


def block(name: str, values: dict[str, str]) -> str:
    match = re.search(rf"<!-- BEGIN {re.escape(name)} -->\n(.*?)\n<!-- END {re.escape(name)} -->",
                      _controller_text(), re.S)
    if not match:
        raise ValueError(f"block {name} not found in {CONTROLLER_FILE.name}")
    return render(match.group(1).strip("\n"), values)


def values_for(track: tracks.Track, language: Language) -> dict[str, str]:
    values = language.placeholders()
    values.update(version=prompt_version(), learner_context=track.learner_context)
    return values


def controller(track: tracks.Track, mode: str) -> str:
    values = values_for(track, track.language)
    return "\n\n".join([block("COMMON", values), block(f"MODE {mode}", values), block("CLOSE", values)])


def mode_of(package: str) -> str | None:
    match = re.search(r"^Mode: (.+)$", package, re.M)
    if not match:
        return None
    return next((k for k, v in MODES.items() if match.group(1).strip() == v), None)


def track_of(cfg: Config, package: str) -> tracks.Track:
    match = re.search(r"^Track: (\S+)", package, re.M)
    if not match:
        raise ValueError("package has no 'Track: <id> ...' line")
    return tracks.find(cfg, match.group(1))


def brief(cfg: Config, track: tracks.Track, mode: str, session: int, part: str) -> str:
    title, intro, lines = track.opening(session)
    queue = f"queues/{track.language_code}.md"
    weak_fill = ('<<FILL: "None", or at most two lines starting with "- ": expression — '
                 f"original source and origin, from {queue} in the learner data>>")
    head = [
        "SESSION_BRIEF",
        f"Mode: {MODES[mode]}",
        f"Track: {track.id} {track.version} — {track.title}",
        f"Session: {session} — {title}",
    ]
    who = f"Learner: {learner.learner_line(cfg, track.language_code)}"
    if mode == "repetition":
        body = [
            f"Length: {LENGTH[mode].format(lines=len(lines), recall='3–6')}",
            who,
            f"Lines ({len(lines)}):",
            "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1)),
            "<<FILL: optional, at most two extra numbered Lines for queued "
            "expressions, continuing the numbering, then fix the count in "
            "\"Lines (N)\" and in Length; otherwise delete this line>>",
            "Recall prompts:",
            f"<<FILL: 3–6 lines \"- <{track.language.name} prompt> → Line K\" "
            "that make the learner produce Line K without hearing it>>",
        ]
    elif mode == "guided":
        body = [
            f"Lesson part: {session}{part} — <<FILL: short name of this lesson part>>",
            f"Length: {LENGTH[mode]}",
            who,
            "Main goal: <<FILL: one sentence, functional goal of this part>>",
            "Teacher introduction:",
            intro,
            "Active phrase set:",
            "<<FILL: 4–6 closely related target expressions, one per line "
            "starting with \"- \">>",
            "Guided steps:",
            f"<<FILL: at most 10 numbered steps: the teacher's {track.language.name} line, "
            "then what the learner is to say as an outcome; no answers supplied>>",
        ]
    else:
        body = [
            f"Length: {LENGTH[mode]}",
            who,
            "Topic: <<FILL: one sentence in English>>",
            "Situation: <<FILL: who the teacher is and where, in one sentence>>",
            f"Opening question: <<FILL: one open {track.language.name} question>>",
            "Useful vocabulary:",
            "<<FILL: at most 12 lines starting with \"- \": words and chunks from "
            "the session's preparation section>>",
        ]
    tail = [
        "Earlier weak expressions included:",
        weak_fill,
        f"Source: {track.source}",
        "END_SESSION_BRIEF",
        "",
        "END_VOICE_SESSION_PACKAGE",
    ]
    return "\n".join(head + body + tail)


def skeleton(cfg: Config, track: tracks.Track, mode: str, session: int, part: str) -> str:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    s = track.session(session)
    if mode == "guided":
        if not part:
            raise ValueError("a guided lesson needs a part, e.g. --part A")
        if s.parts and part not in s.parts:
            raise ValueError(f"session {session} has parts {', '.join(s.parts)}, not {part}")
    return f"{controller(track, mode)}\n\n{brief(cfg, track, mode, session, part)}\n"


def write_skeleton(cfg: Config, track: tracks.Track, mode: str, session: int, part: str,
                   date: str, out: Path | None = None) -> Path:
    package = skeleton(cfg, track, mode, session, part)
    label = f"{session}{part}"
    out = out or learner.sessions_dir(cfg, track.id) / f"{date}-session-{label}-{mode}" / "package.md"
    if out.exists():
        raise FileExistsError(f"{out} already exists; refusing to overwrite")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(package, encoding="utf-8", newline="\n")
    transcript = out.parent / "transcript.md"
    if not transcript.exists():
        transcript.write_text(TRANSCRIPT_TEMPLATE.format(
            track=track.id, label=label, mode=MODES[mode], version=prompt_version(),
            language=track.language.name), encoding="utf-8", newline="\n")
    return out


def _field(package: str, name: str, following: str) -> str:
    match = re.search(rf"^{re.escape(name)}(.*?)^{re.escape(following)}", package, re.M | re.S)
    return match.group(1).strip() if match else ""


def _bullets(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip().startswith("- ")]


def _numbered(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"^\d+\. ", line)]


def check(cfg: Config, path: Path) -> tuple[list[str], list[str], str]:
    """(errors, warnings, summary) for a filled package."""
    package = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    errors: list[str] = []
    warnings: list[str] = []
    mode = mode_of(package)
    if mode is None:
        return [f"no valid 'Mode:' line ({', '.join(MODES.values())})"], [], ""
    try:
        track = track_of(cfg, package)
    except (ValueError, LookupError) as error:
        return [str(error)], [], ""

    if controller(track, mode) not in package:
        errors.append(f"{mode} controller for {track.language.name} is missing or was altered (copy it verbatim)")
    version = prompt_version()
    if f"Prompt version: {version}" not in package:
        errors.append(f"package does not state the current prompt version {version}")
    if FILL in package:
        errors.append(f"{package.count(FILL)} <<FILL: ...>> placeholder(s) remain")
    if not re.search(rf"^Track: {re.escape(track.id)} {re.escape(track.version)} ", package, re.M):
        warnings.append(f"package was built for another version of {track.id} (installed: {track.version})")

    match = re.search(r"^Session: (\d+)", package, re.M)
    session = int(match.group(1)) if match else None
    if session is None:
        errors.append("cannot read the session number from 'Session: N — ...'")

    weak_text = _field(package, "Earlier weak expressions included:", "Source:")
    weak = _bullets(weak_text)
    if weak_text != "None" and not weak:
        errors.append("earlier weak expressions must be 'None' or '- ' lines")
    if len(weak) > MAX_WEAK:
        errors.append(f"{len(weak)} earlier weak expressions; allowed at most {MAX_WEAK}")

    if mode == "repetition":
        lines = _numbered(_field(package, "Lines (", "Recall prompts:"))
        declared = re.search(r"^Lines \((\d+)\):", package, re.M)
        if not declared or int(declared.group(1)) != len(lines):
            errors.append(f"'Lines (N):' must declare the {len(lines)} numbered lines")
        if session is not None:
            _, _, opening_lines = track.opening(session)
            for i, line in enumerate(opening_lines, 1):
                if f"\n{i}. {line}\n" not in package:
                    errors.append(f"opening line {i} missing or altered: {line}")
            extra = len(lines) - len(opening_lines)
            if extra > MAX_EXTRA_LINES:
                errors.append(f"{extra} extra Lines; allowed at most {MAX_EXTRA_LINES}")
        recall = _bullets(_field(package, "Recall prompts:", "Earlier weak expressions"))
        low, high = RECALL_RANGE
        if not low <= len(recall) <= high:
            errors.append(f"{len(recall)} recall prompts; allowed {low}–{high}")
        for prompt in recall:
            ref = re.search(r"→ Line (\d+)\s*$", prompt)
            if not ref or not 1 <= int(ref.group(1)) <= len(lines):
                errors.append(f"recall prompt must end with '→ Line K' for an existing Line: {prompt}")
        summary = f"{len(lines)} lines, {len(recall)} recall prompts"
    elif mode == "guided":
        if session is not None:
            _, intro, _ = track.opening(session)
            if intro not in package:
                errors.append("teacher introduction is missing or altered")
        active = _bullets(_field(package, "Active phrase set:", "Guided steps:"))
        low, high = ACTIVE_RANGE
        if not 1 <= len(active) <= high:
            errors.append(f"active phrase set has {len(active)} items; allowed 1–{high}")
        elif len(active) < low:
            warnings.append(f"active phrase set has only {len(active)} items (plan: {low}–{high})")
        steps = _numbered(_field(package, "Guided steps:", "Earlier weak expressions"))
        if not steps:
            errors.append("guided steps are empty or not numbered")
        if len(steps) > MAX_GUIDED_STEPS:
            errors.append(f"{len(steps)} guided steps; allowed at most {MAX_GUIDED_STEPS}")
        summary = f"{len(active)} active phrases, {len(steps)} guided steps"
    else:
        for name in ("Topic:", "Situation:", "Opening question:"):
            value = re.search(rf"^{re.escape(name)}(.*)$", package, re.M)
            if not value or not value.group(1).strip():
                errors.append(f"field is empty: {name}")
        vocabulary = _bullets(_field(package, "Useful vocabulary:", "Earlier weak expressions"))
        if not vocabulary:
            errors.append("useful vocabulary has no '- ' lines")
        if len(vocabulary) > MAX_VOCABULARY:
            errors.append(f"{len(vocabulary)} vocabulary lines; allowed at most {MAX_VOCABULARY}")
        summary = f"{len(vocabulary)} vocabulary lines"
    return errors, warnings, (f"{track.id}, prompt {version}, {MODES[mode]}, {summary}, "
                              f"{len(weak)} weak expressions")


def refresh(cfg: Config, path: Path) -> None:
    """Replace the controller of an unused package with the current one."""
    package = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    mode = mode_of(package)
    match = re.search(r"^SESSION_BRIEF$", package, re.M)
    if mode is None or not match:
        raise ValueError(f"{path}: no Mode or SESSION_BRIEF line")
    track = track_of(cfg, package)
    path.write_text(controller(track, mode) + "\n\n" + package[match.start():],
                    encoding="utf-8", newline="\n")


def copy(path: Path) -> None:
    """Put the package on the clipboard (Windows via WSL, macOS, Wayland, X11)."""
    if shutil.which("powershell.exe") and shutil.which("wslpath"):
        win = subprocess.run(["wslpath", "-w", str(path.resolve())],
                             capture_output=True, text=True, check=True).stdout.strip()
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                 f"Get-Content -Raw -Encoding UTF8 '{win}' | Set-Clipboard"])
    else:
        for tool in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
            if shutil.which(tool[0]):
                result = subprocess.run(tool, input=path.read_bytes())
                break
        else:
            raise RuntimeError("No clipboard tool found; open the file and copy it by hand.")
    if result.returncode:
        raise RuntimeError("Copying to the clipboard failed.")
