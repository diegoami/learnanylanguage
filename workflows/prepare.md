# Workflow: prepare the next lesson package

Use when the user asks to prepare their next lesson, in any language or
track, in voice or as a typed (text) lesson. Commands run from anywhere; `lal paths` shows where the tracks and the
learner data are. `<data>` below is the learner data folder.

Input (optional): a track id, a mode (`repetition`, `guided`, `free`, or the
experimental `grammar`, `vocabulary`, `writing`), a channel (`voice`, `text`)
and a session and part, e.g. `es-travel guided 2B` or `pl-first-steps grammar
2 text`.

1. **Choose the track.** The one the user names (switch with `lal use <id>`,
   or pass `--track`); otherwise the current track (`lal status`). If it is
   not installed, follow [track.md](track.md); if it is not started, run
   `lal start <id>` and ask the user to fill in `<data>/profile.toml` for the
   track's language before the first lesson.
2. **Choose the lesson.** Unless the user named it, read the **Current
   position** table and the latest **Practice history** entries in
   `<data>/tracks/<id>/TRACKER.md`, the existing folders in
   `<data>/tracks/<id>/sessions/`, and the language's queue
   `<data>/queues/<lang>.md`. Pick the earliest session that is not Covered
   and the mode and part in its **Next** column; the usual order is one
   repetition lesson, one guided lesson per part, then one free conversation.
   Grammar, vocabulary and writing lessons are extras the user asks for (or
   that the track's `PLAN.md` suggests under **Drills**); they need no part.
   Grammar and vocabulary run in voice by default; offer `text` when the user
   wants to practise spelling or script. Writing is always text.
   Read the track's `README.md` for track-specific rules (for example, a
   non-gating diagnostic session). If a folder for that lesson already exists
   with an empty transcript (only the template), reuse it (run `lal lesson
   refresh` on it if the prompt version changed) and skip to step 5.
3. **Skeleton.** `lal lesson new --mode <mode> --session N [--part X]
   [--channel voice|text] [--track <id>]` (`--part` is required for guided).
   It creates
   `<data>/tracks/<id>/sessions/<today>-session-<N><X>-<mode>[-text]/package.md` and
   a `transcript.md` template, copying the controller (rendered for the
   track's language), the introduction and the opening lines. Never retype
   those parts.
4. **Fill every `<<FILL: ...>>` field** from the session's targets in the
   track's `PLAN.md` and its section of `MATERIAL.md` (installed track folder:
   `lal track info`). Keep the track's conventions (for Ukrainian, stress
   marks only when certain).
   - **Repetition**
     - Extra Lines: at most two queued expressions that belong to this
       session, numbered after the opening lines; update `Lines (N)` and
       `Length`. Otherwise delete the placeholder line.
     - Recall prompts: 3–6 lines `- <prompt in the target language> → Line K`.
       A prompt names the situation or function, never the words of the Line.
   - **Guided conversation**
     - Active phrase set: 4–6 closely related expressions, one `- ` line each,
       from the session's material.
     - Guided steps: one situation sentence, then at most 10 numbered steps.
       Stage directions in English, every line the teacher says in the target
       language. Never write the learner's answer: describe it as an outcome
       the teacher waits for (`Wait for the learner to ask for two small
       bottles.`). A target-language sentence in a step is read as a line for
       the teacher to say. One changed detail per cycle; at most one
       changed-detail cycle.
   - **Free conversation**
     - Topic and Situation: one sentence each, from the session's topic.
     - Opening question: one open question in the target language.
     - Useful vocabulary: at most 12 `- ` lines from the session's material.
   - **Grammar drill** (experimental), from the session's **Grammar** section
     (or its patterns when the track has none):
     - Pattern: one English sentence for the teacher (what changes).
     - Instruction: one short target-language sentence for the learner.
     - Example and Items: `cue → answer`; 6–10 numbered Items, one change
       each, vocabulary from the session only. Write the full correct answer:
       the teacher needs it to correct, and the controller forbids saying it
       before the attempt. Vary the Items (person, number, a new noun) so
       that they cannot be answered by copying the previous one.
   - **Vocabulary drill** (experimental), from the session's **Vocabulary**
     section: 6–10 numbered `prompt → word` lines. A prompt is a short
     target-language definition, opposite or situation that only this word
     fits; at beginner level an English gloss is fine. Never put the word
     itself, or a word of the same root, in its prompt.
   - **Writing** (experimental, text), from the session's **Writing**
     section: the Task in the target language with a sentence count; at most
     8 Useful-language lines with meanings; a Focus in English (the
     session's grammar point); a one-sentence Follow-up task.
   - The new modes' packages carry a `Channel:` line; never edit it by hand:
     rebuild with the other `--channel` instead.
   - **Earlier weak expressions included** (all modes): `None`, or at most two
     `- ` lines from the language's queue that fit naturally, each with its
     original source and origin. A queue row may come from another track of
     the same language. In a guided package, mark the step where each fits.
   Use only vocabulary from the session's material, or give the meaning of
   anything new in the step where it appears. Do not copy full dialogues or
   model answers into a guided or free package: that defeats active recall.
5. **Check.** `lal lesson check <package.md>` and `lal audit <package.md>`
   (the language's built-in checks: Ukrainian stress against dictionaries,
   Spanish ¿…?/¡…! and accented question words; Swedish, Polish and Japanese
   have none yet). Fix every error. Do not hand over a package that fails
   either. For Japanese, also make sure no romaji or bracketed readings
   slipped into the brief.
6. **Clipboard.** `lal lesson copy <package.md>`. If no clipboard tool is
   available, tell the user to open the file and copy it. Never hand over the
   brief alone: the voice chat needs its instructions in the same paste.
7. **Commit** the lesson folder in the learner data repository, if it is
   one, with a message like `es-travel: prepare Session 2B guided package
   (prompt g3)`. Do not touch the tracker or the queue: a prepared package
   is not progress.
8. **Tell the user**, briefly: the folder, the mode, the channel and what it
   practises, any weak expressions included, whether the package is on the
   clipboard, and the next steps:
   1. New ordinary ChatGPT chat → paste → send → expect only the ready
      sentence.
   2. **Voice:** same chat, start voice → say the start command from the
      ready sentence (Ukrainian «Почні́мо», Spanish «Empecemos», Swedish
      «Nu börjar vi», Polish «Zaczynamy», Japanese «はじめましょう»). Speak
      only the target language. **Text:** type the start command instead,
      and answer by typing.
   3. Grammar, vocabulary and writing only: after the closing sentence, if
      the user wants a summary, end voice mode and type `REPORT` in the
      same chat. The teacher writes a LESSON_REPORT; it is optional and the
      transcript stays the evidence.
   4. Afterwards share the chat, copy the link, and hand it back to be
      recorded ([record.md](record.md)).

   Or run it in `lal web`: the page lists the prepared lesson, offers the
   same ChatGPT hand-off (and reads the share link itself), or runs it with
   the learner's own keys, typed or in voice, and saves the transcript into
   the lesson folder.
