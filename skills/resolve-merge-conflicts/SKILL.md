---
name: resolve-merge-conflicts
description: Resolve every conflict in an ongoing Git rebase or merge and continue the operation to completion without routine confirmation prompts.
compatibility: Requires git and an already-running rebase or merge. The invocation authorizes resolving conflicts, staging the resolved conflict files, and continuing the current operation, but never pushing.
disable-model-invocation: true
---

# Resolve Merge Conflicts

Complete an already-running rebase or merge. Invocation is authorization to resolve its conflicts, stage the resolved conflict files, and repeatedly continue until Git reports that the operation has finished. Do not pause for confirmation between conflict rounds.

## Automation contract

- Infer routine resolutions from the code, the replayed commit, target-branch history, tests, and project guidance.
- Ask only when competing behaviors are materially incompatible and primary sources do not establish which one is intended, or when completion would require a destructive choice unrelated to normal conflict resolution.
- If a decision is required, ask all currently known blocking questions together. After the user answers, resume the loop automatically without requesting another general confirmation.
- Preserve unrelated working-tree changes. Never stash, reset, abort, force-push, or stage unrelated files.
- Do not start a new rebase or merge. If none is in progress, stop and report that clearly.

## 1. Establish the operation

Inspect Git status, the in-progress rebase/merge metadata, unmerged paths, and applicable repository instructions. Determine why Git stopped without asking the user for information already recorded by Git.

For a rebase, inspect the commit currently being replayed with `git rebase --show-current-patch` and relevant history. Remember that during a rebase Git's ours/theirs labels are counterintuitive: the current rebased target is one side and the commit being replayed is the other. Reason from intent and content, not the labels.

Completion criterion: the operation type, current replayed change, conflicted paths, and any unrelated work are accounted for.

## 2. Resolve the current stop

For every unmerged path:

1. Read the complete conflict and enough surrounding code to understand both behaviors.
2. Trace each side to primary sources where useful: commit messages and diffs, nearby history, Jira/MR context already available, tests, and project documentation.
3. Preserve both intents when compatible. When they conflict, choose the behavior consistent with the target branch's current contracts and the replayed commit's actual purpose. Do not invent unrelated behavior.
4. Handle modify/delete, rename, generated-file, and binary conflicts according to the same intent, rather than selecting a side mechanically.
5. Remove conflict markers and verify that Git reports no unmerged entries.
6. Stage exactly the files resolved for this conflict round. Avoid broad staging commands such as `git add -A`.

Use `git diff --check` and the unmerged-path list as gates before continuing. A clean marker check alone is not proof that the semantic resolution is correct; inspect the resulting staged diff as well.

Completion criterion: every conflict in the current round is semantically resolved, no unmerged entries remain, and only operation-related paths were staged.

## 3. Continue until finished

Continue non-interactively so Git reuses the existing commit message instead of opening an editor:

```bash
GIT_EDITOR=true git rebase --continue
# or, for an ongoing merge
GIT_EDITOR=true git merge --continue
```

If Git stops on another conflict, return immediately to step 2. Repeat for every conflict round without asking for routine permission.

If a replayed commit becomes empty, verify that all of its intended behavior is already present in the rebased result. When it is, skip that now-redundant commit and continue automatically. If behavior would be lost, resolve that discrepancy instead of skipping.

Do not bypass failing hooks or use destructive recovery commands. Stop only when an error cannot be resolved within the ongoing operation, and report the exact blocker and Git state.

Completion criterion: Git reports the rebase or merge completed and no operation metadata or unmerged entries remain.

## 4. Verify and report

Inspect final status and recent history. Run focused verification appropriate to the resolved behavior when practical; when invoking `xcodebuild`, use the `xcodebuild-xcsift` workflow. Do not amend, create an extra commit, push, or force-push unless separately requested.

Report concisely:

- that the operation completed, or the exact blocker if it did not
- conflicts resolved and any meaningful resolution choices
- empty commits skipped, if any, and why they were redundant
- verification run and its result
- final Git status
