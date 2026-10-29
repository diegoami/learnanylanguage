"""Built-in, language-specific checks for lesson text.

A language profile lists its checks by name (`checks = ["uk_stress"]`). Each
check module defines `DESCRIPTION` and `run(paths) -> (report_lines, failed)`.
Checks ship with the engine only; a track can never add code.
"""

from __future__ import annotations

import importlib
from pathlib import Path

KNOWN = ("uk_stress", "es_punctuation")


def run(name: str, paths: list[Path]) -> tuple[list[str], bool]:
    if name not in KNOWN:
        raise ValueError(f"unknown check {name!r}")
    module = importlib.import_module(f"{__name__}.{name}")
    return module.run(paths)


def description(name: str) -> str:
    return importlib.import_module(f"{__name__}.{name}").DESCRIPTION
