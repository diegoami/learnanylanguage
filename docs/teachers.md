# Who teaches: alternatives to ChatGPT, with your own key

Evaluation, 2026-10-29. Today every lesson is taught by **ChatGPT** (Voice,
or a typed chat) from a pasted package, recorded afterwards from a share
link. This note looks at adding **other teachers as an option**, ChatGPT
staying the default, and in particular Gemini with **bring-your-own-key
(BYOK)**, drawing on what `diegoami/voice-teacher` measured.

## What voice-teacher already learned

voice-teacher ([`pocs/05-session-engine`](https://github.com/diegoami/voice-teacher/tree/main/pocs/05-session-engine),
[`docs/architecture.md`](https://github.com/diegoami/voice-teacher/blob/main/docs/architecture.md))
does not use a voice chat at all. It owns the turn loop:

```
phone (PWA, tap to talk) → ElevenLabs Scribe v2 (language locked)
  → engine state machine (lesson shape in code; the model only judges)
  → OpenRouter, google/gemini-3.8-flash as judge (keys: OPENROUTER_API_KEY)
  → ElevenLabs Multilingual v2 with stress-marked text → phone
```

Measured there: Gemini 3.8 Flash judged a simulated lesson as well as GPT-6
Sol and Luna and was fastest (median 1.06 s per call, about 3 cents of
judging per lesson); two real Ukrainian voice lessons on Android cost $0.155
and $0.076 with turns of about 1–3 s. The decisive lessons:

- **Recognition decides the runtime.** A language-locked recogniser (Scribe)
  kept Ukrainian as Ukrainian *and kept the learner's mistakes*, which
  `gpt-transcribe` tended to correct away. A general voice chat cannot be
  locked to a language.
- **Structure in code beats structure in a prompt**, but that is a whole
  product (server, storage, audio, PWA, 30+ tasks), not an option to bolt
  onto `lal`.
- Speech-to-speech APIs were judged "several times the cost" and "the
  teacher model fixed to the vendor"; that was against OpenAI Realtime
  (≈ $3 per 10 minutes). Gemini's Live API is now far cheaper (below).

## The candidates

### A. Gemini app (Gemini Live), pasted package: no code

The same pattern as ChatGPT: paste the package, start Live, speak.

- For: no key, no code beyond a COMMON variant naming the app; Gemini Live
  speaks Ukrainian, Japanese and Polish, and its voices list Swedish.
- Against, unverified: whether a pasted package stays in force once Live
  starts, whether the Live turns appear in a shareable chat, and in what
  format (`lal share` reads only chatgpt.com pages). Every one of these is
  an app behaviour that can change without notice.
- Cost: a Gemini subscription; no BYOK.
- Verdict: worth **one manual test** (ten minutes, no code) before building
  anything, because it answers "does Gemini follow our controller in voice?"
  for free. Not worth building around until the transcript can be captured.

### B. Gemini Live API from a local page, BYOK: `lal live`

`lal` serves a local page (like `lal gui`) that talks to the **Gemini Live
API** directly from the browser over WebSocket: microphone in, the teacher's
voice out, the rendered package as the system instruction, and **input and
output transcription switched on**, so the page saves the transcript into
the lesson folder itself. No share link, no copy-paste.

Facts (Google's docs, checked 2026-10-29):

- Models: `gemini-3.8-live` and `gemini-3.8-live-extended-thinking`
  (GA), `gemini-3.1-flash-live-preview` (legacy).
- 99 languages, including `uk`, `pl`, `ja`, `sv`, `es`.
- Native audio models **cannot be locked to a language code**: they pick
  the language themselves; system instructions can only restrict it. Output
  is audio only; text comes from output transcription.
- Audio sessions last at most 15 minutes (enough for a 5–10 minute lesson).
- Price: audio in $0.005/min, audio out $0.018/min; text in/out
  $0.75/$4.50 per million tokens. A 10-minute lesson is roughly
  **$0.10–0.30** (to be measured: context re-reading per turn is the
  uncertain part). There is a rate-limited **free tier**; Google may use
  free-tier content to improve its products, so a paid key suits transcripts
  you want kept private.
- Keys: the browser should not hold the long-lived key. The local `lal`
  server keeps the key and mints an **ephemeral token** (one HTTPS call,
  standard library), locked to the model and config, valid 1 minute to
  connect and 30 minutes in use.

BYOK fits naturally: the key is the learner's own (`GEMINI_API_KEY` in the
environment, or a `keys.toml` with mode 600 next to `lal.toml`), never in a
track, a package, the learner data or a git repository.

- For: the transcript is captured automatically and completely (both
  sides, timestamps), which removes the share-link step and the "pasted
  transcript lost turns" failure; the same controller and modes work, so
  runs stay comparable with ChatGPT on the adherence checklist; cheap; all
  five languages; free tier for trying; standard library on the server, the
  WebSocket lives in the page.
- Against: (1) **the recognition question voice-teacher already met**: the
  model's own recognition, not a language-locked recogniser, writes the
  learner's turns. It may drift (Ukrainian heard as Russian) or tidy the
  learner's mistakes away, and the transcript is our only evidence. (2) The
  model speaks the stress itself: authored stress marks help only as much as
  in ChatGPT Voice. (3) It is still a prompt-following teacher, with
  ChatGPT's adherence risks (praise, giving answers early). (4) Phone use
  needs HTTPS (a tunnel, as voice-teacher's `run.sh` does); desktop first.
  (5) Effort: a microphone worklet (16 kHz PCM), playback (24 kHz PCM),
  a token endpoint, a transcript endpoint, a COMMON variant without the
  paste step, tests with a fake socket: a few hundred lines.
- Verdict: **the best option for voice**, as a proof of concept first,
  judged on two questions before it becomes a supported runtime: does the
  input transcription keep the learner's language and mistakes, and does
  Gemini follow the controller at least as well as ChatGPT Voice?

### C. Typed lessons through any chat API, BYOK: `lal chat`

For the text channel (writing, typed grammar and vocabulary drills): a
terminal or local-page chat that sends the package as the system prompt to
an **OpenAI-compatible chat endpoint**, with the learner's key: Gemini
(through its OpenAI-compatible endpoint), OpenRouter (any model, one key, as
voice-teacher uses), OpenAI, or a local model.

- For: smallest effort (a hundred lines, `urllib` only); automatic
  transcript; the model becomes a choice per lesson (`--model
  google/gemini-3.8-flash`); costs fractions of a cent per lesson; it is the
  BYOK plumbing that B needs anyway (key lookup, no key in any repository).
- Against: text only; it competes with a free ChatGPT chat window, so its
  value is the automatic transcript and the model choice.
- Verdict: **build first**: low risk, immediately useful for the
  experimental text modes, and it settles the key handling before B.

### D. voice-teacher as the teacher

Feed `lal` tracks into voice-teacher's engine (its legacy adapter already
reads learnukrainian packages plus reviewed lesson JSON).

- For: the strongest teaching loop (locked recognition, structure in code,
  stress handled, measured on real lessons).
- Against: a different lesson shape and data model, a server with storage
  and pairing, ElevenLabs and OpenRouter keys; it only supports Ukrainian
  profiles today. Joining the two would be a project of its own.
- Verdict: **keep separate**. If voice-teacher becomes the main way to
  practise, export `lal` tracks into its curriculum format then.

## Comparison

| | ChatGPT (today) | A · Gemini app | B · `lal live` (Gemini Live API) | C · `lal chat` (any chat API) | D · voice-teacher |
| --- | --- | --- | --- | --- | --- |
| Voice | yes | yes | yes | no | yes |
| BYOK | no (subscription) | no | yes | yes | yes (server keys) |
| Transcript | share link, by hand | unknown | automatic | automatic | automatic, with evidence |
| Same controller and modes | yes | yes, with a COMMON variant | yes, with a COMMON variant | yes (text modes) | no |
| Language-locked recognition | no | no | no | n/a | yes |
| Cost per 10-minute lesson | in subscription | in subscription | ≈ $0.10–0.30, free tier | < $0.01 | ≈ $0.08–0.16 measured |
| Effort in `lal` | — | minutes (test) | days (POC) | hours | separate project |

## Recommendation

1. **Now, no code:** one manual Gemini app lesson (A) with a current
   package, to see whether Gemini follows the controller in voice.
2. **Build `lal chat`** (C) with BYOK: `--provider openrouter|gemini|openai`
   and `--model`, keys from the environment or `~/.config/learnanylanguage/keys.toml`
   (mode 600), transcript written into the lesson folder in the share
   format so `lal report` and the record workflow work unchanged.
3. **Then a `lal live` POC** (B) on Gemini Live with an ephemeral token from
   the local server: one lesson per language, recorded and checked like
   ChatGPT runs, plus the recognition check (are the learner's mistakes and
   language preserved in the input transcription?).
4. Teacher choice stays per lesson: `teacher = "chatgpt"` remains the
   default; packages for an API teacher get their own COMMON variant (no
   paste step, no "Ready" reply) and the teacher is recorded in
   `teacher-runs.md`, so runs can be compared per teacher and prompt version.

Sources: Google's [Live API overview](https://ai.google.dev/gemini-api/docs/live),
[Live API guide](https://ai.google.dev/gemini-api/docs/live-guide) (models,
languages, transcription, session limits),
[ephemeral tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)
and [pricing](https://ai.google.dev/gemini-api/docs/pricing); voice-teacher's
POC 1, POC 5 and architecture notes.
