#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map added or context line text in a unified diff to a GitLab new_line.")
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--path", required=True, help="Target file path as it appears in the diff after b/")
    parser.add_argument("--needle", required=True, help="Line text to match, without diff prefix; leading/trailing whitespace is ignored")
    parser.add_argument("--occurrence", type=int, default=1, help="1-based occurrence for repeated matches")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lines = Path(args.diff_file).read_text(encoding="utf-8").splitlines()

    target_headers = {f"+++ b/{args.path}", f"+++ {args.path}"}
    in_file = False
    new_line = None
    match_count = 0

    for line in lines:
        if line.startswith("diff --git ") or line.startswith("--- "):
            in_file = False
            new_line = None
            continue

        if line in target_headers:
            in_file = True
            continue

        if not in_file:
            continue

        if line.startswith("@@ "):
            match = HUNK_RE.match(line)
            if not match:
                continue
            new_line = int(match.group(1))
            continue

        if new_line is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            text = line[1:]
            if text.strip() == args.needle.strip():
                match_count += 1
                if match_count == args.occurrence:
                    print(new_line)
                    return 0
            new_line += 1
            continue

        if line.startswith(" "):
            text = line[1:]
            if text.strip() == args.needle.strip():
                match_count += 1
                if match_count == args.occurrence:
                    print(new_line, file=sys.stdout)
                    print(
                        f"WARNING: matched a context line (not an added line) at new_line={new_line}. "
                        "GitLab requires old_line too for context lines — posting with only new_line will "
                        "fail with 'line_code can\\'t be blank'. "
                        "Use a needle that matches a nearby added (+) line instead.",
                        file=sys.stderr,
                    )
                    return 0
            new_line += 1
            continue

        if line.startswith("-") and not line.startswith("---"):
            continue

    print(f"no match found for path={args.path!r} needle={args.needle!r} occurrence={args.occurrence}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
