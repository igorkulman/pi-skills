---
name: verify
description: Verify whether self-authored review comments on a GitLab merge request or GitHub pull request have been addressed, then optionally resolve fixed self-authored threads and approve when explicitly requested. Use after a code review when the author has pushed fixes and the user wants /verify <pr-or-mr-url>.
compatibility: Uses glab for GitLab MRs. GitHub PR support uses gh when available. Only threads created by the authenticated user (Igor Kulman) are assessed/resolved. Mutating actions require an explicit user request.
---

# Verify Review Feedback

Inspect unresolved self-authored review threads, compare each concern with the latest replies/diff/code, report whether it is addressed, and optionally resolve addressed threads and approve when explicitly requested.

## Core rules

- Default to read-only assessment. Do not resolve threads, submit reviews, or approve unless the user explicitly requests those exact actions. A direct request in the initial message counts; do not ask redundantly.
- Assess/resolve only threads whose original review note was authored by the authenticated user (Igor Kulman; GitLab username usually `igor.kulman`). Report other authors' open resolvable-thread count but do not assess or mutate them unless scope is explicitly changed.
- Mark a thread **Addressed** only when replies or latest code/diff clearly implement the requested behavior, test, migration, localization, or error handling.
- Mark ambiguous evidence **Uncertain** or **Not addressed** and leave the thread open.
- Resolve addressed in-scope threads before approving. Never approve while an in-scope resolvable thread remains open.
- Re-fetch remote thread state after mutations and before approval.
- Do not use ad hoc Python. Prefer `glab`, `gh`, `git`, `jq`, `rg`, `sed`, and `awk`.
- Do not switch branches or mutate Git state unless explicitly requested and the working tree is safe.

## Target and required routing

Supported targets:

- GitLab MR URL or MR IID in the target repository
- GitHub PR URL when authenticated `gh` is available

If ambiguous, ask which platform/repository is intended.

Resolve references relative to this skill directory and read the selected file completely:

- GitLab MR: `references/gitlab.md`
- GitHub PR: `references/github.md`

Load exactly the relevant platform workflow; do not load both.

## Shared assessment contract

For each open in-scope self-authored thread:

1. Read the original concern and all replies.
2. Inspect the latest diff and enough code/context to verify behavior.
3. Classify it as **Addressed**, **Not addressed**, or **Uncertain**.
4. Record concrete evidence and proposed action: Resolve or Leave open.

Present the assessment before mutations, including:

- target and in-scope count
- other authors' open resolvable-thread count
- thread ID, location, concern excerpt, status, evidence, and proposed action
- remaining blockers and approval recommendation
- whether resolution/approval is already authorized or still requires a request

If the user already requested resolving addressed self-authored threads and approving when clean, state the planned actions and continue without asking again. Otherwise wait for explicit authorization.

## Mutation order

When authorized:

1. Resolve only in-scope threads classified Addressed.
2. Check every API result.
3. Re-fetch thread state.
4. Approve only when no in-scope resolvable threads remain and approval was explicitly requested.
5. Report resolved/open thread IDs, other-author count, approval status, and failures.

Do not approve drafts unless the user explicitly requests approval despite draft state and the platform allows it.

## Known pitfalls

- A reply saying “fixed” is evidence, not conclusive proof when code contradicts it.
- Outdated threads are not automatically addressed.
- GitLab `resolved` may be missing/null; use `(.resolved != true)` for open discussions.
- Prefer current GitLab repository context and `projects/:id`; mismatched `--repo`/host usage can produce 404s.
- GitHub thread/comment pagination limits must be reported rather than silently truncating assessment.
