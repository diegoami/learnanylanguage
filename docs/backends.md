# Where learner data lives: backends compared

Learner data (profile, trackers, lesson folders with transcripts, review
queues, teacher runs) is written by the coding agent's workflows and read
by the learner. This note compares where it can live and how to read it.
Decision (2026-10-29): **a folder of Markdown and TOML is the store, a
private git repository is the recommended home for it, and readers sit on
top of it without syncing**.

## What the store has to do

1. **Any coding agent can write it** with ordinary file edits, without
   credentials, SDKs or network access (AGENTS.md: model-agnostic, standard
   library only at runtime).
2. **Evidence stays exact**: transcripts are kept unedited, and trackers keep
   every attempt → preferred form → reason. Every change is reviewable.
3. **It is private**: transcripts are personal data.
4. **It works offline and on more than one computer.**
5. **The learner can read and evaluate it** comfortably, on a phone too.

## The store

| Option | 1 agent writes | 2 exact, reviewable | 3 private | 4 offline, several computers | Verdict |
| --- | --- | --- | --- | --- | --- |
| Plain directory (default `~/.local/share/learnanylanguage/learner`) | yes | yes, no history | yes | offline yes; one computer | fine to start |
| **Private git repository** (`data_dir` → a clone) | yes | yes, with history; one commit per lesson | yes | yes, push and pull | **recommended** |
| Notion database | needs an integration token and API calls (rate-limited); Markdown tables become database rows; transcripts become blocks | edits happen in two places (agent and app) and drift; no diff of a lesson | data on a third-party service | online only for the agent | not as the store |
| Google Sheets / Airtable | API and credentials; transcripts do not fit cells | weak history | third-party | online | not as the store |
| SQLite file | needs code for every edit; agents cannot hand-edit safely | binary diffs | yes | offline; sync is awkward | at most a derived cache |

The data already is a set of Markdown files. Every option except a folder
would put an API between the agent and the evidence, and would need a sync
that the workflows do not have to handle today.

## Readers on top of the store

These read the same folder; none needs a sync step.

| Reader | Setup | Good for | Limits |
| --- | --- | --- | --- |
| **`lal gui`** (built in) | `lal gui`, or `lal gui --data DIR\|GIT_URL` | evaluation: sessions covered per track, recorded lessons per week, evidence labels, queue status, failed teacher checks per prompt version, git history; opens any tracker, package or transcript | local, read-only; desktop or phone on the same machine |
| **Obsidian** | open the learner-data folder as a vault | reading and searching everything, links, mobile reading (Obsidian Git plugin or Obsidian Sync) | Dataview queries frontmatter and fields, not the trackers' Markdown tables, so it cannot compute the overview without a format change. Hand edits bypass the record workflow; keep them to notes |
| **GitHub** (the private repository on the web and in the mobile app) | none | reading on a phone, history and diffs per lesson | no aggregate view |
| Logseq | open the folder as a graph | reading | outliner-first; tables and long transcripts read poorly |

Recommendation: `lal gui` to evaluate, Obsidian or the GitHub app to read on
the go. In the Obsidian vault, ignore `.obsidian/workspace*.json` in git;
the learner-data repository's `.gitignore` does.

## Worth adding later

- **Anki export of the review queue** (and tracker vocabulary): a CSV or
  `.apkg` of the active queue targets, with their source and origin. Spaced
  repetition between voice lessons is the one thing none of the readers
  adds. Export only, so Anki never becomes a second record: a word
  practised in Anki is not transcript evidence.
- **A Notion export**, one-way, if the learner wants trackers in Notion: a
  `lal export notion` that writes the current position and queues into a
  database. Only on request; the folder stays the store.
- **Frontmatter in lesson folders** (date, track, mode, channel) if Obsidian
  queries become important: that would let Dataview list lessons without
  `lal gui`.
