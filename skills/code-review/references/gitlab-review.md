# GitLab MR Review Workflow

Use for GitLab merge request reviews. Apply `review-methodology.md` throughout.

## 1. Gather MR context

Run inside the target repository so `glab` resolves `projects/:id`. Avoid `--repo` unless the user explicitly targets another repository.

```bash
glab mr view <MR_IID> --output json > /tmp/pi_mr_<MR_IID>.json
glab mr diff <MR_IID> --color=never > /tmp/pi_mr_<MR_IID>_diff.txt
glab api "projects/:id/merge_requests/<MR_IID>/discussions?sort=asc&per_page=100" > /tmp/pi_mr_<MR_IID>_discussions.json
```

If JSON is incomplete/unreadable:

```bash
glab mr view <MR_IID> > /tmp/pi_mr_<MR_IID>.txt
glab mr view <MR_IID> --comments > /tmp/pi_mr_<MR_IID>_comments.txt
```

Inspect state and metadata before spending substantial effort. If the MR is closed, draft, automated, trivial, or already reviewed, do not silently skip an explicit request. State the condition and use a proportionate review or ask whether a full review is still wanted. Earlier reviews are deduplication context, not a reason to refuse re-review.

Record existing resolved/unresolved discussions and prior self-authored findings so new findings do not duplicate them.

## 2. Fetch Jira context when present

Extract Jira keys from title, description, branch name, and diff:

```bash
~/.pi/agent/skills/code-review/scripts/extract_jira_key.sh /tmp/pi_mr_<MR_IID>.json
```

When found, use `jira-task-context`; its helper is:

```bash
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<JIRA_KEY_OR_URL>" --depth 1 --comments 1000 --max-issues 20 --max-text-chars 20000
```

Use summary, description, acceptance criteria, comments, and linked issues to check requirements and scope drift.

## 3. Inspect the diff and surrounding code

Read the diff and identify touched files:

```bash
rg '^\+\+\+ b/' /tmp/pi_mr_<MR_IID>_diff.txt
```

Build the changed-behavior inventory required by the shared methodology. Inspect full changed files, direct callers/callees, relevant tests, related config/DI/routing/migration/localization/permission files, and similar implementations when needed.

Read local files only when the checkout corresponds to the MR source or target code under review. If surrounding context requires checking out the MR branch, ask before `glab mr checkout <MR_IID>`; never switch a dirty working tree without explicit authorization.

Apply scoped `AGENTS.md`, `CLAUDE.md`, `.ai-rules/`, and equivalent guidance.

## 4. Review, consolidate, and refresh

Apply the shared independent-pass calibration, review focus, candidate verification, confidence threshold, and severity rules.

Immediately before presenting findings, refresh MR metadata and discussions. If the head SHA changed, refresh the diff and revalidate candidates. Drop findings now covered by an unresolved discussion.

## 5. Present before posting

Use the shared output format. Do not post anything yet.

After presenting every reportable finding:

- Call `review_findings_selector` immediately unless the user already explicitly authorized posting every reportable finding.
- Pass every finding to the selector so the user can choose.
- Post only selected findings, or all findings when that exact action was directly requested.
- If no reportable findings exist, do not call the selector.

If posting is authorized, read `posting-findings.md` completely before any GitLab mutation.
