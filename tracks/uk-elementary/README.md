# Ukrainian A1–A2 in 27 topics (uk-elementary)

An elementary Ukrainian series that covers what the free A1–A2 course of
**Є-мова** covers: «Українська за 27 уроків» (Ukrainian in 27 lessons, by
the Є-мова project and the volunteer initiative «Безкоштовні курси
української мови», hosted on Prometheus). Its topic map is followed session
for session, with the same numbering: three phonetics sessions (alphabet,
vowels, consonants), then 24 everyday themes, each with **one vocabulary
set and one grammar point**. Every dialogue, explanation, list and drill
here is **original**; nothing is copied from the course. Work through it
alongside the course, or on its own.

The series is published in blocks. Sessions 1–6 are written; sessions 7–27
are planned in [PLAN.md](PLAN.md) (topic, vocabulary and grammar) and are
listed as *planned* by `lal companion`.

- [MATERIAL.md](MATERIAL.md): per session, the explanation, a dialogue,
  **Vocabulary**, **Grammar** and **Writing** sections, and a "You should be
  able to" list.
- [PLAN.md](PLAN.md): all 27 sessions, their parts, suggested modes and
  when a session counts as covered.
- [OPENINGS.md](OPENINGS.md): the stress-marked teacher introductions and
  listen-and-repeat lines.
- [TRACKER.md](TRACKER.md): the empty tracker that `lal start` copies.

## Modules

Each session in `track.toml` has a `focus`: **phonetics**, **vocabulary**,
**grammar**, **conversation**. The prepare workflow suggests modes from it:

| Focus | Lessons | What happens |
| --- | --- | --- |
| phonetics | repetition | listen and repeat sounds, minimal pairs (кит — кіт) and stress pairs (за́мок — замо́к) |
| vocabulary | vocabulary drill, repetition | recall the session's words from prompts, use each in a sentence |
| grammar | grammar drill, writing | one pattern, transformation items, then a short text |
| conversation | guided, free | the session's situation as a role-play, then open talk |

## Track-specific rules

- Everything Ukrainian here carries **stress marks**, checked with `lal
  audit` (goroh.pp.ua, СУМ-20). Keep them in packages; add new ones only
  when certain. After a preposition the pronoun keeps the forward stress
  (`у те́бе`, `у ме́не`).
- **Phonetics lessons never judge pronunciation**: the transcript cannot
  show it. They give exposure and repetition; the tracker records what was
  repeated. In `lal web` with own keys, ElevenLabs speaks the marked lines
  with their stress, which suits the stress sessions.
- Opening lines use masculine forms where a form depends on the speaker;
  the material gives the feminine form too.
