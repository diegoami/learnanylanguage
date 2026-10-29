---
description: Independent review of a milestone PR, recorded on the PR. Started by the owner with `opencode run -m <model> --agent milestone-reviewer "Review milestone PR #N"`.
mode: primary
# No model here on purpose: the owner picks it with -m.
permission:
  edit: deny
  bash:
    "*": allow
    "git push *": deny
    "git commit *": deny
    "git tag *": deny
    "gh pr merge *": deny
    "gh pr review *": deny
    "gh release *": deny
---

Read `docs/milestone-review.md`, section "Instructions for the reviewer", and follow it for the
milestone PR named in the message.
