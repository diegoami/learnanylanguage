"""Read the LESSON_REPORT a teacher writes on request after the close.

The grammar, vocabulary and writing modes (experimental, prompt g3) let the
learner type «REPORT» after the closing sentence; the teacher then writes a
LESSON_REPORT block (format in CONTROLLER.md, block CLOSE report). The report
is a hint, never evidence: the record workflow checks every line against the
transcript turns, and the transcript wins.

This module finds the block in a transcript or a pasted reply, checks its
shape, flags what the controller forbids (scores, levels, pronunciation,
praise), and prints its items with the tracker's evidence labels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# A marker is a line of its own, perhaps after the `**Teacher** (text): ` prefix
# that `lal share` writes and inside the Markdown a chat reply may add.
MARKER = re.compile(r"^(?:\*\*Teacher\*\* \((?:voice|text)\):)?[\s*`#]*(END_)?LESSON_REPORT[\s*`]*$")
SECTIONS = {"items": "Items:", "corrections": "Corrections:", "words": "Words given by the teacher:"}
# Report outcome → the tracker's evidence label (workflows/record.md).
EVIDENCE = {
    "independent": "independent",
    "after a cue": "cued",
    "corrected": "corrected (check the transcript for the repetition)",
    "not reached": "not practised",
}
FORBIDDEN = re.compile(
    r"\b(scores?|scored|grades?|graded|percent|marks? out of|level|CEFR|[ABC][12]|pronunciation|"
    r"pronounced|accent|fluency|fluent|excellent|great job|well done|impressive)\b|\d+\s*%|\b\d+\s*/\s*\d+\b",
    re.I)


@dataclass
class Report:
    mode: str = ""
    items: list[tuple[str, str, str]] = field(default_factory=list)  # (item, outcome, said)
    corrections: list[str] = field(default_factory=list)
    words: list[str] = field(default_factory=list)


def clean(line: str) -> str:
    """Drop the markdown a chat reply may add: bold, code fences, headings, bullets."""
    line = re.sub(r"[*`]+", "", line).strip()
    line = re.sub(r"^#+\s*", "", line)
    return re.sub(r"^[-•]\s*", "- ", line)


def extract(text: str) -> str | None:
    """The body of the last LESSON_REPORT block in the text, or None.

    Only marker lines count, so a mention of LESSON_REPORT in a transcript's
    header or in a turn never starts a block; the empty template a package
    carries is skipped.
    """
    found = []
    body: list[str] | None = None
    for line in text.splitlines():
        marker = MARKER.match(line.strip())
        if marker and not marker.group(1):
            body = []
        elif marker and body is not None:
            found.append("\n".join(body))
            body = None
        elif body is not None:
            body.append(line)
    found = [b for b in found if "<Item number" not in b]
    return found[-1] if found else None


def parse(body: str) -> tuple[Report, list[str], list[str]]:
    """(report, errors, warnings) for the body of a LESSON_REPORT block."""
    report = Report()
    errors: list[str] = []
    warnings: list[str] = []
    section = None
    seen = set()
    for raw in body.splitlines():
        line = clean(raw)
        if not line:
            continue
        if line.startswith("Mode:"):
            report.mode = line[5:].strip()
            continue
        heading = next((k for k, v in SECTIONS.items() if line.lower() == v.lower()), None)
        if heading:
            section = heading
            seen.add(heading)
            continue
        if section is None:
            warnings.append(f"line outside the report's sections: {line}")
            continue
        if line.lstrip("- ").strip().lower() in ("none", "none."):
            continue
        if not line.startswith("- "):
            warnings.append(f"not a '- ' line under {SECTIONS[section]}: {line}")
            continue
        entry = line[2:].strip()
        if section == "items":
            match = re.match(r"(.+?):\s*(independent|after a cue|corrected|not reached)\s*(?:[—–-]\s*(.*))?$",
                             entry, re.I)
            if not match:
                errors.append(f"item without an allowed outcome ({', '.join(EVIDENCE)}): {entry}")
                continue
            report.items.append((match.group(1).strip(), match.group(2).lower(), (match.group(3) or "").strip()))
        elif section == "corrections":
            if "→" not in entry:
                warnings.append(f"correction without «…» → «…»: {entry}")
            report.corrections.append(entry)
        else:
            report.words.append(entry)
        hit = FORBIDDEN.search(entry)
        if hit:
            warnings.append(f"forbidden content «{hit.group(0)}» (scores, levels, pronunciation, praise): {entry}")
    if not report.mode:
        errors.append("no 'Mode:' line")
    for key, heading in SECTIONS.items():
        if key not in seen:
            errors.append(f"no '{heading}' section")
    return report, errors, warnings


def render(report: Report) -> str:
    """The report as Markdown tables for the record workflow, labelled as unverified."""
    out = [f"Report (unverified; check each row against the transcript) — mode: {report.mode or '?'}", "",
           "| Item | Outcome | Evidence label | Learner's final words |", "| --- | --- | --- | --- |"]
    out += [f"| {item} | {outcome} | {EVIDENCE[outcome]} | {said} |" for item, outcome, said in report.items]
    out += ["", "Corrections:"] + [f"- {c}" for c in report.corrections or ["None"]]
    out += ["", "Words given by the teacher:"] + [f"- {w}" for w in report.words or ["None"]]
    return "\n".join(out)


def read(path: Path) -> tuple[Report | None, list[str], list[str]]:
    body = extract(path.read_text(encoding="utf-8"))
    if body is None:
        return None, [f"{path}: no LESSON_REPORT … END_LESSON_REPORT block"], []
    return parse(body)
