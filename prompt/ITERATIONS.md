# Voice-teacher iterations

How each version of the controller in
[`src/lal/prompt/CONTROLLER.md`](../src/lal/prompt/CONTROLLER.md) behaves in
real lessons, in every language, so that versions are compared on evidence
rather than impression. **Teacher behaviour only**: learner progress stays in
each track's tracker in the learner data.

One prompt version serves every language and track. A change that helps the
Ukrainian teacher must not quietly break the Spanish one: when a version
changes COMMON or a MODE block, watch the next run in each language in use.

## How an iteration works

1. [`workflows/prepare.md`](../workflows/prepare.md) builds a package with the
   current version.
2. The lesson runs in ChatGPT Voice (or as a typed dry run).
3. [`workflows/record.md`](../workflows/record.md) records the learner's
   practice **and** adds one row to `teacher-runs.md` in the learner data,
   applying this checklist to the teacher's turns.
4. [`workflows/iterate.md`](../workflows/iterate.md) reads the failed checks
   across recent runs (all languages), changes the controller for at most one
   or two failure types, bumps the version, and adds a **Versions** entry here
   stating the hypothesis.
5. The next lessons in the affected modes test it. Keep the change if its
   target checks pass; otherwise revise or revert it.

Settings (voice language, input mode, voice) are variables too: change them
one at a time and record them in the transcript's test-settings block.

## Adherence checklist

Each check is marked **pass**, **fail**, or **n/a** from the transcript alone,
for the modes listed (R = repetition, G = guided conversation, F = free
conversation). Cite the turn that shows a failure.

| ID | Modes | Check | Passes when |
| --- | --- | --- | --- |
| C1 | R G F | Waits on receipt | The reply to the package is only the ready sentence. |
| C2 | R G F | Starts on command | Teaching begins only after the start command, as the mode prescribes (R: the repeat cue and Line 1; G: the introduction and step 1; F: the opening question). |
| C3 | R | Full opening | Every Line is presented, in order, with none skipped or merged. |
| C4 | R | One line per turn | During the Lines each teacher turn is only the next Line (plus a single re-say when meaning was lost). |
| C5 | R G F | No routine praise | No praise, thanks, or evaluation after routine repetitions or answers. |
| C6 | G F | Scope | G: practice stays within the active phrase set (≤ 6) and listed weak expressions (≤ 2). F: the conversation stays on the topic and the learner's level. No unprepared vocabulary without a meaning given first. |
| C7 | R G F | Short turns | Teacher turns are one or two sentences with at most one question. |
| C8 | G | Correction routine | Important errors get the profile's correction marker (uk «Виправлення:», es «Corrección:»), chunk repetition, full sentence, and later reuse with one changed detail; valid sentences that differ from the step are accepted. |
| C9 | R | Recall | Each recall prompt is asked without a model or cue before the learner's first attempt, and followed by its answer Line. |
| C10 | R G F | Target language first | English only when asked or after two failed explanations in the target language. |
| C11 | R G F | Voice formatting | No markdown, lists, emoji, labels, or spoken line or step numbers. |
| C12 | R G F | Clean close | The closing sentence is used; no summary, scores, or tracker content, even when asked. |
| C13 | R G F | Recognition repair | Garbled or cut-off learner turns get a repeat/continue request, not a grammar correction. |
| C14 | G | Attempt before model | The learner gets to try first; if stuck, a partial cue comes before the full target sentence. |
| C15 | — | Plain spelling | Retired (learnukrainian, Claude line). |
| C16 | R G F | No meta-talk | Teacher turns never contain notes about the brief, the recording, or the teacher's own process, in any language. |
| C17 | R G F | One purpose | The teacher does only its mode's activity: no conversation in repetition, no listen-and-repeat drill or recall quiz in guided, no drills or target list in free; it closes when the mode's end is reached instead of extending the lesson. (Added 2026-10-29 with g2.) |
| C18 | F | Light correction | No correction marker, repetition requests or grammar explanations; at most a natural recast when meaning was lost or an interference word (the profile's `interference`, e.g. Russian for Ukrainian) was used; the teacher never says the learner's answer for them. (Added 2026-10-29 with g2.) |

Also note anything the learner reported about audio in the transcript's
**Test settings** block (stress, speed, cut-offs, voice).

## Versions

### Before g2 — learnukrainian

v0 (ChatGPT, until 2026-09-13), v1–v4 (Claude voice mode, 2026-09-14 to
2026-09-25) and g1 (ChatGPT, 2026-09-25) were developed for Ukrainian only in
`diegoami/learnukrainian` (`pimsleur-review/VOICE_ITERATIONS.md`), with their
test runs. What carried over: plain spoken sentences (C11), one opening line
per turn (C3, C4), an explicit list of banned praise words (C5), no
multi-step summary sentences (C6, C7), a repeat request instead of a
correction for unclear turns (C13), any first voice turn as the start
command and a target-language-only close (C2, C12), the teacher speaks only
its own line with a partial cue before any full model (C14), corrects only
wrong target language (C8), and never speaks notes about the instructions
(C16). ChatGPT Voice is the teacher because its recognition kept Ukrainian
learner turns Ukrainian, where Claude voice mode turned them into Russian
spelling.

### g2 — One lesson, one mode (2026-10-29), any language

learnukrainian's g2 split every lesson into exactly one mode (repetition,
guided conversation, free conversation), 5–10 minutes each, because combined
15–25 minute lessons were regularly abandoned half-way. New checks C17 (one
purpose) and C18 (light correction in free conversation).

In learnanylanguage the g2 blocks became a template: every Ukrainian word,
the language name, the role context, and the interference and stress rules
are placeholders filled from the language profile and the track. For
Ukrainian the template renders word for word as learnukrainian's g2
(`tests/test_prompt.py`), so its runs remain comparable. Spanish (es-travel,
es-smalltalk) runs the same rules with Spanish classroom phrases, no stress
rule and no interference clause.

Hypothesis (as in learnukrainian): short single-purpose lessons are
finished; the teacher does not drift between modes (C17). New for other
languages: whether the English-written controller works as well when the
classroom phrases are Spanish, and whether the informal [phrases] override
(es-smalltalk) keeps the teacher in tú.

Test results: pending (no runs yet in any language).
