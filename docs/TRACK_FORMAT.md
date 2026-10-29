# Track format

A track is a folder of Markdown and TOML that teaches one language through
short one-mode lessons, in voice or typed. It carries no code: only `.md`, `.toml`,
`.json` and `.txt` files are accepted, and symbolic links are refused.

```
<id>/
  track.toml     metadata and sessions
  README.md      what the track is for; track-specific rules
  OPENINGS.md    per session: teacher introduction + listen-and-repeat lines
  MATERIAL.md    the learner's preparation material, per session
  PLAN.md        lesson parts and coverage criteria, per session
  TRACKER.md     empty progress tracker, copied by `lal start`
  language.toml  optional: a language profile (when the engine has none)
```

## track.toml

```toml
id = "es-travel"                 # lowercase letters, digits, hyphens; usually <lang>-<name>
version = "1.0.0"                # MAJOR.MINOR.PATCH; bump on every content change
language = "es"                  # a language profile code
title = "Spanish for a first trip"
description = "One or two sentences for `lal track available`."
source = "Spanish travel"        # label in practice-history and queue entries
learner_context = "a beginner preparing for a first trip to Spain"
                                 # ends the teacher's ROLE sentence: "... one adult learner who is <this>."

[phrases]                        # optional: override classroom phrases of the profile
repeat_please = "Repite, por favor."

[[sessions]]
number = 1                       # any integers; packages are named after them
title = "Greetings and getting by"   # must equal the OPENINGS.md heading
parts = ["A", "B"]               # guided lessons need one of these
focus = ["vocabulary", "grammar"]  # optional: phonetics, vocabulary, grammar, conversation, writing
```

`focus` says what a session concentrates on. `lal companion` shows it, and the
prepare workflow suggests modes from it: phonetics → repetition (minimal
pairs, stress), vocabulary → vocabulary drill, grammar → grammar drill,
conversation → guided and free, writing → writing.

`PLAN.md` may describe sessions that are not written yet (no `[[sessions]]`
entry, no OPENINGS or MATERIAL section): the companion lists them as
planned, so a long series can be published in blocks.

Overridable phrases: `start`, `close`, `english_please`, `repeat_please`,
`go_on`, `stop`, `listen_repeat`, `now_you`, `correction`.

## OPENINGS.md

Parsed by `lal`; keep the shape exactly:

```markdown
# Session 1 — Greetings and getting by

## Teacher introduction

> One to three sentences in the target language, as a blockquote.

## Opening review

- One line to listen to and repeat.
- …
```

Sessions are separated by `---`. A repetition lesson uses the opening lines
as its Lines; a guided lesson starts with the introduction. Lines are copied
into packages verbatim and `lal lesson check` refuses altered copies.

## MATERIAL.md and PLAN.md

`MATERIAL.md` needs a `# Session N — Title` section per session (dialogues
with translations, patterns, a "You should be able to" list work well).
Optional subsections feed the experimental modes, and the agent fills those
packages from them: `## Grammar — <pattern>` (a short explanation, a table of
forms, and **Drill ideas** as `cue → answer` examples), `## Vocabulary`
(`- word — meaning` lines), and `## Writing` (a task with a sentence count
and a follow-up). Without them the agent works from the dialogues and
patterns. `sv-everyday`, `pl-first-steps`, `ja-first-steps` and
`uk-advanced` show the shape.
`PLAN.md` says, per session, what each part (A, B, …) practises, optionally
which **Drills** suit it, and when the session counts as **Covered** (its
topic areas have appeared in transcripts of any mode; not mastery).

## Language profiles

Built-in profiles are in `src/lal/languages/<code>.toml` and may name
built-in checks (`uk_stress`, `es_punctuation`). A track for another
language bundles `language.toml` with the same keys:

```toml
code = "it"
name = "Italian"
native_name = "Italiano"
start = "Cominciamo"
close = "La lezione è finita."
english_please = "In inglese, per favore"
praise = ["Bravo", "Benissimo", "Perfetto", "Ottimo"]
ack = ["Sì.", "Bene."]
repeat_please = "Ripeta, per favore."
go_on = "Continui."
stop = "Finiamo"
listen_repeat = "Ascolti e ripeta."
now_you = "Ora provi lei."
correction = "Correzione:"
interference = ""     # e.g. "a Russian word" for Ukrainian
stress_rule = ""      # a voice-teacher rule about how the brief writes the language
                      # (Ukrainian stress marks, Japanese kanji readings)
text_rule = ""        # the same for text lessons (Polish diacritics, Japanese furigana)
```

A bundled profile supplies phrases only; its `checks` are ignored.
