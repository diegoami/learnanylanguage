# Workflow: record a finished lesson

Use when the user shares a finished ChatGPT lesson, voice or text (a share
link, a pasted conversation, or a folder). `<data>` is the learner data folder
(`lal paths`). The package's `Track:` line names the track.

Input (optional): a share link, a lesson folder, or a transcript path.
Default: the newest folder of the current track.

If `lal web` ran the lesson, the transcript is already in the folder: with a
`Share link:` line (ChatGPT; the page saved the share-page package as
`shared-package.md` for the comparison below) or with a header naming the
teacher and models (own keys). Use it as the raw transcript and go to step
1b. In the teacher-runs row, write the teacher and model in the Model column
(e.g. `own keys, voice: google/gemini-3.8-flash`); in voice lessons with own
keys, the learner's turns are ElevenLabs Scribe's recognition.

## 1. Get the raw transcript

- **Share link** (`https://chatgpt.com/share/...`):
  `lal share <link> --package-out <temp dir>/pasted.md`. It prints every
  message in order, marked `(voice)` or `(text)`, with ChatGPT's transcription
  of each voice turn, and saves the package that was pasted. Compare it with
  the folder's `package.md`; if a different one was pasted, replace
  `package.md` with it and say so in the transcript header. Put the output
  below the transcript's `---` line unchanged, and note the share URL, the
  time span and the models from its first line.
- **Pasted conversation:** long pastes into a terminal have lost turns
  before. Check that it starts with the ready reply and the start command and
  has no two teacher turns or big gaps in a row; if anything looks missing,
  ask for the share link.
- **Path given:** use that folder or file.

If the transcript is still only the template, stop and ask for the
conversation. Never tidy, translate, or correct the transcript.

Learner turns come from speech recognition: a garbled or implausible turn is
a recognition problem, not a learner error. When a turn is plausibly
misrecognised, say so instead of recording a correction. Typed turns (text
lessons) are the learner's own: spelling there is learner evidence.

## 1b. The LESSON_REPORT (grammar, vocabulary, writing; optional)

If the learner typed `REPORT` after the close, the transcript ends with a
LESSON_REPORT. Run `lal report <transcript.md>`: it checks the format, flags
scores, levels, praise and pronunciation (a C23 failure), and prints the
items with the tracker's evidence labels (independent → **independent**,
after a cue → **cued**, corrected → **corrected and repeated** only if the
transcript shows the repetition).

Treat every line as a claim to verify: find the turns it describes. Keep the
lines the transcript supports, correct the ones it contradicts, drop the
ones it does not show, and record anything the report missed. Never record
from the report alone. Note in the teacher-runs row how many report lines
were wrong or missing (C23); that number decides whether the report is worth
keeping (see g3 in `prompt/ITERATIONS.md`).

## 2. Learner record

In `<data>/tracks/<id>/TRACKER.md` and `<data>/queues/<lang>.md`:

- Record only vocabulary encountered and sentences or patterns practised. No
  scores for comprehension, recall, grammar or pronunciation, and no
  pronunciation targets inferred from spelling.
- Evidence per item: **modelled**, **repeated**, **cued** (used with a cue),
  **independent**, **corrected and repeated**. Typically: repetition lines
  *repeated*, recall answers *independent* when produced before the model;
  guided steps per step; free conversation what the learner *used
  independently* and the teacher's recasts (*modelled*); grammar Items and
  vocabulary words per item; writing: the patterns the learner used
  correctly (*independent*) and each correction (attempt → preferred form →
  reason), *corrected and repeated* only if the follow-up reused it.
- Preserve every useful attempt → preferred form → reason the transcript
  supports.
- Add a dated **Practice history** entry with the line
  `Mode: <mode> (<voice | text>). Teacher: ChatGPT, prompt <gN> — sessions/<folder>/`,
  and a one-line process note if teacher behaviour limited coverage.
- Update **Current position**: the session's status and its **Next** column.
  A session is **Covered** once its planned topic areas (track `PLAN.md`)
  have appeared in the accumulated transcripts of any mode. Covered is not
  mastery and weak expressions never keep a session open.
- Add or update queue rows for expressions that need another turn, labelled
  with the track's source label and the lesson; add a repetition-history row
  when a queued target was practised, naming the track that practised it
  (it may differ from the one where the target arose).
- Preserve earlier evidence. Do not remove an item because it recurs.

## 3. Teacher adherence

Apply every check of the checklist in `prompt/ITERATIONS.md` that applies to
the lesson's mode to the teacher's turns, citing a few words of each failing
turn. Add one row to `<data>/teacher-runs.md` (date, track, lesson, mode,
prompt version, model, input mode, failed checks or `none`, notes including
audio notes from the test-settings block, folder).

## 4. Commit and report

Commit the transcript, tracker, queue and teacher-runs row together in the
learner data repository, e.g. `es-travel: record Session 2B guided lesson
(prompt g3)`. Report briefly: coverage change, new or updated queue targets,
failed checks, the suggested next lesson, and whether iterating the prompt
([iterate.md](iterate.md)) is worth it: recommend it when a check fails in a
way that affects the lesson, or fails in two runs.
