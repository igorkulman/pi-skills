---
name: git-redate
description: Rewrite Git commit timestamps. Use when the user wants to change, move, or fix the date/time of specific commits — including moving weekend commits to weekdays, setting a commit to a particular date, or adjusting multiple commit dates at once.
---

# git-redate

Rewrite author and committer timestamps for one or more commits using
`git rebase -i` with an injected `GIT_SEQUENCE_EDITOR`. No external plugins required.

> ⚠️ **This rewrites commit history.** Safe for unpushed commits. For already-pushed
> commits a `git push --force-with-lease` will be needed afterward.

---

## Script

```
./scripts/redate.py
```

Resolve against the skill directory:
`~/.pi/agent/skills/git-redate/scripts/redate.py`

---

## Modes

### Auto mode — move all weekend commits in a range

Scans a commit range, finds Saturday/Sunday commits, moves them to Monday or Friday.

```bash
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py [--range RANGE] [--move-to monday|friday] [--dry-run]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--range RANGE` | `@{u}..HEAD` | Range to scan — default is all unpushed commits |
| `--move-to monday\|friday` | `monday` | Where to move Saturday/Sunday commits |
| `--dry-run` | — | Preview without touching history |

### Manual mode — set specific commits to specific dates

Explicitly name which commits to rewrite and to what date/time. Repeatable.

```bash
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py --set HASH DATE [--set HASH2 DATE2 ...] [--dry-run]
```

| Argument | Description |
|----------|-------------|
| `HASH` | Full or short commit hash (e.g. `a1b2c3d`) |
| `DATE` | Target date/time — see formats below |

**DATE formats:**

| Format | Example | Time behaviour |
|--------|---------|----------------|
| `YYYY-MM-DD` | `2025-01-20` | Preserves original time of day |
| `YYYY-MM-DDTHH:MM` | `2025-01-20T14:30` | Sets exact time |
| `YYYY-MM-DDTHH:MM:SS` | `2025-01-20T14:30:00` | Sets exact time |
| `YYYY-MM-DD HH:MM` | `2025-01-20 14:30` | Sets exact time |

---

## Agent workflow

### For "move weekend commits" requests

1. Run auto dry-run to show what will change:
   ```bash
   python3 ~/.pi/agent/skills/git-redate/scripts/redate.py --dry-run
   ```
2. Present the output to the user.
3. If the user explicitly requested this rewrite and the dry-run matches the requested scope, apply without asking again. Otherwise ask for authorization before applying:
   ```bash
   python3 ~/.pi/agent/skills/git-redate/scripts/redate.py
   ```

### For "change specific commits" requests

1. Show the user recent commits so they can identify which ones to change:
   ```bash
   git log --format="%h  %ad  %s" --date=format:"%a %Y-%m-%d %H:%M" -n 20
   ```
2. Understand the user's intent — e.g.:
   - "change `a1b2c3d` to last Wednesday"
   - "move these two commits to Monday morning"
   - "set commit `deadbeef` to 2025-01-15 at 10:00"
3. Resolve natural-language dates to concrete `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`
   values using the current date as reference.
4. Run dry-run and present the planned changes:
   ```bash
   python3 ~/.pi/agent/skills/git-redate/scripts/redate.py \
     --set a1b2c3d 2025-01-15 \
     --set deadbeef 2025-01-15T10:00 \
     --dry-run
   ```
5. If the request already specified the commits and target dates and the dry-run matches it, apply without another confirmation. Otherwise ask the user to authorize the concrete dry-run plan before applying without `--dry-run`.

### After applying

Always verify the result:
```bash
git log --format="%h  %ad  %s" --date=format:"%a %Y-%m-%d %H:%M" -n 20
```

---

## Example invocations

```bash
# Auto: preview all unpushed weekend commits
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py --dry-run

# Auto: move unpushed weekend commits to Monday
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py

# Auto: move to Friday, custom range
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py --range main..HEAD --move-to friday

# Manual: move one commit to a specific date (preserves original time)
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py --set a1b2c3d 2025-01-20

# Manual: move one commit to a specific date and time
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py --set a1b2c3d 2025-01-20T10:30

# Manual: rewrite multiple commits at once
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py \
  --set a1b2c3d 2025-01-20 \
  --set b2c3d4e 2025-01-21T09:00 \
  --set c3d4e5f 2025-01-22

# Manual: dry-run first
python3 ~/.pi/agent/skills/git-redate/scripts/redate.py \
  --set a1b2c3d 2025-01-20 \
  --dry-run
```

---

## How it works

1. **Auto mode:** `git log` collects commits in the range. Weekend commits get their
   timestamps shifted ±1–2 days (time of day preserved).
2. **Manual mode:** each `--set HASH DATE` pair is resolved via `git rev-parse`.
   If only a date is given, the commit's original time is preserved.
   The rebase base is computed automatically from the oldest targeted commit.
3. A temporary `GIT_SEQUENCE_EDITOR` script is generated that injects
   `exec env GIT_COMMITTER_DATE='...' git commit --amend --no-edit --date='...'`
   after the relevant `pick` lines in the rebase todo.
   (`--date` sets author date; `GIT_COMMITTER_DATE` sets committer date.)
4. `git rebase -i <base>` runs with that editor. The script has its own confirmation prompt; answer it affirmatively only when the rewrite is authorized under the global policy.
5. Temp files are cleaned up automatically.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `fatal: no upstream configured` | Pass `--range HEAD~N..HEAD` explicitly |
| Rebase fails mid-way | Run `git rebase --abort` to restore |
| Uncommitted changes | Stop and ask the user to commit/discard them or explicitly request a stash; never stash automatically |
| Already-pushed commits | Report that `git push --force-with-lease` will be required; never force-push unless the user explicitly requests it |
| Commit not in branch history | Make sure you are on the correct branch |
