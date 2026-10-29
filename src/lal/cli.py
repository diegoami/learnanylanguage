"""lal: choose a language and a track, install tracks from releases, and
build, check and record one-mode ChatGPT Voice lessons."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from . import __version__, checks, config, languages, learner, lesson, registry, share, tracks


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def resolve_track(cfg: config.Config, track_id: str | None) -> tracks.Track:
    track_id = track_id or learner.current(cfg)
    if not track_id:
        raise LookupError("no track chosen: pass --track ID or run `lal start ID`")
    return tracks.find(cfg, track_id)


# --- commands ---------------------------------------------------------------

def cmd_paths(cfg, args):
    print(f"config file : {cfg.file or '(none; defaults)'}")
    print(f"tracks dir  : {cfg.tracks_dir}")
    print(f"track path  : {', '.join(map(str, cfg.track_path)) or '(none)'}")
    print(f"learner data: {cfg.data_dir}")
    print(f"sources     : {', '.join(cfg.sources)}")
    return 0


def cmd_languages(cfg, args):
    seen = {}
    for code in languages.builtin_codes():
        seen[code] = (languages.builtin(code), "built in")
    for track in tracks.installed(cfg):
        if track.language_code not in seen:
            seen[track.language_code] = (track.language, f"bundled with {track.id}")
    by_lang: dict[str, list[str]] = {}
    for track in tracks.installed(cfg):
        by_lang.setdefault(track.language_code, []).append(track.id)
    for code, (lang, origin) in sorted(seen.items()):
        checks_ = ", ".join(lang.checks) or "none"
        print(f"{code}  {lang.name} ({lang.native_name}) — {origin}; checks: {checks_}; "
              f"tracks: {', '.join(by_lang.get(code, [])) or 'none installed'}")
    return 0


def cmd_track_list(cfg, args):
    found = tracks.installed(cfg)
    if not found:
        print("No tracks installed. See `lal track available`.")
    current = learner.current(cfg)
    for t in found:
        mark = "*" if t.id == current else " "
        print(f"{mark} {t.id:<18} {t.version:<8} {t.language_code}  {t.title}  [{t.dir}]")
    return 0


def cmd_track_available(cfg, args):
    installed = {t.id: t.version for t in tracks.installed(cfg)}
    for source, e in registry.available(args.source or cfg.sources):
        state = f"installed {installed[e['id']]}" if e["id"] in installed else "not installed"
        print(f"{e['id']:<18} {e['version']:<8} {e['language']}  {e['title']} "
              f"({e['sessions']} sessions; {state}) — {source}")
    return 0


def cmd_track_install(cfg, args):
    if args.from_:
        track = registry.install_from(cfg, args.from_, args.sha256)
    elif args.spec:
        track = registry.install(cfg, args.spec, args.source)
    else:
        return fail("give a track id (id or id@version) or --from PATH|URL")
    print(f"Installed {track.id} {track.version} ({track.language.name}) in {track.dir}")
    print(f"Start it with: lal start {track.id}")
    return 0


def cmd_track_remove(cfg, args):
    print(f"Removed {registry.remove(cfg, args.id)} (learner data kept)")
    return 0


def cmd_track_info(cfg, args):
    t = resolve_track(cfg, args.id)
    lang = t.language
    print(f"{t.title}\n  id {t.id}, version {t.version}, language {lang.name} ({t.language_code})")
    print(f"  source label: {t.source}\n  folder: {t.dir}")
    if t.description:
        print(f"  {t.description}")
    for s in t.sessions:
        parts = f" (parts {', '.join(s.parts)})" if s.parts else ""
        print(f"  Session {s.number} — {s.title}{parts}")
    return 0


def cmd_track_validate(cfg, args):
    status = 0
    for directory in args.dirs:
        errors = tracks.validate(directory)
        if errors:
            status = 1
            print(f"FAIL {directory}")
            for e in errors:
                print(f"  {e}")
        else:
            t = tracks.load(directory)
            print(f"OK   {directory}: {t.id} {t.version}, {t.language.name}, {len(t.sessions)} sessions")
    return status


def cmd_track_pack(cfg, args):
    for directory in args.dirs:
        print(registry.pack(directory, args.out))
    if args.index:
        print(registry.build_index(args.out))
    return 0


def cmd_track_index(cfg, args):
    print(registry.build_index(args.dist))
    return 0


def cmd_start(cfg, args):
    track = tracks.find(cfg, args.id)
    created = learner.start(cfg, track)
    print(f"Current track: {track.id} ({track.language.name}). Learner data: {cfg.data_dir}")
    for path in created:
        print(f"  created {path}")
    if any(p.name == "profile.toml" for p in created):
        print("Fill in profile.toml (your name and notes per language) before the first lesson.")
    return 0


def cmd_use(cfg, args):
    track = tracks.find(cfg, args.id)
    if not (learner.track_dir(cfg, track.id) / "TRACKER.md").is_file():
        return fail(f"{track.id} is not started yet: run `lal start {track.id}`")
    learner.set_current(cfg, track.id)
    print(f"Current track: {track.id} ({track.language.name})")
    return 0


def cmd_status(cfg, args):
    current = learner.current(cfg)
    print(f"Learner data: {cfg.data_dir}")
    print(f"Current track: {current or '(none)'}")
    for t in tracks.installed(cfg):
        tracker = learner.track_dir(cfg, t.id) / "TRACKER.md"
        sessions = learner.sessions_dir(cfg, t.id)
        lessons = sorted(p.name for p in sessions.iterdir()) if sessions.is_dir() else []
        state = f"{len(lessons)} lesson folder(s)" + (f", latest {lessons[-1]}" if lessons else "") \
            if tracker.is_file() else "not started"
        print(f"  {t.id:<18} {t.language_code}  {state}")
    return 0


def cmd_lesson_new(cfg, args):
    track = resolve_track(cfg, args.track)
    part = (args.part or "").upper()
    if args.stdout:
        print(lesson.skeleton(cfg, track, args.mode, args.session, part), end="")
        return 0
    out = lesson.write_skeleton(cfg, track, args.mode, args.session, part, args.date,
                                Path(args.out) if args.out else None)
    print(out)
    return 0


def cmd_lesson_check(cfg, args):
    errors, warnings, summary = lesson.check(cfg, args.path)
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"FAIL: {args.path}")
        return 1
    print(f"OK: {args.path} ({summary})")
    return 0


def cmd_lesson_refresh(cfg, args):
    lesson.refresh(cfg, args.path)
    print(f"Refreshed controller to prompt {lesson.prompt_version()}: {args.path}")
    return cmd_lesson_check(cfg, args)


def cmd_lesson_copy(cfg, args):
    lesson.copy(args.path)
    print(f"Copied to the clipboard: {args.path}")
    return 0


def cmd_audit(cfg, args):
    if args.language:
        lang = languages.builtin(args.language)
        if lang is None:
            return fail(f"no built-in language {args.language!r}")
    else:
        track = None
        text = args.files[0].read_text(encoding="utf-8")
        match = re.search(r"^Track: (\S+)", text, re.M)
        track = tracks.find(cfg, match.group(1)) if match else resolve_track(cfg, args.track)
        lang = track.language
    if not lang.checks:
        print(f"{lang.name} has no built-in checks.")
        return 0
    status = 0
    for name in lang.checks:
        print(f"== {name}: {checks.description(name)}")
        report, failed = checks.run(name, args.files)
        print("\n".join(report))
        status |= failed
    return int(status)


def cmd_prompt(cfg, args):
    track = resolve_track(cfg, args.track)
    print(lesson.controller(track, args.mode))
    return 0


def cmd_share(cfg, args):
    if not (args.url or args.html):
        return fail("give a share URL or --html")
    print(share.read(args.url, args.html, args.package_out))
    return 0


# --- parser -----------------------------------------------------------------

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lal", description=__doc__)
    p.add_argument("--version", action="version", version=f"lal {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("paths", help="show where tracks and learner data live").set_defaults(fn=cmd_paths)
    sub.add_parser("languages", help="list language profiles").set_defaults(fn=cmd_languages)

    tr = sub.add_parser("track", help="install, inspect and publish tracks")
    ts = tr.add_subparsers(dest="track_command", required=True)
    ts.add_parser("list", help="installed tracks (* = current)").set_defaults(fn=cmd_track_list)
    a = ts.add_parser("available", help="tracks offered by the sources")
    a.add_argument("--source", action="append", help="owner/repo[@tag], index URL or folder (repeatable)")
    a.set_defaults(fn=cmd_track_available)
    i = ts.add_parser("install", help="install ID[@VERSION] from a release, or --from a folder/archive")
    i.add_argument("spec", nargs="?")
    i.add_argument("--source", action="append", help="owner/repo[@tag], index URL or folder (repeatable)")
    i.add_argument("--from", dest="from_", metavar="PATH|URL", help="a track folder or .tar.gz")
    i.add_argument("--sha256", help="expected SHA-256 of a --from archive")
    i.set_defaults(fn=cmd_track_install)
    r = ts.add_parser("remove", help="uninstall a track (learner data is kept)")
    r.add_argument("id")
    r.set_defaults(fn=cmd_track_remove)
    n = ts.add_parser("info", help="describe a track (default: the current one)")
    n.add_argument("id", nargs="?")
    n.set_defaults(fn=cmd_track_info)
    v = ts.add_parser("validate", help="validate track folders")
    v.add_argument("dirs", nargs="+", type=Path)
    v.set_defaults(fn=cmd_track_validate)
    k = ts.add_parser("pack", help="build release archives from track folders")
    k.add_argument("dirs", nargs="+", type=Path)
    k.add_argument("--out", type=Path, default=Path("dist"))
    k.add_argument("--index", action="store_true", help="also write tracks-index.json")
    k.set_defaults(fn=cmd_track_pack)
    x = ts.add_parser("index", help="write tracks-index.json for a folder of archives")
    x.add_argument("dist", type=Path)
    x.set_defaults(fn=cmd_track_index)

    s = sub.add_parser("start", help="start a track: create learner data and make it current")
    s.add_argument("id")
    s.set_defaults(fn=cmd_start)
    u = sub.add_parser("use", help="switch the current track")
    u.add_argument("id")
    u.set_defaults(fn=cmd_use)
    sub.add_parser("status", help="tracks and lessons in the learner data").set_defaults(fn=cmd_status)

    le = sub.add_parser("lesson", help="build and check lesson packages")
    ls = le.add_subparsers(dest="lesson_command", required=True)
    nw = ls.add_parser("new", help="write a package skeleton")
    nw.add_argument("--mode", choices=sorted(lesson.MODES), required=True)
    nw.add_argument("--session", type=int, required=True)
    nw.add_argument("--part", default="", help="lesson part letter (required for guided)")
    nw.add_argument("--track", help="track id (default: current)")
    nw.add_argument("--date", default=dt.date.today().isoformat())
    nw.add_argument("--out")
    nw.add_argument("--stdout", action="store_true", help="print instead of writing files")
    nw.set_defaults(fn=cmd_lesson_new)
    for name, fn, helptext in (("check", cmd_lesson_check, "validate a filled package"),
                               ("refresh", cmd_lesson_refresh, "swap in the current controller, then check"),
                               ("copy", cmd_lesson_copy, "copy a package to the clipboard")):
        c = ls.add_parser(name, help=helptext)
        c.add_argument("path", type=Path)
        c.set_defaults(fn=fn)

    au = sub.add_parser("audit", help="run the language's built-in checks on files")
    au.add_argument("files", nargs="+", type=Path)
    au.add_argument("--track", help="take the language from this track (default: package's or current)")
    au.add_argument("--language", help="a built-in language code instead of a track")
    au.set_defaults(fn=cmd_audit)

    pr = sub.add_parser("prompt", help="print the controller for a track and mode")
    pr.add_argument("--mode", choices=sorted(lesson.MODES), required=True)
    pr.add_argument("--track")
    pr.set_defaults(fn=cmd_prompt)

    sh = sub.add_parser("share", help="read a ChatGPT share link as a transcript")
    sh.add_argument("url", nargs="?")
    sh.add_argument("--html", type=Path, help="a saved share page instead of fetching")
    sh.add_argument("--package-out", type=Path, help="write the pasted package to this file")
    sh.set_defaults(fn=cmd_share)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    cfg = config.load()
    try:
        return args.fn(cfg, args)
    except (LookupError, ValueError, FileExistsError, RuntimeError, OSError) as error:
        return fail(str(error))


if __name__ == "__main__":
    sys.exit(main())
