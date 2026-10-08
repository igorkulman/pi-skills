---
name: mr-comment-resolution
description: Analyze and address GitLab merge request reviewer comments. Use when the user asks to analyze MR comments, implement review comments, reply to comments, mark comments as done, or resolve/respond to GitLab MR discussions.
compatibility: Requires git and authenticated glab for the relevant GitLab host. For iOS/Xcode verification, prefer available Xcode MCP tools; use xcodebuild-xcsift only as a fallback.
---

# MR Comment Resolution

Use this skill to turn GitLab MR reviewer comments into a safe, auditable workflow: fetch discussions, understand what each comment asks for, inspect code read-only, implement explicitly requested fixes, verify them, optionally commit them, and post replies only when that external action is explicitly requested.

## Core rules

- Use `gitlab-glab` / `glab` for all GitLab MR data and comment posting.
- Start read-only unless the user explicitly says to implement now, fix the comments, reply, or equivalent.
- Do not edit code, stage, commit, push, resolve threads, or post GitLab replies during the analysis phase.
- Do not post externally visible GitLab replies until the user explicitly approves the exact posting action or requests it in the same message.
- Keep discussion IDs and note IDs distinct:
  - discussion ID: used for replying to a thread via `/discussions/<discussion_id>/notes`
  - note ID: the individual comment inside a discussion
- Prefer replying to the discussion thread, not creating a detached MR-level note, when the original concern is a thread.
- For fixed comments, use the user's requested wording if provided (for example `hotovo`). Otherwise propose concise wording and ask.
- For explanation-only comments, draft a factual answer grounded in the code/MR history.
- For actionable comments, implement the requested behavior, not merely the wording of the comment.
- Preserve unrelated local or user changes. Do not stage or commit unrelated files.
- If asked to commit fixes, use the `git-commit` skill. Keep a production change and its focused regression tests in the same commit unless either change is independently meaningful or the user requests a separate commit.

## 1. Establish repository and MR context

Run read-only checks first:

```bash
command -v glab && glab --version
glab auth status
git remote -v
git branch --show-current
git status --short
```

Determine the MR IID:

- From a URL, use the number after `/merge_requests/`.
- From an IID, use it directly in the current repo.
- If ambiguous, ask which MR to use.

Fetch MR metadata and discussions:

```bash
glab mr view <iid> --output json | jq '{iid,title,state,source_branch,target_branch,author,reviewers,assignees,draft,work_in_progress,merge_status,detailed_merge_status,web_url}'

glab api projects/:fullpath/merge_requests/<iid>/discussions --paginate --output ndjson \
  | jq -s 'flatten | map({id, individual_note, notes: [.notes[] | {id,type,body,author: .author.username,created_at,updated_at,system,resolvable,resolved,resolved_by: (.resolved_by.username? // null),position}]})'
```

When useful, also fetch the MR diff:

```bash
glab mr diff <iid> --color=never > /tmp/pi_mr_<iid>_diff.txt
```

## 2. Classify comments

Ignore system notes except when they affect state, such as resolved/unresolved changes.

For every non-system reviewer comment, classify it as one of:

- `explanation`: asks a question or needs context, no code change required.
- `actionable`: asks for a code/test/doc change.
- `mixed`: requires both an answer and a code change.
- `stale/already-fixed`: appears addressed by current code; verify before saying so.
- `unclear`: ambiguous; ask the user or propose an interpretation.

For each comment capture:

- discussion ID
- note ID
- author
- resolved state, if resolvable
- file and line/range, if diff note
- exact reviewer request
- proposed response text, if obvious

## 3. Read-only code analysis before implementation

For actionable or mixed comments:

1. Read the affected file around the commented line.
2. Read related protocols, call sites, test doubles, and existing tests.
3. Search for symbols that need renaming or behavior changes.
4. Check project instructions and relevant docs for the type of change.
5. Present a short plan:
   - problem understanding
   - comments to address
   - files likely to change
   - implementation approach
   - risks/unknowns
   - verification plan
6. If implementation was not explicitly requested, ask: `Proceed with implementation?`

If the user already explicitly said to implement or fix the comments, inspect relevant context first and then proceed without another approval pause.

## 4. Implement fixes

When implementation is authorized under the global policy:

- Make precise edits with `edit` for existing files.
- Keep renames consistent across protocols, implementations, call sites, mocks, and tests.
- Remove comments only when requested or when they become redundant.
- Strengthen tests to assert exact behavior and state transitions, not just presence or partial values.
- For regression comments, prefer tests that demonstrate:
  - previous/cached state `X`
  - operation under review
  - resulting/new state `Y`
  - failure paths preserve the correct previous state when relevant

After changes, search for stale names or comments:

```bash
rg '<oldSymbolOrPhrase>'
rg '<newSymbolOrPhrase>'
```

## 5. Verify

Choose verification appropriate to the project and comment scope.

For iOS/Xcode projects, prefer the available Xcode MCP build, test, and diagnostic tools. Discover native tools and inspect their current schemas rather than assuming mirrored tool names. Choose focused tests for the changed behavior; a successful build is not proof that tests or product behavior are correct.

Use `xcodebuild-xcsift` only when Xcode MCP is unavailable or cannot perform the required operation. Do not rerun a real MCP-reported build/test failure through the shell, and never run the MCP and shell routes concurrently. For the shell fallback, load that skill and pipe all `xcodebuild` output to `xcsift`:

```bash
set -o pipefail
xcodebuild \
  -project <ProjectName>.xcodeproj \
  -scheme "<Scheme>" \
  -destination 'platform=iOS Simulator,name=<Device>' \
  -only-testing:<TestTarget>/<SuiteName> \
  test \
  2>&1 | xcsift --quiet
```

If a requested targeted test is not in the active scheme/test plan, inspect the configured targets/test plan and use the correct target through the chosen route. Report the tool invocation or command, status, failed tests, diagnostics, and warning count when available. State exactly why tests were not run if verification is blocked.

For visual SwiftUI fixes, render and inspect representative previews when Xcode MCP is available, comparing the snapshot against the requested state or supplied design. For interaction fixes, follow `device-interaction` for runtime verification when the necessary tools are available; do not claim runtime correctness from a build or static inspection alone.

Before finalizing implementation, run:

```bash
git diff --check
git diff --stat
git diff
```

## 6. Optional commit workflow

If the user asks to commit after fixes, load and follow the `git-commit` skill.

Keep each production change with the focused regression tests that verify it. Split commits only when the changes are independently meaningful or the user requests a separate commit.

Use descriptive messages that describe the actual change, not `Address review feedback`.

## 7. Reply to comments

Only post replies after explicit approval, or when the user directly asks to reply/post.

### Draft replies

Use concise, factual wording:

- Explanation comments: answer the actual question with technical context.
- Fixed actionable comments: use the user's requested done text, often `hotovo`, or a short summary such as `Hotovo, upravené v <commit/file>.`
- If verification matters, mention it briefly only when useful.

### Post replies to discussions

Use the discussion ID, not the note ID:

```bash
glab api --method POST \
  projects/:fullpath/merge_requests/<iid>/discussions/<discussion_id>/notes \
  --raw-field body='<reply text>'
```

For multiple replies, prefer one command per discussion and capture returned IDs:

```bash
glab api --method POST projects/:fullpath/merge_requests/<iid>/discussions/<discussion_id>/notes --raw-field body='hotovo' > /tmp/pi_mr_<iid>_reply_<discussion_id>.json
jq -r '.id, .body' /tmp/pi_mr_<iid>_reply_<discussion_id>.json
```

### Resolve threads

Do not resolve threads unless the user explicitly asks to resolve them.

When resolution is explicitly authorized:

```bash
glab api --method PUT \
  projects/:fullpath/merge_requests/<iid>/discussions/<discussion_id> \
  --field resolved=true
```

## 8. Final response

Summarize:

- comments analyzed
- changes made, if any
- verification run and result
- commits created, if any
- GitLab replies posted, including note IDs or a concise confirmation
- any remaining unresolved comments, rebase needs, or blockers
