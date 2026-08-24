---
name: code-review
description: Review code changes either from the local working tree/current branch or from a GitLab merge request. Use when the user asks for a code review, MR review, branch review, review of local/staged changes, or wants findings that can optionally be posted back to GitLab via glab.
compatibility: Uses git for local reviews and glab for GitLab MR reviews. Can use one optional independent subagent pass for non-trivial reviews and falls back to a parent-only workflow when unavailable. Can use jira-task-context when a Jira key/URL is found.
---

# Code Review

Review code like a senior engineer. Support both local branch/worktree reviews and GitLab merge request reviews.

## Core rules

- Default to read-only review. Do not edit code during a review unless the user explicitly asks for fixes.
- Compare changes against requirements, project guidance, surrounding code, tests, and existing codebase patterns.
- Report only defects introduced or exposed by the reviewed change. Suppress unrelated pre-existing issues and duplicates of unresolved discussions.
- Require a concrete failure mode, requirement violation, or applicable project-rule violation. Do not report vague maintainability concerns or style preferences.
- Treat severity and confidence separately. Report only independently verified findings with confidence **80 or higher**.
- Prefer actionable minimal fixes. A missing test is a finding only when tied to concrete changed behavior, a regression risk, or an explicit requirement.
- If there are no reportable findings, say so clearly and mention residual risks or unverified areas without presenting rejected candidates as suggestions.
- Use `gitlab-glab`/`glab` for GitLab data and `jira-task-context` for Jira data when relevant.
- Preserve repository and Git state throughout the review.

## Select the review mode

Use **GitLab MR mode** for a GitLab MR URL, an MR IID in the target repository, or an explicit MR-review request. For URLs, extract the IID after `/merge_requests/`.

Use **local mode** for uncommitted changes, staged changes, the current branch, a branch against a base, or specified local paths.

If ambiguous, ask whether the user means local unstaged/staged changes, a branch comparison, or a GitLab MR.

## Required reference routing

Resolve references relative to this skill directory. Read every selected reference completely before performing that part of the workflow.

1. Always read `references/review-methodology.md`.
2. For local reviews, read `references/local-review.md`.
3. For GitLab MR reviews, read `references/gitlab-review.md`.
4. Read `references/posting-findings.md` only when GitLab findings are authorized for posting after selection, or when the user already explicitly requested posting every reportable finding.

Do not load GitLab or posting instructions during an ordinary local review.

## Workflow

1. Establish the exact target, comparison base, and changed-file list.
2. Gather requirements and scoped project guidance before judging the implementation.
3. Follow the selected mode reference and the shared methodology.
4. Inspect the diff plus enough surrounding code, tests, configuration, and call sites to verify behavior.
5. Consolidate and independently verify candidates; keep only confidence-80+ findings.
6. Present findings before any externally visible action.
7. For GitLab reviews, refresh the MR and discussions before finalizing findings, then use the selector unless posting all findings was explicitly authorized.

For GitLab findings:

- Immediately call `review_findings_selector` after presenting all reportable findings unless the user already explicitly requested posting every reportable finding in the same request.
- Post only selected findings, or all reportable findings when that exact action was directly authorized.
- Never duplicate an equivalent unresolved discussion.

## Fixing findings

A review is read-only by default. If the user explicitly asks to fix findings:

1. Inspect the relevant implementation and present a short plan for the selected fixes.
2. Proceed with scoped changes and focused verification without asking for redundant confirmation.

If the user requested only a review, remain read-only and ask before editing.
