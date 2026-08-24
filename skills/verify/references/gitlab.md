# GitLab Verification Workflow

Use for GitLab MR URLs or IIDs. Apply the shared scope, evidence, authorization, and mutation rules from `../SKILL.md`.

## 1. Validate repository and fetch state

Extract the IID after `/merge_requests/` for URLs. Run inside the target repository so `glab` resolves `projects/:id`; avoid `--repo` unless another repository was explicitly requested.

```bash
git remote -v
glab auth status
glab mr view <MR_IID> --output json > /tmp/pi_verify_mr_<MR_IID>.json
glab mr diff <MR_IID> --color=never > /tmp/pi_verify_mr_<MR_IID>_diff.txt
glab api --paginate "projects/:id/merge_requests/<MR_IID>/discussions?sort=asc&per_page=100" > /tmp/pi_verify_mr_<MR_IID>_discussions.json
```

If `glab mr view` resolves a project/MR different from the supplied URL, stop and ask the user to run from the correct repository.

Determine the authenticated username from `glab auth status` and use it as `<SELF_USERNAME>`.

## 2. Identify scope

Open self-authored resolvable discussions:

```bash
jq --arg self "<SELF_USERNAME>" '[.[] | select(.resolvable == true and (.resolved != true) and (.notes[0].author.username == $self))]' /tmp/pi_verify_mr_<MR_IID>_discussions.json
```

Other authors' open resolvable count:

```bash
jq --arg self "<SELF_USERNAME>" '[.[] | select(.resolvable == true and (.resolved != true) and (.notes[0].author.username != $self))] | length' /tmp/pi_verify_mr_<MR_IID>_discussions.json
```

Compact in-scope list:

```bash
jq -r --arg self "<SELF_USERNAME>" '.[] | select(.resolvable == true and (.resolved != true) and (.notes[0].author.username == $self)) | [.id, (.notes[0].path // "-"), (.notes[0].line // .notes[0].new_line // .notes[0].old_line // "-"), (.notes[0].author.username // "-"), (.notes[0].body // "" | gsub("\\n"; " ") | .[0:120])] | @tsv' /tmp/pi_verify_mr_<MR_IID>_discussions.json
```

If no in-scope discussions remain, skip assessment and evaluate approval eligibility. Do not assess/resolve other authors' threads.

Useful fields:

- `discussion.id` for resolution
- `resolvable` / `resolved` for state
- `notes[].body` for concern/replies
- `notes[].path`, `line`, `new_line`, `old_line`, and `position` for diff context

## 3. Assess and present

For each in-scope discussion, apply the shared classification contract using replies, latest MR diff, and local surrounding code when appropriate.

Present:

```markdown
## Verification scope
- Target: GitLab MR !<MR_IID>
- Open in-scope resolvable threads created by me: <count>
- Other authors' open resolvable threads (reported only): <count>

## Thread assessment
1. `DISCUSSION_ID` — `path:line` — <concern excerpt>
   - Status: Addressed / Not addressed / Uncertain
   - Evidence: <concrete replies/diff/code evidence>
   - Proposed action: Resolve / Leave open

## Approval gate
- Remaining blockers if proposed actions are applied: <none/list>
- Recommendation: Approve after resolving addressed threads / Do not approve
- Authorization: Already requested / Ask to resolve and approve
```

Follow the shared authorization gate before continuing.

## 4. Resolve authorized addressed discussions

```bash
glab api --method PUT "projects/:id/merge_requests/<MR_IID>/discussions/<DISCUSSION_ID>" -F resolved=true
```

Resolve only discussions whose first note belongs to the authenticated user and whose status is Addressed. Check every result.

## 5. Re-check and optionally approve

```bash
glab api --paginate "projects/:id/merge_requests/<MR_IID>/discussions?sort=asc&per_page=100" > /tmp/pi_verify_mr_<MR_IID>_discussions_after.json
jq --arg self "<SELF_USERNAME>" '[.[] | select(.resolvable == true and (.resolved != true) and (.notes[0].author.username == $self))] | length' /tmp/pi_verify_mr_<MR_IID>_discussions_after.json
```

If the count is zero and approval was explicitly requested:

```bash
glab mr approve <MR_IID>
```

Otherwise do not approve. Report remaining in-scope discussion IDs/reasons and the count of other authors' open resolvable discussions.

## 6. Report

Summarize initial in-scope count, resolved/open thread IDs with concise excerpts, other-author count, approval status, and API failures.
