# Posting GitLab Review Findings

Read this only after findings have been selected for posting or the user explicitly requested posting every reportable finding. Posting is externally visible.

Before posting, read these existing references completely:

- `gitlab-inline-comments.md`
- `diff-positioning.md`

Do not duplicate an equivalent unresolved discussion. If a prior self-authored finding appears fixed, mention it in the summary and ask before resolving unless resolution was explicitly requested.

Comment bodies must contain only the finding prose: problem, impact, evidence as needed, and suggested fix. Do not include severity labels or bold title headers.

## 1. Resolve an exact added line

Map every selected finding to a real added line in the latest diff:

```bash
python3 ~/.pi/agent/skills/code-review/scripts/find_diff_line.py \
  --diff-file /tmp/pi_mr_<MR_IID>_diff.txt \
  --path path/to/file.swift \
  --needle "exact added line text"
```

The needle should match a `+` line. If the natural target is context and the helper warns, use the nearest semantically relevant added line in the same hunk or ask whether to post a general MR note. Never guess from rendered diff line numbers.

## 2. Fetch latest diff-version SHAs

```bash
~/.pi/agent/skills/code-review/scripts/read_mr_versions.sh <MR_IID>
```

Use `base_commit_sha`, `head_commit_sha`, and `start_commit_sha`.

## 3. Publish one GitLab review

Use draft notes, then bulk-publish, matching GitLab's **Start a review / Submit review** flow. This produces one review notification instead of one per immediate discussion.

Write the selected findings to `/tmp/pi_mr_<MR_IID>_comments_to_post.json`:

```json
[
  {"path": "path/to/file.swift", "line": 42, "body": "Comment text here"}
]
```

Run:

```bash
python3 ~/.pi/agent/skills/code-review/scripts/post_inline_comments.py \
  --mr <MR_IID> \
  --base-sha <BASE_SHA> \
  --head-sha <HEAD_SHA> \
  --start-sha <START_SHA> \
  --comments-file /tmp/pi_mr_<MR_IID>_comments_to_post.json
```

The helper aborts when the current user already has draft notes because GitLab `bulk_publish` publishes all pending drafts on the MR. Use `--allow-existing-drafts` only when the user explicitly agrees to publish those existing drafts too.

Use the same JSON/helper flow for a single comment. Do not post directly to `/discussions` unless the user explicitly requests immediate comments rather than one review.

Afterward, report each `file:line`, its short issue summary, and whether it was published in one GitLab review. Check command/API results and never claim success after a failure.
