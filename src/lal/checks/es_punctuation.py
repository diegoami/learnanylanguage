"""Spanish punctuation and interrogative accents in lesson text.

Flags a Spanish question or exclamation without its opening «¿»/«¡», and an
interrogative word without its accent right after «¿» (¿Donde → ¿Dónde).
Only Spanish-looking sentences are checked, so English stage directions in a
package are left alone.
"""

from __future__ import annotations

import re
from pathlib import Path

DESCRIPTION = "Spanish ¿…? / ¡…! pairs and accented interrogatives"

SPANISH = re.compile(
    r"\b(qué|cómo|dónde|adónde|cuándo|cuánto|cuánta|cuántos|cuántas|cuál|cuáles|quién|"
    r"usted|ustedes|tiene|tienes|puede|puedes|quiere|quieres|hay|está|estás|es|eres|"
    r"vamos|me|le|te|por favor|gracias|hola|buenos|buenas|perdone|perdón|del|una|un|el|la|los|las)\b",
    re.I)
ENGLISH = re.compile(r"\b(the|you|your|what|where|when|how|who|is|are|does|do|did|can|it|this|that|there|excuse|much|many|learner|teacher|wait|ask|asks)\b", re.I)
UNACCENTED = {"que": "qué", "como": "cómo", "donde": "dónde", "adonde": "adónde", "cuando": "cuándo",
              "cuanto": "cuánto", "cuanta": "cuánta", "cuantos": "cuántos", "cuantas": "cuántas",
              "cual": "cuál", "cuales": "cuáles", "quien": "quién", "quienes": "quiénes"}
SENTENCE = re.compile(r"[^.?!:;«»“”\"()\n]*[?!]")


def scan(text: str) -> list[str]:
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in SENTENCE.finditer(line):
            sentence = match.group(0).strip()
            end = sentence[-1]
            opener = "¿" if end == "?" else "¡"
            if len(ENGLISH.findall(sentence)) >= len(SPANISH.findall(sentence)):
                continue
            if opener not in sentence:
                problems.append(f"line {number}: missing «{opener}»: {sentence}")
        for match in re.finditer(r"¿\s*(\w+)", line):
            word = match.group(1)
            if word.lower() in UNACCENTED:
                fixed = UNACCENTED[word.lower()]
                fixed = fixed.capitalize() if word[0].isupper() else fixed
                problems.append(f"line {number}: «¿{word}» → «¿{fixed}»?")
    return problems


def run(paths: list[Path]) -> tuple[list[str], bool]:
    report = []
    for path in paths:
        for problem in scan(path.read_text(encoding="utf-8")):
            report.append(f"{path}: {problem}")
    if not report:
        report.append(f"no Spanish punctuation problems in {len(paths)} file(s)")
        return report, False
    return report, True
