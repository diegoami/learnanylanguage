# learnanylanguage

Short lessons in any language: a coding agent prepares a self-contained
lesson package, **ChatGPT** teaches it (in Voice, or in a typed chat), and the
agent records the raw conversation as evidence of what was practised.

This generalises the Ukrainian practice in
[`diegoami/learnukrainian`](https://github.com/diegoami/learnukrainian):

- **Pluggable tracks.** Lesson content comes in data-only *tracks*
  (Markdown + TOML), published as GitHub release assets and installed with
  `lal track install`. Anyone can publish tracks from their own repository.
- **Any language.** The teacher prompt is a template; a *language profile*
  supplies the classroom phrases («Почнімо» / «Empecemos», «Виправлення:» /
  «Corrección:», …) and enables language-specific checks.
- **Learner data apart.** Profile, trackers, transcripts and review queues
  live in their own folder (ideally a private repository), never in the
  tracks or the engine.

## Tracks in this repository

| Track | Language | Sessions | |
| --- | --- | --- | --- |
| [`uk-reactivation`](tracks/uk-reactivation/) | Ukrainian | 7 | Reactivation after a Pimsleur-style Level 1; ported from learnukrainian with verified stress marks |
| [`es-travel`](tracks/es-travel/) | Spanish | 3 | A first trip: greetings, café and paying, directions and transport (usted) |
| [`es-smalltalk`](tracks/es-smalltalk/) | Spanish | 2 | Informal chat with friends: yourself and your likes, the weekend and plans (tú) |
| [`uk-elementary`](tracks/uk-elementary/) | Ukrainian | 6 of 27 | A1–A2 following the topic map of Є-мова's «Українська за 27 уроків»: phonetics, then one vocabulary theme and one grammar point per session (sessions 7–27 planned) |
| [`uk-advanced`](tracks/uk-advanced/) | Ukrainian | 3 | Towards an advanced level: opinions and polite disagreement, telling a story (aspect), news and society (-но/-то forms) |
| [`sv-everyday`](tracks/sv-everyday/) | Swedish | 3 | Everyday Swedish (du): introductions, fika and likes, the weekend and plans |
| [`pl-first-steps`](tracks/pl-first-steps/) | Polish | 3 | A first stay in Poland (pan/pani): introductions, café and paying, directions and transport |
| [`ja-first-steps`](tracks/ja-first-steps/) | Japanese | 3 | Polite everyday Japanese (です／ます): introductions, shopping and ordering, time and plans |

Tracks of one language share one review queue (the two Spanish tracks; the
two Ukrainian ones); `es-smalltalk` overrides the Spanish profile's classroom
phrases to stay informal. The four newest tracks have **Grammar**,
**Vocabulary** and **Writing** sections per session for the experimental
modes below.

## Lesson modes

Every lesson has exactly one mode and lasts about 5–10 minutes.

| Mode | Channel | What happens |
| --- | --- | --- |
| `repetition` | voice | listen and repeat the session's opening lines, then a short recall pass |
| `guided` | voice | one role-play for one lesson part, 4–6 target expressions |
| `free` | voice | open conversation on the session topic, light recasts only |
| `grammar` *(experimental)* | voice or text | one pattern, 6–10 cue → answer items, one-chunk corrections, a repeat pass |
| `vocabulary` *(experimental)* | voice or text | 6–10 words found from prompts, each used in a sentence, a repeat pass |
| `writing` *(experimental)* | text | write a short text, get a minimal rewrite with reasoned corrections, do a follow-up |

The experimental modes end with an optional **report**: after the closing
sentence, type `REPORT` in the same chat and the teacher writes a factual
`LESSON_REPORT` (items reached independently, after a cue or corrected; the
corrections; words it gave). No scores or assessment. `lal report` checks it
and turns it into tracker rows, and the record workflow verifies every line
against the transcript, which stays the evidence.

## Quick start

```bash
uv tool install git+https://github.com/diegoami/learnanylanguage   # or: uv sync && uv run lal ...

lal track available                # what the latest release offers
lal track install es-travel        # download, verify SHA-256, validate, install
lal start es-travel                # create learner data, make it the current track
$EDITOR "$(lal paths | sed -n 's/^learner data: //p')/profile.toml"

lal lesson new --mode repetition --session 1   # skeleton in the learner data
lal lesson new --mode grammar --session 1 --channel text   # an experimental typed drill
# ... fill the <<FILL>> fields (or let your coding agent do it: workflows/prepare.md)
lal lesson check <package.md> && lal audit <package.md> && lal lesson copy <package.md>
```

Then: new ChatGPT chat → paste → send → it answers only that it is ready →
start voice and say the start command (text lessons: type it). Afterwards share the chat and give
the link to the agent (`lal share <link>` reads it; see
[workflows/record.md](workflows/record.md)).

Switch language or track at any time: `lal start uk-reactivation`,
`lal use es-travel`, `lal status`.

## Commands

| Command | Does |
| --- | --- |
| `lal paths` | config file, tracks folder, learner data, sources |
| `lal languages` | language profiles, their checks and installed tracks |
| `lal track available / install / list / info / remove` | find and manage tracks |
| `lal track validate / pack / index` | check and publish tracks |
| `lal start ID` / `lal use ID` / `lal status` | choose the current track |
| `lal lesson new / check / refresh / copy` | build and check packages (`--channel voice\|text`) |
| `lal audit FILE...` | the language's checks (Ukrainian stress, Spanish ¿…?) |
| `lal prompt --mode M [--channel C] [--track ID]` | show the rendered teacher controller |
| `lal share URL` | read a ChatGPT share link as a transcript |
| `lal report FILE` | check a LESSON_REPORT and print it with evidence labels |
| `lal gui [--data DIR\|GIT_URL]` | read and evaluate progress in a local web page |
| `lal web` | run lessons in a local page: hand-off to ChatGPT, or your own keys |
| `lal companion` | write `COMPANION.md`: what was covered, each lesson's transcript, what comes next |
| `lal open [companion\|tracker\|queue\|profile\|data\|FILE]` | open it in your editor (`editor = "code"` in `lal.toml`) |

Configuration: `lal.toml` (see [lal.example.toml](lal.example.toml)) or
`LAL_HOME`, `LAL_DATA`, `LAL_TRACK_PATH`, `LAL_CONFIG`.

## Layout

```
src/lal/              engine: CLI, controller template, profiles, checks
  prompt/CONTROLLER.md   the teacher prompt template (version g3)
  languages/*.toml       language profiles (uk, es, sv, pl, ja)
  checks/                built-in checks (uk_stress, es_punctuation)
tracks/<id>/          track sources, released as <id>-<version>.tar.gz
workflows/            prepare, record, iterate, track: for any coding agent
prompt/ITERATIONS.md  adherence checklist and prompt version history
docs/TRACK_FORMAT.md  how to write a track (and a profile for a new language)
```

Learner data (`lal paths`):

```
profile.toml  state.toml  teacher-runs.md
queues/<lang>.md                  shared by every track of a language
tracks/<id>/TRACKER.md
tracks/<id>/sessions/<date>-session-<N><part>-<mode>/{package,transcript}.md
```

## Running lessons in `lal web`

`lal web` opens a local page (on `127.0.0.1`, so no tunnel) that lists the
prepared lessons in your learner data and runs one with the teacher you
choose:

- **ChatGPT**: the page copies the package; you paste it into ChatGPT (Voice
  or typed), share the chat, and paste the share link back. `lal` reads it
  and writes the transcript into the lesson folder.
- **Your own keys, typed**: OpenRouter or Gemini answers in the page.
- **Your own keys, voice**: tap to talk; ElevenLabs Scribe hears you (locked
  to the lesson's language), OpenRouter or Gemini answers, ElevenLabs
  Multilingual v2 speaks (with the brief's stress marks).

Keys are entered in the page's Settings, kept in that browser only, and sent
only to their provider; the `lal` server never sees them. Transcripts are
written in the format `lal share` produces, so recording works unchanged.
Why these teachers, and what was left out: [docs/teachers.md](docs/teachers.md).

## The companion

`lal companion` writes `COMPANION.md` into the learner data: per started
track, where you are (sessions, their focus, status, next), every lesson
with what it practised and a link to its transcript (or how to supply a
missing one), the sessions coming next with their "you should be able to"
lists, sessions planned but not yet written, and the review queue. It does
not depend on the route a lesson took; the prepare and record workflows
and `lal web` regenerate it, and `lal web` shows it in its Companion tab.
Every lesson keeps its full transcript in its folder: a ChatGPT share link,
a pasted conversation, or the page's own record.

For Japanese, `romanization = true` under `[languages.ja]` in `profile.toml`
adds romaji: typed packages ask the teacher for it after each sentence, and
`lal web` shows it under each turn (own keys; never spoken, never in the
transcript). Voice packages stay script-only.

Neither page edits files: their viewers have **Open in editor**, which
starts the application set as `editor` in `lal.toml` (for example `editor =
"code"` for VS Code; `$LAL_EDITOR` works too), or the system's opener when
none is set. `lal open companion` does the same from the terminal.

Sessions can carry a `focus` (phonetics, vocabulary, grammar, conversation,
writing) that suggests their modes; see [docs/TRACK_FORMAT.md](docs/TRACK_FORMAT.md).

## Reading your progress

`lal gui` opens a local, read-only page over the learner data: sessions
covered per track, recorded lessons per week, evidence labels, review-queue
status, the teacher's failed checks per prompt version, and the git history;
any tracker, package or transcript opens in a reader. `--data` reads another
directory or a git URL (cloned once, pulled with `--pull`). The learner data
also opens as an Obsidian vault. Why a folder in a private git repository,
and not Notion or a database: [docs/backends.md](docs/backends.md).

## Publishing tracks

Push a tag `tracks-YYYY.MM.DD`; [the release workflow](.github/workflows/release-tracks.yml)
tests, validates and packs every track and attaches the archives and
`tracks-index.json` to a GitHub release. See [workflows/track.md](workflows/track.md).

## Development

```bash
uv sync
uv run pytest
LAL_TRACK_PATH=tracks uv run lal track list     # use tracks/ without installing
```
