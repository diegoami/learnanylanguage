"""Language profiles: the teacher's classroom phrases and the built-in checks.

Built-in profiles live in `lal/languages/<code>.toml`. A track for a language
without a built-in profile bundles a `language.toml` with the same keys; a
bundled profile supplies phrases only, never checks (tracks are data, and
checks are code that ships with the engine).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

BUILTIN_DIR = Path(__file__).resolve().parent / "languages"
PHRASES = ("start", "close", "english_please", "repeat_please", "go_on", "stop",
           "listen_repeat", "now_you", "correction")


@dataclass
class Language:
    code: str
    name: str
    native_name: str
    phrases: dict[str, str]
    praise: list[str]
    ack: list[str]
    interference: str
    stress_rule: str
    text_rule: str
    romanized_text_rule: str
    start_spoken: str
    checks: list[str]
    builtin: bool

    def placeholders(self) -> dict[str, str]:
        values = dict(self.phrases)
        values.update(
            language=self.name,
            praise=", ".join(f"«{p}»" for p in self.praise),
            ack=" or ".join(f"«{a}»" for a in self.ack),
            interference=f", or the learner uses {self.interference}" if self.interference else "",
            stress_rule=self.stress_rule,
            text_rule=self.text_rule,
        )
        return values


def parse(raw: dict, builtin: bool, origin: str) -> Language:
    missing = [k for k in ("code", "name", *PHRASES, "praise", "ack") if k not in raw]
    if missing:
        raise ValueError(f"{origin}: language profile lacks {', '.join(missing)}")
    return Language(
        code=raw["code"],
        name=raw["name"],
        native_name=raw.get("native_name", raw["name"]),
        phrases={k: raw[k] for k in PHRASES},
        praise=list(raw["praise"]),
        ack=list(raw["ack"]),
        interference=raw.get("interference", ""),
        stress_rule=raw.get("stress_rule", ""),
        text_rule=raw.get("text_rule", ""),
        romanized_text_rule=raw.get("romanized_text_rule", ""),
        start_spoken=raw.get("start_spoken", raw["start"]),
        checks=list(raw.get("checks", [])) if builtin else [],
        builtin=builtin,
    )


def builtin(code: str) -> Language | None:
    path = BUILTIN_DIR / f"{code}.toml"
    if not path.is_file():
        return None
    return parse(tomllib.loads(path.read_text(encoding="utf-8")), True, path.name)


def builtin_codes() -> list[str]:
    return sorted(p.stem for p in BUILTIN_DIR.glob("*.toml"))


def for_track(code: str, track_dir: Path) -> Language:
    """The built-in profile, else the one bundled with the track."""
    found = builtin(code)
    if found:
        return found
    bundled = track_dir / "language.toml"
    if bundled.is_file():
        lang = parse(tomllib.loads(bundled.read_text(encoding="utf-8")), False, str(bundled))
        if lang.code != code:
            raise ValueError(f"{bundled}: code {lang.code!r} does not match track language {code!r}")
        return lang
    raise ValueError(f"no language profile for {code!r}: not built in and no language.toml in {track_dir}")
