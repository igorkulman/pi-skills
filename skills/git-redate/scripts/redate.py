#!/usr/bin/env python3
"""
git-redate: Rewrite commit timestamps.

Two modes:

  Auto mode (default):
    Scan a range of commits, find those on Saturday/Sunday, and move them
    to the nearest Monday or Friday, preserving the original time of day.

    python3 redate.py [--range RANGE] [--move-to monday|friday] [--dry-run]

  Manual mode:
    Explicitly specify which commits to rewrite and to what date/time.
    Can be mixed with auto mode.

    python3 redate.py --set HASH DATE [--set HASH DATE ...] [--dry-run]

DATE formats accepted:
    YYYY-MM-DD              preserves the commit's original time of day
    YYYY-MM-DDTHH:MM
    YYYY-MM-DDTHH:MM:SS
    YYYY-MM-DD HH:MM
    YYYY-MM-DD HH:MM:SS
"""

import argparse
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=capture,
        text=True,
        check=check,
    )


def get_commits_in_range(range_spec: str) -> list[dict]:
    """Return commits in range (oldest first)."""
    result = git("log", "--format=%H\t%at\t%ct\t%s", "--reverse", range_spec)
    return _parse_commit_lines(result.stdout)


def get_commit(ref: str) -> dict:
    """Return a single commit by ref/hash."""
    result = git("log", "-1", "--format=%H\t%at\t%ct\t%s", ref)
    commits = _parse_commit_lines(result.stdout)
    if not commits:
        raise ValueError(f"No commit found for ref: {ref!r}")
    return commits[0]


def resolve_hash(short_or_full: str) -> str:
    """Resolve any ref or short hash to a full 40-char commit hash."""
    try:
        return git("rev-parse", "--verify", f"{short_or_full}^{{commit}}").stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError(f"Cannot resolve commit: {short_or_full!r}")


def find_oldest_ancestor(full_hashes: list[str]) -> str:
    """
    Given a list of full commit hashes, return the hash of the one that is
    oldest (i.e. furthest from HEAD / deepest in history).
    """
    result = git("log", "--format=%H", "HEAD")
    history = result.stdout.strip().splitlines()  # newest first → oldest last

    oldest_idx = -1
    oldest_hash = None
    for h in full_hashes:
        try:
            idx = history.index(h)
        except ValueError:
            raise ValueError(
                f"Commit {h[:8]} is not in the current branch history.\n"
                "Make sure you are on the right branch."
            )
        if idx > oldest_idx:
            oldest_idx = idx
            oldest_hash = h
    return oldest_hash


def parent_hash(commit_hash: str) -> str:
    try:
        return git("rev-parse", f"{commit_hash}^").stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError(
            f"Commit {commit_hash[:8]} has no parent (it is the root commit). "
            "Cannot rebase from before the root."
        )


def _parse_commit_lines(text: str) -> list[dict]:
    commits = []
    for line in text.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        hash_, at, ct, subject = parts
        commits.append(
            {"hash": hash_, "author_ts": int(at), "committer_ts": int(ct), "subject": subject}
        )
    return commits


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
]


def parse_date(date_str: str, original_ts: int | None = None) -> int:
    """
    Parse a date string to a Unix timestamp.
    If only a date (no time) is given and original_ts is provided,
    the original time of day is preserved.
    """
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if fmt == "%Y-%m-%d" and original_ts is not None:
                orig = datetime.fromtimestamp(original_ts)
                dt = dt.replace(hour=orig.hour, minute=orig.minute, second=orig.second)
            return int(dt.timestamp())
        except ValueError:
            continue
    raise ValueError(
        f"Cannot parse date {date_str!r}.\n"
        "Accepted formats: YYYY-MM-DD  YYYY-MM-DDTHH:MM  YYYY-MM-DDTHH:MM:SS"
    )


def is_weekend(ts: int) -> bool:
    return datetime.fromtimestamp(ts).weekday() >= 5


def nearest_weekday(ts: int, direction: str) -> int:
    dt = datetime.fromtimestamp(ts)
    dow = dt.weekday()
    if dow == 5:    # Saturday
        delta = timedelta(days=2 if direction == "monday" else -1)
    elif dow == 6:  # Sunday
        delta = timedelta(days=1 if direction == "monday" else -2)
    else:
        return ts
    return int((dt + delta).timestamp())


def fmt_human(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%a %Y-%m-%d %H:%M")


def fmt_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Rebase machinery
# ---------------------------------------------------------------------------

def run_rebase(base_hash: str, changes: dict[str, int]) -> bool:
    """
    Run `git rebase -i base_hash`, injecting exec lines for commits in `changes`.
    `changes` maps full commit hash -> new Unix timestamp.
    Returns True on success.
    """
    # Write mapping file: full_hash TAB iso_date
    mapping_fd, mapping_path = tempfile.mkstemp(suffix=".redate-map")
    try:
        with os.fdopen(mapping_fd, "w") as mf:
            for full_hash, new_ts in changes.items():
                mf.write(f"{full_hash}\t{fmt_iso(new_ts)}\n")
    except Exception:
        os.unlink(mapping_path)
        raise

    # Write the GIT_SEQUENCE_EDITOR script.
    # It injects `exec env GIT_COMMITTER_DATE=... git commit --amend --no-edit --date=...`
    # after each pick line whose hash matches a commit in the mapping.
    # --date sets the author date; GIT_COMMITTER_DATE sets the committer date.
    seq_script = f"""\
#!/usr/bin/env python3
import sys

mapping = {{}}
with open({repr(mapping_path)}) as f:
    for line in f:
        line = line.strip()
        if line:
            h, d = line.split("\\t", 1)
            mapping[h] = d

todo = sys.argv[1]
with open(todo) as f:
    lines = f.readlines()

out = []
for line in lines:
    out.append(line)
    parts = line.split()
    if len(parts) >= 2 and parts[0] in ("pick", "p"):
        short = parts[1]
        for full_hash, new_date in mapping.items():
            if full_hash.startswith(short) or short.startswith(full_hash[: len(short)]):
                out.append(
                    f"exec env GIT_COMMITTER_DATE='{{new_date}}' "
                    f"git commit --amend --no-edit --allow-empty --date='{{new_date}}'\\n"
                )
                break

with open(todo, "w") as f:
    f.writelines(out)
"""

    seq_fd, seq_path = tempfile.mkstemp(suffix=".redate-seq.py")
    try:
        with os.fdopen(seq_fd, "w") as sf:
            sf.write(seq_script)
        os.chmod(
            seq_path,
            os.stat(seq_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
        )
    except Exception:
        os.unlink(seq_path)
        os.unlink(mapping_path)
        raise

    try:
        env = os.environ.copy()
        env["GIT_SEQUENCE_EDITOR"] = f"python3 {seq_path}"
        result = subprocess.run(["git", "rebase", "-i", base_hash], env=env)
        return result.returncode == 0
    finally:
        for path in (mapping_path, seq_path):
            try:
                os.unlink(path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

def confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite Git commit timestamps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Auto mode options
    parser.add_argument(
        "--range",
        default="@{u}..HEAD",
        dest="range_spec",
        metavar="RANGE",
        help="Commit range for auto weekend detection (default: @{u}..HEAD)",
    )
    parser.add_argument(
        "--move-to",
        choices=["monday", "friday"],
        default="monday",
        dest="move_to",
        help="Auto mode: move weekend commits to Monday (default) or Friday",
    )
    # Manual mode option
    parser.add_argument(
        "--set",
        nargs=2,
        metavar=("HASH", "DATE"),
        action="append",
        dest="sets",
        help="Rewrite HASH to DATE. Repeatable. DATE: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying history",
    )
    args = parser.parse_args()

    # Sanity checks
    try:
        git("rev-parse", "--git-dir")
    except subprocess.CalledProcessError:
        print("Error: not inside a git repository.", file=sys.stderr)
        sys.exit(1)

    status = git("status", "--porcelain")
    if status.stdout.strip():
        print(
            "Error: working tree has uncommitted changes.\n"
            "Commit or stash them before redating.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build changes dict: full_hash -> new_ts
    changes: dict[str, int] = {}

    # ── Manual mode ──────────────────────────────────────────────────────────
    if args.sets:
        for short_hash, date_str in args.sets:
            try:
                full_hash = resolve_hash(short_hash)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            commit = get_commit(full_hash)
            try:
                new_ts = parse_date(date_str, original_ts=commit["author_ts"])
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            changes[full_hash] = new_ts

    # ── Auto mode (weekend detection) ────────────────────────────────────────
    else:
        try:
            auto_commits = get_commits_in_range(args.range_spec)
        except subprocess.CalledProcessError as exc:
            print(
                f"Error listing commits for range '{args.range_spec}':\n{exc.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

        if not auto_commits:
            print(f"No commits found in range '{args.range_spec}'.")
            return

        for c in auto_commits:
            if is_weekend(c["author_ts"]):
                changes[c["hash"]] = nearest_weekday(c["author_ts"], args.move_to)

        if not changes:
            print(f"No weekend commits found in range '{args.range_spec}'.")
            return

    # ── Report planned changes ────────────────────────────────────────────────
    print(f"Will rewrite {len(changes)} commit(s):\n")
    for full_hash, new_ts in changes.items():
        commit = get_commit(full_hash)
        print(
            f"  {full_hash[:8]}  "
            f"{fmt_human(commit['author_ts'])}  →  {fmt_human(new_ts)}  "
            f"{commit['subject'][:55]}"
        )
    print()

    if args.dry_run:
        print("Dry run — no history was modified.")
        return

    if not confirm("Rewrite these commits?"):
        print("Aborted.")
        return

    # ── Determine rebase base ─────────────────────────────────────────────────
    if args.sets:
        # Manual mode: derive base from oldest commit in the set
        try:
            oldest = find_oldest_ancestor(list(changes.keys()))
            base_hash = parent_hash(oldest)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Auto mode: derive base from range spec
        if ".." not in args.range_spec:
            print(
                "Error: cannot determine rebase base — range must contain '..'",
                file=sys.stderr,
            )
            sys.exit(1)
        base_ref = args.range_spec.split("..")[0].strip()
        try:
            base_hash = git("rev-parse", base_ref).stdout.strip()
        except subprocess.CalledProcessError:
            print(f"Error: cannot resolve base ref '{base_ref}'", file=sys.stderr)
            sys.exit(1)

    # ── Run the rebase ────────────────────────────────────────────────────────
    num_affected = len(changes)
    success = run_rebase(base_hash, changes)

    if not success:
        print(
            "\nRebase did not complete cleanly.\n"
            "Run 'git rebase --abort' to restore the original state.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nDone — timestamps updated.\n")
    git(
        "log",
        "--format=%h  %ad  %s",
        "--date=format:%a %Y-%m-%d %H:%M",
        f"-n{num_affected + 2}",
        capture=False,
    )


if __name__ == "__main__":
    main()
