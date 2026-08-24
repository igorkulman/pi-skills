---
name: git-commit
description: Create high-quality Git commits from local changes. Use when the user asks to commit, stage changes, split work into commits, or prepare commit messages.
compatibility: Requires git. Operates directly in the current repository and avoids destructive Git commands unless explicitly requested.
---

# Git Commit

Create clean, intentional commits directly in the current session. Do not delegate the workflow to a subagent.

## Core rules

- Inspect the complete relevant staged and unstaged changes before staging anything.
- Commit only changes that belong to the user's requested scope. If ownership is unclear, ask before staging.
- Preserve existing staged intent unless the user asks to reorganize it.
- Keep each commit atomic and coherent. Include tests with the production behavior they verify unless tests are independently meaningful or the user requests a separate commit.
- Split independent features, fixes, refactors, documentation, or build changes when that produces clearer commits; do not split merely by file type or file count.
- Do not mention AI assistance, agents, generated-by text, or co-authorship.
- Avoid prefixes such as `feat:`, `fix:`, `chore:`, Jira keys, ticket IDs, or bracketed labels unless explicitly requested.
- Never use vague messages such as `Address review feedback`, `Fix comments`, `Update code`, `Misc changes`, `Cleanup`, or `WIP`.
- Do not run destructive history or worktree commands such as reset, checkout, switch, rebase, clean, amend, or squash unless the user explicitly requests that action.
- Never stash changes automatically. If unrelated or dirty worktree changes block the requested operation, report them and ask the user to handle them or explicitly request a stash.

## Workflow

### 1. Inspect

Run read-only discovery:

```bash
git status --short
git branch --show-current
git diff --stat
git diff --cached --stat
git diff
git diff --cached
git log --oneline -n 20
```

Use recent history to learn the repository's message tone and granularity. Determine whether existing staged changes belong to the request.

### 2. Plan commits

Group changes by intent. If multiple reasonable groupings exist or unrelated changes are present, summarize the proposed groups and ask before staging.

A production change and its focused regression test normally belong together. Separate them only when one is useful and understandable without the other.

### 3. Stage precisely

Prefer path-specific or patch staging:

```bash
git add -- path/to/file
git add -p -- path/to/file
```

Avoid `git add .` and `git add -A` unless inspection confirms every changed path belongs to the same commit.

Before each commit, verify:

```bash
git diff --cached --name-status
git diff --cached --stat
git diff --cached
```

Do not commit a staged diff containing unrelated changes.

### 4. Write the message

Use a concise, specific subject, normally imperative and under 72 characters, with no trailing period. Describe the repository change rather than the process that prompted it.

Examples:

- `Guard notification tracking against missing payload data`
- `Use injected analytics client for child-alone tracking`
- `Add child-alone notification analytics coverage`

Add a body only when it provides useful rationale, constraints, or non-obvious behavior.

### 5. Commit and verify

Create each commit, then inspect the result:

```bash
git commit -m "Descriptive subject"
git status --short
git log --oneline -n 5
```

Report each created short hash and subject, remaining uncommitted changes, and any verification that was or was not run.
