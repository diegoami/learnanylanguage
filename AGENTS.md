# learnanylanguage

Short lessons in any language, taught by ChatGPT (Voice, or an ordinary
typed chat) from a self-contained package that a coding agent prepares and
later records. It generalises `diegoami/learnukrainian` (pimsleur-review): the engine is
language-neutral, the content comes in pluggable **tracks**, and each
language plugs in through a **language profile**.

This repository is model-agnostic: it is maintained with any coding agent.
`AGENTS.md` is authoritative; `CLAUDE.md` only imports it, and
`.claude/skills/` only point to the workflows.

## Three layers, kept apart

| Layer | Where | What |
| --- | --- | --- |
| Engine | `src/lal/` (CLI `lal`) | controller template, package builder and checker, track registry, language profiles and checks, the read-only progress page (`lal gui`) |
| Tracks | `tracks/<id>/` here (source); installed copies in the tracks folder | data-only lesson content for one language: `track.toml`, `OPENINGS.md`, `MATERIAL.md`, `PLAN.md`, `TRACKER.md`, `README.md` |
| Learner data | `$LAL_DATA` / `data_dir` (`lal paths`) | profile, per-track trackers and lesson folders, per-language review queues, teacher runs |

- Never write learner progress, transcripts or personal data into this
  repository; they belong in the learner data (git-ignored here as
  `learner/`).
- Never put code in a track. Checks are engine code in `src/lal/checks/`,
  enabled by a language profile.
- Tracks are published as GitHub release assets
  ([workflows/track.md](workflows/track.md)) and installed with
  `lal track install`. Creating a release is public: ask the owner first.

## Roles

- **The coding agent** prepares each lesson package and records the finished
  conversation, editing the learner data and running `lal`.
- **ChatGPT teaches** from the pasted package, in ChatGPT Voice or, for
  text lessons, in a typed chat. It has no repository access; never tell the
  user it can read or update anything.

The chat must not create scores, assessments, or tracker updates; the agent
extracts practice from the raw conversation. One experimental exception: in
the grammar, vocabulary and writing modes the learner may ask for a factual
`LESSON_REPORT` after the close. It is a hint that the agent checks line by
line against the transcript (`lal report`); the transcript stays the
evidence, and a report line it does not support is dropped.

## One lesson, one mode

Every lesson lasts about 5–10 minutes (writing up to 15) and has exactly
one mode:

- In voice: **repetition** (listen-and-repeat of a session's opening lines,
  then a short recall pass), **guided conversation** (one role-play for one
  lesson part, 4–6 target expressions, at most 10 steps), or **free
  conversation** (open conversation on the session topic, no targets, no
  drills).
- Experimental since prompt g3, ending with the optional report:
  **grammar drill** (one pattern, 6–10 cue → answer items; voice or text),
  **vocabulary drill** (6–10 words recalled from prompts and used in a
  sentence; voice or text), and **writing** (one short text, corrected, and
  a follow-up; text only).

Never combine modes or extend a lesson; a session is worked through as
several lessons.

## Workflows

Plain Markdown procedures; follow them step by step.

- [workflows/prepare.md](workflows/prepare.md): prepare the next lesson.
- [workflows/record.md](workflows/record.md): record a finished lesson.
- [workflows/iterate.md](workflows/iterate.md): revise the teacher prompt.
- [workflows/track.md](workflows/track.md): choose, install, write and
  publish tracks.

Claude Code exposes them as `/lesson-prepare`, `/lesson-record`,
`/lesson-iterate` and `/track`.

## Scope rules

- Work only in the track the user names (or the current one), plus the
  language's shared queue when that track produces or practises a queued
  item. Ask when a request is ambiguous about the track.
- Tracks of the same language share one queue
  (`<data>/queues/<lang>.md`); keep every entry's original track and lesson
  and every later practice source visible. Never move vocabulary, history or
  progress between tracks.
- Progress means exposure and transcript coverage, not mastery. Record only
  transcript-observable evidence; never score and never infer pronunciation
  from transcripts. Speech-recognition errors are not learner errors.
- Preserve information: retire queue entries without deleting their history;
  avoid aggressive deduplication.
- Each track's `README.md` can add rules for that track (for example,
  Ukrainian stress marks); follow them when working in it.

## Engine changes

- Change the controller only between the block markers in
  `src/lal/prompt/CONTROLLER.md`, bump its **Prompt version** in both places,
  and log the change in `prompt/ITERATIONS.md`. Language-specific wording
  belongs in placeholders filled from language profiles.
- Run `uv run pytest` before committing. The tests validate every track in
  `tracks/` and pin the Ukrainian rendering of the repetition, guided and
  free modes to learnukrainian's g2.
- Python ≥ 3.12, standard library only at runtime; `uv` for the environment.

## Git and reviews

Engine and track changes: commit on `main` unless the owner asks for a
branch. Learner data has its own repository, if any.

No automatic reviews: never start a reviewer on your own. Reviews happen
only at milestones, through a milestone PR that the owner has a model of
their choice review: [docs/milestone-review.md](docs/milestone-review.md).
