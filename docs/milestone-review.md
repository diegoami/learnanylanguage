# Milestone review

A milestone is an engine version tag `vX.Y.Z` on `main`. Its work arrives as
one **milestone PR** from `milestone/X.Y.Z` into `main`, and one independent
review covers the whole PR before it is merged. There is no automatic
reviewer: the owner starts the review by calling a model's CLI, on whatever
model they pick, in a fresh session. Adapted from malpaco's milestone review.

Track releases (`tracks-YYYY.MM.DD`, [workflows/track.md](../workflows/track.md))
are separate and public: they follow an accepted milestone only when the
owner asks.

## How a milestone happens

1. The owner calls a milestone, or the main session proposes one when a
   coherent set of work is ready.
2. The work, the version bump (`pyproject.toml`, `src/lal/__init__.py`,
   `uv.lock`) and the release notes (`docs/releases/X.Y.Z.md`) go on the
   branch `milestone/X.Y.Z`; its head is the **candidate**.
3. The main session opens the **milestone PR** (label `milestone`) whose body
   gives: the proposed tag, the candidate's full SHA, the base (previous tag
   or commit), the checks already run, the claims to verify with
   `file:line`, and the owner's decisions that are not defects. From then on
   the branch takes only fixes for the review's findings.
4. The owner starts the review from any checkout of this repository, for
   example:

   ```sh
   opencode run -m <provider/model> --agent milestone-reviewer "Review milestone PR #N"
   claude -p --model <model> "Read docs/milestone-review.md and review milestone PR #N as it says."
   codex exec "Read docs/milestone-review.md and review milestone PR #N as it says."
   ```
5. The reviewer opens one issue per reproduced finding and posts one verdict,
   AGREE or BLOCK, as a comment on the PR. Nothing is pasted back.
6. BLOCK: the findings are fixed on the milestone branch, the PR body names
   the new candidate SHA, and the owner starts a re-review. After a third
   round without AGREE the owner decides.
7. AGREE: the owner merges the PR; the main session tags the merged commit
   `vX.Y.Z`. The owner may also merge without a review; the PR says so.

## Instructions for the reviewer

You are the independent reviewer of a learnanylanguage milestone. You
implemented none of it: verify everything against the files, not against
commit messages, the PR body or the docs.

**Input.** The milestone PR number. `gh pr view <n> --comments` gives the
tag, candidate SHA, base, checks, claims and owner decisions; for a
re-review, the earlier verdict and the fixes. If any of these is missing,
say so on the PR and stop.

**Set up.** `git fetch origin`. If the working tree is clean,
`git checkout --detach <sha>`, then run:

- `uv sync` and `uv run pytest -q`
- `uv run lal track validate tracks/*`
- `LAL_TRACK_PATH=tracks LAL_DATA=$(mktemp -d) uv run lal lesson new --track <id> --mode <mode> [--part X] [--channel text] --session N --stdout`
  for every mode and channel on at least two languages, and read the output
- `uv run lal audit --language uk <file>` on Ukrainian files whose stress
  marks changed (network; the first run takes minutes)

When you finish, check out the branch you started on. If the tree is not
clean, do not touch it: read the candidate with `git show <sha>:<path>` and
say which checks you could not run.

**Review** `git diff <base>..<sha>` and follow it into every file it touches
or relies on. `AGENTS.md` is the standard. Look hardest at:

- **The teacher prompt** (`src/lal/prompt/CONTROLLER.md`): does each block,
  rendered for each language, tell ChatGPT to do what the mode claims?
  Contradictions between blocks (COMMON vs CLOSE report), rules a voice
  model cannot follow, wording that invites the failures the adherence
  checklist (`prompt/ITERATIONS.md`) tests for. The original modes must
  render as g2 apart from the version line.
- **Language content**: grammar, spelling, register, translations, romaji,
  grammar tables and drill answers in every new or changed track, as a
  native-level teacher would see them. Ukrainian stress only through
  `lal audit` evidence. This is what no test can see.
- **The engine** (`src/lal/`): packages that `lal lesson check` accepts but
  that would break a lesson, parsing that reads the controller instead of
  the brief, the report parser's false passes and false alarms, CLI options
  that do not reach the code.
- **Rules from AGENTS.md**: no code in tracks, no learner data in the
  repository, original material only, no scores or assessments from the
  teacher beyond the factual LESSON_REPORT.
- **Workflows and docs** that an agent would follow into a wrong action.

Out-of-scope problems elsewhere count too; mark them so.

**Write to GitHub yourself**, and only this; never edit, commit, push, tag,
merge or approve:

- one issue per reproduced finding: label `review` plus one of `bug`,
  `content`, `prompt`, `tests`, `documentation`; `MUST-FIX:` or
  `Follow-up:` at the start of the title; linking the milestone PR and SHA;
- exactly one verdict comment on the milestone PR: AGREE, or BLOCK when any
  finding is MUST-FIX; the SHA reviewed, your model, whether you checked out
  the SHA, the checks you ran and their results, the issues you opened, and
  what you checked and found clean. A review that finds nothing still leaves
  this record.

Write comment and issue bodies to a file and pass `--body-file`. If posting
fails, print the complete text instead and say why.
