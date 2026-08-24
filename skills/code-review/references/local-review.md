# Local Review Workflow

Use for working-tree, staged, branch, or path-scoped local reviews. Apply `review-methodology.md` throughout.

## 1. Establish scope

Run read-only discovery:

```bash
git status --short
git branch --show-current
git remote -v
```

Capture the requested diff:

```bash
# Uncommitted working tree
git diff --stat
git diff --name-status
git diff > /tmp/pi_local_worktree_review.diff

# Staged changes
git diff --cached --stat
git diff --cached --name-status
git diff --cached > /tmp/pi_local_staged_review.diff

# Current branch against a supplied base
git merge-base HEAD <base-branch>
git diff --stat <merge-base>...HEAD
git diff --name-status <merge-base>...HEAD
git diff <merge-base>...HEAD > /tmp/pi_branch_review.diff
```

If no base was supplied for a branch review, infer carefully in this order:

1. upstream tracking branch
2. `origin/main`
3. `origin/master`
4. `origin/develop`
5. ask the user

Do not run `git checkout`, `git switch`, `git reset`, `git stash`, formatters, or other state-changing commands.

## 2. Inspect changed behavior and context

Use the diff to identify files/hunks, then read surrounding code:

```bash
rg "<changed symbol or feature term>" .
git diff --name-only <scope>
```

Before judging lines, inventory:

- user-visible/API behavior
- data/state transitions
- errors, permissions, lifecycle, persistence, and async behavior
- tests changed and the behavior they actually prove

Read as needed:

- full changed production files for non-trivial changes
- relevant tests and fixtures
- direct callers/callees and similar implementations
- configuration, routing, dependency injection, migrations, localization, and permission files
- project documents required by scoped guidance
- `CLAUDE.md`, `.ai-rules/`, and equivalent convention files

## 3. Review and report

Apply the shared review focus, independent-pass calibration, consolidation, confidence threshold, severity, and output format.

There is no GitLab posting selector for an ordinary local review. Report verified findings directly. Remain read-only unless the user explicitly requests fixes.
