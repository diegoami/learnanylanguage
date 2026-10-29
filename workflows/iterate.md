# Workflow: iterate the voice-teacher prompt

Use when the user wants to improve how the ChatGPT teacher behaves (voice or text).
The controller is shared by every language and track, so a change is an
engine change in this repository.

Input (optional): a specific teacher problem to address.

1. **Read the evidence.** `prompt/ITERATIONS.md` (checklist, versions), the
   blocks in `src/lal/prompt/CONTROLLER.md`, `teacher-runs.md` in the learner
   data, and the transcripts of the runs for the current version.
2. **Choose what to fix.** The problem the user named; otherwise the one or
   two failed checks that recur most or hurt most for the current version.
   With no runs and no named problem, stop: a test lesson comes first.
3. **Diagnose from the turns.** Vague or buried wording, a conflicting rule,
   a missing example, a brief that invited the behaviour, a rule in the wrong
   block, a language-specific phrase that belongs in the language profile or
   in a track's `[phrases]`, or a speech-recognition effect no prompt can fix.
   If the cause is a setting, a brief or a profile, change that instead.
4. **Edit the blocks** only between their markers; the smallest change, in
   the affected MODE block where possible. Anything language-specific goes
   into a `{{placeholder}}` filled from `src/lal/languages/<code>.toml`
   (add the key to every built-in profile). Never add scoring, summaries,
   tracker output or repository-access claims; the only report is the
   factual LESSON_REPORT of CLOSE report, and it must stay free of scores.
5. **Bump the version** (gN → gN+1) in the file header and in COMMON.
6. **Log it** in `prompt/ITERATIONS.md` → **Versions**: date, changes, modes,
   checks and languages targeted, hypothesis, what to watch, how to roll back.
7. **Test.** `uv run pytest`. The Ukrainian equivalence test pins the
   repetition, guided and free blocks to g2 (apart from the version line);
   when a change to them is deliberate, update `tests/fixtures/` to the new
   expected text in the same commit.
8. **Refresh unused packages** in the learner data: for every lesson folder
   whose transcript is still only the template, `lal lesson refresh
   <package.md>`.
9. **Commit** as `Voice teacher prompt gN+1: <summary>`. Report the change,
   the hypothesis, and what to listen for in the next lesson in each language.
