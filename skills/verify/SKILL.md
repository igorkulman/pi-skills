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
- Never approve when the MR/PR has zero total in-scope self-authored resolvable threads; that means this reviewer has not reviewed it.
- Never approve a draft/WIP.
- Never approve while the latest CI pipeline/check is failing, running, pending, or otherwise incomplete. Passing means `success`, `skipped`, or `manual`; no pipeline/check is not a blocker.
- Re-fetch remote thread state, draft state, and CI state after mutations and before approval.
- Approval requires explicit authorization after the approval gate is known. If approval was already explicitly requested in the initial instruction, do not ask redundantly; otherwise show the approval confirmation picker.
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

- target, total in-scope resolvable-thread count, and open in-scope count
- other authors' open resolvable-thread count
- draft state and latest CI pipeline/check status
- thread ID, location, concern excerpt, status, evidence, and proposed action
- remaining blockers and approval recommendation
- whether resolution/approval is already authorized or still requires a request

## Resolution selector

If the user already requested the exact threads to resolve, state the planned resolutions and continue without asking again. Otherwise, immediately after presenting the assessment, call `ask_user_question` with a selector for the individual **Addressed** threads. Do not show a generic action picker and do not merely wait for another command.

The selector must:

- show one selectable option per **Addressed** thread, identified by a concise thread ID, location, and concern excerpt
- use `multiSelect: true` when there are two or more candidates, so the user can check exactly which threads to resolve and leave the rest unchecked
- state that only selected threads will be resolved
- never offer **Not addressed** or **Uncertain** threads as resolution choices
- treat cancellation or no selection as authorization for no mutations

`ask_user_question` allows at most four options per question and four questions per invocation. Put up to four thread options in each question and group all required questions into one invocation when possible. If there is exactly one candidate, use a single-select question with **Resolve this thread** and **Keep it open**. If there are more candidates than one invocation supports, continue in numbered batches, preserving the thread IDs.

The resolution selector authorizes only the selected resolutions; it does not authorize approval. Threads assessed as addressed but left unchecked remain open and block approval.

If there are no **Addressed** candidates, do not show a resolution selector. Continue to the approval gate only when no open in-scope threads remain.

## Approval gate and confirmation

After resolving selected threads, re-fetch remote thread state, draft state, and latest CI state. Approval is possible only when all of these are true:

- total in-scope self-authored resolvable-thread count is greater than zero
- open in-scope self-authored resolvable-thread count is zero
- the MR/PR is not draft/WIP
- latest CI is `success`, `skipped`, or `manual`; no CI pipeline/check is also allowed

Treat `failed`, `canceled`, `running`, `pending`, `created`, `waiting_for_resource`, `preparing`, and `scheduled` as blocking. If any gate fails, report every blocker and do not offer or perform approval.

When all gates pass and approval was not already explicitly requested, call `ask_user_question` with **Approve** and **Do not approve**. The question must summarize the number of resolved threads, non-draft state, and CI status. Only approve after the user selects **Approve**. If the initial instruction already explicitly requested approval when clean, that authorization remains valid and must not be requested again.

## Mutation order

After selector submission or direct authorization:

1. Resolve only the selected or explicitly requested in-scope threads classified **Addressed**.
2. Check every API result.
3. Re-fetch thread, draft, and CI state.
4. Evaluate every approval gate and report blockers.
5. If all gates pass, obtain approval authorization unless it was already explicit.
6. Approve only when authorized and all gates still pass.
7. Report selected/resolved/open thread IDs, other-author count, draft and CI state, approval status, and failures.

## Known pitfalls

- A reply saying “fixed” is evidence, not conclusive proof when code contradicts it.
- Outdated threads are not automatically addressed.
- GitLab `resolved` may be missing/null; use `(.resolved != true)` for open discussions.
- Prefer current GitLab repository context and `projects/:id`; mismatched `--repo`/host usage can produce 404s.
- GitHub thread/comment pagination limits must be reported rather than silently truncating assessment.
