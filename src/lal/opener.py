"""Open learner-data files in the learner's own editor instead of an editor in the page.

The command is `editor` in lal.toml (or $LAL_EDITOR), split like a shell
command, with the file appended: `editor = "code"` opens VS Code,
`editor = "code --reuse-window"`, `editor = "typora"`, `editor =
"open -a Obsidian"`. Without one, the system's opener for the file type is
used (`wslview` in WSL, `xdg-open` on Linux, `open` on macOS).
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from .config import Config

FALLBACKS = ("wslview", "xdg-open", "open")


def command(cfg: Config) -> list[str]:
    if cfg.editor:
        return shlex.split(cfg.editor)
    for name in FALLBACKS:
        if shutil.which(name):
            return [name]
    raise RuntimeError('no editor configured: set editor = "code" (or another command) in lal.toml')


def open_file(cfg: Config, path: Path) -> list[str]:
    """Start the editor on path, detached; return the command that was run."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    cmd = [*command(cfg), str(path)]
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return cmd
