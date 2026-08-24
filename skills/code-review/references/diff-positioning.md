# Diff Positioning

GitLab expects the real file line number in `position.new_line`, not the rendered line number from the diff output.

Unified diff hunk rules:
- Hunk header format: `@@ -old_start,old_count +new_start,new_count @@`
- `+` lines increment the new-file line counter
- Context lines increment the new-file line counter
- `-` lines do not increment the new-file line counter
- For new files, `@@ -0,0 +1,N @@` starts at line 1

Use the checked-in helper:

```bash
python3 ~/.pi/agent/skills/code-review/scripts/find_diff_line.py \
  --diff-file /tmp/mr_diff.txt \
  --path path/to/file.swift \
  --needle "exact added line text"
```

The script prints the matching `new_line`.

If there are multiple identical matches, disambiguate with:
- `--occurrence N`
- a more precise needle

Do not guess line numbers from visual diff output.

## Context lines vs added lines

The GitLab discussion API only accepts `new_line` alone for **added lines** (`+` prefix in the diff).
For context lines (unchanged, space prefix), GitLab also requires `old_line` — omitting it returns
`line_code: ["can't be blank"]` (HTTP 400). The script emits a stderr warning when the needle
matches a context line.

**Rule: always use a needle that is an added (`+`) line.** When your natural target is a context
line, pick the nearest added line in the same hunk that is semantically close to the issue — e.g.
the function or `case` declaration just above it.
