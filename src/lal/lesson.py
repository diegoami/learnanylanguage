"""Build and check one-mode voice lesson packages for any track.

The parts of a VOICE_SESSION_PACKAGE that must be copied exactly (the
controller blocks, rendered for the track's language, the opening lines and
the teacher introduction) are copied mechanically by `skeleton`. The coding
agent then fills only the fields marked <<FILL: ...>>, and `check` verifies
that nothing copied was altered and that the brief respects its mode's limits.

Modes run in a channel: ChatGPT Voice (`voice`) or an ordinary typed ChatGPT
chat (`text`). The grammar, vocabulary and writing modes (experimental, since
prompt g3) end with an optional LESSON_REPORT the learner can ask for; see
`report.py`.
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
    "grammar": "grammar drill",
    "vocabulary": "vocabulary drill",
    "writing": "writing",
}
# The channels each mode runs in; the first is the default.
CHANNELS = {
    "repetition": ("voice",),
    "guided": ("voice",),
    "free": ("voice",),
    "grammar": ("voice", "text"),
    "vocabulary": ("voice", "text"),
    "writing": ("text",),
}
REPORT_MODES = ("grammar", "vocabulary", "writing")
MAX_WEAK = 2
MAX_EXTRA_LINES = 2
RECALL_RANGE = (3, 6)
ACTIVE_RANGE = (4, 6)
MAX_GUIDED_STEPS = 10
MAX_VOCABULARY = 12
ITEMS_RANGE = (6, 10)
WORDS_RANGE = (6, 10)
MAX_USEFUL = 8
LENGTH = {
    "repetition": "{lines} Lines, then {recall} Recall prompts. Roughly 5–8 minutes.",
    "guided": "At most 10 Guided steps. Roughly 8–10 minutes.",
    "free": "About 15 learner turns. Roughly 8–10 minutes.",
    "grammar": "The Items below, then at most three repeats. Roughly 5–8 minutes.",
    "vocabulary": "The Word set below, then at most three repeats. Roughly 5–8 minutes.",
    "writing": "One short text and one follow-up. Roughly 10–15 minutes.",
}

REPORT_NOTE = """

If you asked for the LESSON_REPORT after the close, it is part of the
conversation: keep it. The record workflow checks it against the turns."""

TRANSCRIPT_TEMPLATE = """\
# Transcript — {track}, Session {label}, {mode}

Preferred: share the ChatGPT chat and give the link to the record workflow
(`workflows/record.md`), which fills this file from it. If pasting by hand,
include everything from the "Ready for …" reply to the closing sentence,
unedited; it is the evidence.{report}

## Test settings

- Mode: {mode} ({channel})
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


def channel_for(mode: str, channel: str | None = None) -> str:
    """The channel a lesson runs in: the one asked for, if the mode allows it, else the default."""
    allowed = CHANNELS[mode]
    channel = channel or allowed[0]
    if channel not in allowed:
        raise ValueError(f"{MODES[mode]} lessons run in {' or '.join(allowed)}, not {channel}")
    return channel


def controller(track: tracks.Track, mode: str, channel: str | None = None) -> str:
    channel = channel_for(mode, channel)
    values = values_for(track, track.language)
    common = "COMMON" if channel == "voice" else "COMMON text"
    close = "CLOSE report" if mode in REPORT_MODES else "CLOSE"
    return "\n\n".join([block(common, values), block(f"MODE {mode}", values), block(close, values)])


def brief_of(package: str) -> str:
    """The SESSION_BRIEF and what follows it (the controller's report template has a Mode line too)."""
    match = re.search(r"^SESSION_BRIEF$", package, re.M)
    return package[match.start():] if match else package


def mode_of(package: str) -> str | None:
    match = re.search(r"^Mode: (.+)$", brief_of(package), re.M)
    if not match:
        return None
    return next((k for k, v in MODES.items() if match.group(1).strip() == v), None)


def channel_of(package: str, mode: str) -> str:
    """The brief's `Channel:` line; packages of the original modes have none (voice)."""
    match = re.search(r"^Channel: (\S+)", brief_of(package), re.M)
    return channel_for(mode, match.group(1) if match else None)


def folder_name(date: str, label: str, mode: str, channel: str) -> str:
    suffix = f"-{channel}" if len(CHANNELS[mode]) > 1 and channel != CHANNELS[mode][0] else ""
    return f"{date}-session-{label}-{mode}{suffix}"


def track_of(cfg: Config, package: str) -> tracks.Track:
    match = re.search(r"^Track: (\S+)", package, re.M)
    if not match:
        raise ValueError("package has no 'Track: <id> ...' line")
    return tracks.find(cfg, match.group(1))


def brief(cfg: Config, track: tracks.Track, mode: str, session: int, part: str,
          channel: str = "voice") -> str:
    title, intro, lines = track.opening(session)
    lang = track.language.name
    queue = f"queues/{track.language_code}.md"
    weak_fill = ('<<FILL: "None", or at most two lines starting with "- ": expression — '
                 f"original source and origin, from {queue} in the learner data>>")
    head = [
        "SESSION_BRIEF",
        f"Mode: {MODES[mode]}",
        *([f"Channel: {channel}"] if mode in REPORT_MODES else []),
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
    elif mode == "grammar":
        body = [
            f"Length: {LENGTH[mode]}",
            who,
            "Pattern: <<FILL: one English sentence for the teacher: the form practised and "
            "the change every Item asks for>>",
            f"Instruction: <<FILL: one short {lang} sentence telling the learner what to do>>",
            "Example: <<FILL: one \"cue → answer\" pair that is not among the Items>>",
            "Items:",
            "<<FILL: 6–10 numbered lines \"N. <cue> → <answer>\", built from the session's "
            "material; one change per Item>>",
        ]
    elif mode == "vocabulary":
        body = [
            f"Length: {LENGTH[mode]}",
            who,
            "Word set:",
            f"<<FILL: 6–10 numbered lines \"N. <prompt> → <word>\": the prompt a short {lang} "
            "definition, opposite or situation, or an English gloss; the word from the "
            "session's material>>",
        ]
    elif mode == "writing":
        body = [
            f"Length: {LENGTH[mode]}",
            who,
            f"Task: <<FILL: the writing task in {lang}, one to three short sentences, "
            "saying how many sentences to write (3–8)>>",
            "Useful language:",
            "<<FILL: at most 8 lines starting with \"- \": words and patterns from the "
            "session's material, each with its English meaning>>",
            "Focus: <<FILL: one English sentence: what the corrections look at first>>",
            f"Follow-up task: <<FILL: one {lang} sentence: a short second piece that reuses "
            "the corrected points>>",
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
        "END_VOICE_SESSION_PACKAGE" if channel == "voice" else "END_TEXT_SESSION_PACKAGE",
    ]
    return "\n".join(head + body + tail)


def skeleton(cfg: Config, track: tracks.Track, mode: str, session: int, part: str,
             channel: str | None = None) -> str:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    channel = channel_for(mode, channel)
    s = track.session(session)
    if mode == "guided":
        if not part:
            raise ValueError("a guided lesson needs a part, e.g. --part A")
        if s.parts and part not in s.parts:
            raise ValueError(f"session {session} has parts {', '.join(s.parts)}, not {part}")
    return f"{controller(track, mode, channel)}\n\n{brief(cfg, track, mode, session, part, channel)}\n"


def write_skeleton(cfg: Config, track: tracks.Track, mode: str, session: int, part: str,
                   date: str, out: Path | None = None, channel: str | None = None) -> Path:
    channel = channel_for(mode, channel)
    package = skeleton(cfg, track, mode, session, part, channel)
    label = f"{session}{part}"
    out = out or learner.sessions_dir(cfg, track.id) / folder_name(date, label, mode, channel) / "package.md"
    if out.exists():
        raise FileExistsError(f"{out} already exists; refusing to overwrite")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(package, encoding="utf-8", newline="\n")
    transcript = out.parent / "transcript.md"
    if not transcript.exists():
        transcript.write_text(TRANSCRIPT_TEMPLATE.format(
            track=track.id, label=label, mode=MODES[mode], version=prompt_version(),
            language=track.language.name,
            channel="voice | text dry run" if channel == "voice" else "text",
            report=REPORT_NOTE if mode in REPORT_MODES else ""), encoding="utf-8", newline="\n")
    return out


def _field(package: str, name: str, following: str) -> str:
    match = re.search(rf"^{re.escape(name)}(.*?)^{re.escape(following)}", package, re.M | re.S)
    return match.group(1).strip() if match else ""


def _bullets(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip().startswith("- ")]


def _numbered(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"^\d+\. ", line)]


def _line(text: str, name: str) -> str:
    value = re.search(rf"^{re.escape(name)}(.*)$", text, re.M)
    return value.group(1).strip() if value else ""


def _empty_fields(text: str, names: tuple[str, ...]) -> list[str]:
    return [f"field is empty: {name}" for name in names if not _line(text, name)]


def _pair(text: str) -> bool:
    """A "cue → answer" line with something on both sides of the arrow."""
    left, arrow, right = re.sub(r"^\d+\.\s*", "", text).partition(" → ")
    return bool(arrow and left.strip() and right.strip())


def _pairs_in_range(lines: list[str], what: str, bounds: tuple[int, int]) -> list[str]:
    low, high = bounds
    errors = [] if low <= len(lines) <= high else [f"{len(lines)} {what}; allowed {low}–{high}"]
    numbers = [int(re.match(r"\d+", line).group(0)) for line in lines]
    if numbers != list(range(1, len(lines) + 1)):
        errors.append(f"{what} must be numbered 1, 2, 3, … in order")
    errors += [f"not a \"cue → answer\" line: {line}" for line in lines if not _pair(line)]
    return errors


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

    try:
        channel = channel_of(package, mode)
    except ValueError as error:
        return [str(error)], [], ""
    if controller(track, mode, channel) not in package:
        errors.append(f"{mode} {channel} controller for {track.language.name} is missing or was altered "
                      "(copy it verbatim)")
    start = re.search(r"^SESSION_BRIEF$", package, re.M)
    if not start:
        return errors + ["no SESSION_BRIEF line"], warnings, ""
    brief_text = package[start.start():]
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

    weak_text = _field(brief_text, "Earlier weak expressions included:", "Source:")
    weak = _bullets(weak_text)
    if weak_text != "None" and not weak:
        errors.append("earlier weak expressions must be 'None' or '- ' lines")
    if len(weak) > MAX_WEAK:
        errors.append(f"{len(weak)} earlier weak expressions; allowed at most {MAX_WEAK}")

    if mode == "repetition":
        lines = _numbered(_field(brief_text, "Lines (", "Recall prompts:"))
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
        recall = _bullets(_field(brief_text, "Recall prompts:", "Earlier weak expressions"))
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
        active = _bullets(_field(brief_text, "Active phrase set:", "Guided steps:"))
        low, high = ACTIVE_RANGE
        if not 1 <= len(active) <= high:
            errors.append(f"active phrase set has {len(active)} items; allowed 1–{high}")
        elif len(active) < low:
            warnings.append(f"active phrase set has only {len(active)} items (plan: {low}–{high})")
        steps = _numbered(_field(brief_text, "Guided steps:", "Earlier weak expressions"))
        if not steps:
            errors.append("guided steps are empty or not numbered")
        if len(steps) > MAX_GUIDED_STEPS:
            errors.append(f"{len(steps)} guided steps; allowed at most {MAX_GUIDED_STEPS}")
        summary = f"{len(active)} active phrases, {len(steps)} guided steps"
    elif mode == "grammar":
        errors += _empty_fields(brief_text, ("Pattern:", "Instruction:", "Example:"))
        if not _pair(_line(brief_text, "Example:")):
            errors.append("the Example must be one \"cue → answer\" pair")
        items = _numbered(_field(brief_text, "Items:", "Earlier weak expressions"))
        errors += _pairs_in_range(items, "Items", ITEMS_RANGE)
        summary = f"{channel}, {len(items)} items"
    elif mode == "vocabulary":
        words = _numbered(_field(brief_text, "Word set:", "Earlier weak expressions"))
        errors += _pairs_in_range(words, "Word set entries", WORDS_RANGE)
        summary = f"{channel}, {len(words)} words"
    elif mode == "writing":
        errors += _empty_fields(brief_text, ("Task:", "Focus:", "Follow-up task:"))
        useful = _bullets(_field(brief_text, "Useful language:", "Focus:"))
        if not 1 <= len(useful) <= MAX_USEFUL:
            errors.append(f"useful language has {len(useful)} '- ' lines; allowed 1–{MAX_USEFUL}")
        summary = f"{channel}, {len(useful)} useful-language lines"
    else:
        errors += _empty_fields(brief_text, ("Topic:", "Situation:", "Opening question:"))
        vocabulary = _bullets(_field(brief_text, "Useful vocabulary:", "Earlier weak expressions"))
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
    channel = channel_of(package, mode)
    path.write_text(controller(track, mode, channel) + "\n\n" + package[match.start():],
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
