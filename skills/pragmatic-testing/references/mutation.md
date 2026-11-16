# Mutation recipe

Use this when a mutation check is warranted under the main skill's rules. It snapshots the file, applies one exact replacement, and restores the file even if the run fails or is interrupted.

## Shell-driven test runners

```bash
FILE=path/to/Production.swift
SNAPSHOT=$(mktemp)
cp "$FILE" "$SNAPSHOT"
HASH=$(shasum "$FILE" | cut -d' ' -f1)
trap 'cp "$SNAPSHOT" "$FILE"' EXIT INT TERM

python3 - "$FILE" <<'PY'
import sys
path = sys.argv[1]
old = "return lhs < rhs"   # the exact original code
new = "return lhs <= rhs"  # the named plausible mistake
source = open(path).read()
assert source.count(old) == 1, "mutation target must match exactly once"
open(path, "w").write(source.replace(old, new))
PY

run-the-focused-test-here || true   # the expected result is a failure

cp "$SNAPSHOT" "$FILE"
trap - EXIT INT TERM
[ "$(shasum "$FILE" | cut -d' ' -f1)" = "$HASH" ] && echo "restored"
```

Prefer an exact string replacement to `sed` patterns, because a pattern that silently matches nothing produces a vacuous green run.

## Tool-driven test runners

When tests run through a tool call, such as `xcode_test`, rather than in the same shell:

1. In one shell call, snapshot the file to a temporary path, record its hash, and apply the replacement with the exact-match assertion above.
2. Run only the focused test through the tool. Read the reported failures and confirm that the intended assertion failed.
3. In the next shell call, restore from the snapshot and compare the hash, even if the run failed, errored, or was cancelled.

Do not start other edits, builds, or test runs between steps 1 and 3. If the session may be interrupted, say which file is mutated and where its snapshot is before running the test.
