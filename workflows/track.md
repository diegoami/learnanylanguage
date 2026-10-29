# Workflow: choose, install, write and publish tracks

## Choose and install

- `lal track available` lists what the configured sources publish (default
  source: this repository's latest GitHub release). `--source owner/repo`,
  `--source owner/repo@TAG`, an index URL or a local `dist/` folder adds
  others; `sources = [...]` in `lal.toml` makes them permanent.
- `lal track install <id>` (or `<id>@<version>`) downloads the archive,
  checks its SHA-256 against the index, unpacks it safely, validates it, and
  installs it into the tracks folder. `lal track install --from <folder |
  .tar.gz | URL>` installs one track directly.
- `lal start <id>` creates the learner data for it and makes it current;
  `lal use <id>` switches between started tracks; `lal status` shows them.
- `lal track remove <id>` uninstalls the track and keeps the learner data.

## Write a track

1. Copy the closest track in `tracks/` to `tracks/<lang>-<name>/` and follow
   [`docs/TRACK_FORMAT.md`](../docs/TRACK_FORMAT.md). All teaching material
   must be original: no transcripts of commercial courses.
2. For a language without a built-in profile, either add
   `src/lal/languages/<code>.toml` (engine change: classroom phrases plus any
   checks) or bundle a `language.toml` with the track (phrases only).
3. `lal track validate tracks/<id>`, then try it without installing:
   `LAL_TRACK_PATH=tracks lal lesson new --track <id> --mode repetition
   --session 1 --stdout`. Run `lal audit` on its `OPENINGS.md` and
   `MATERIAL.md`.
4. `uv run pytest` (every folder in `tracks/` is validated by the tests).

## Publish

Tracks are published as GitHub release assets: one `<id>-<version>.tar.gz`
per track plus `tracks-index.json`. Bump `version` in `track.toml` whenever a
track's content changes. Then push a tag `tracks-YYYY.MM.DD` (ask the owner
first: a release is public). `.github/workflows/release-tracks.yml` validates
and packs every track, writes the index, and creates the release; because
installs read `releases/latest/download/tracks-index.json`, every release
carries all tracks. Locally the same is
`lal track pack tracks/* --out dist --index`.

A third party publishes tracks the same way from their own repository; users
add it as a source.
