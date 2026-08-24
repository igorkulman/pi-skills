# GitLab Inline Review Comment Notes

Post review findings through GitLab draft notes, not directly through immediate discussions.

The desired flow is the same as the GitLab UI's **Start a review** / **Submit review** behavior:

1. Create each inline finding as an unpublished draft note.
2. Publish all pending draft notes together with `bulk_publish`.

This lets GitLab send a single review notification email with the review comments attached instead of one notification per immediate comment.

## Create draft inline comments

Draft notes are created with:

```bash
glab api --method POST \
  --header content-type:application/json \
  --input payload.json \
  projects/:id/merge_requests/<MR_NUMBER>/draft_notes
```

The payload uses `note` for the text and must include a `position` object for inline comments:

```json
{
  "note": "Comment text here",
  "position": {
    "base_sha": "<BASE_SHA>",
    "head_sha": "<HEAD_SHA>",
    "start_sha": "<START_SHA>",
    "position_type": "text",
    "new_path": "path/to/file.swift",
    "old_path": "path/to/file.swift",
    "new_line": 183
  }
}
```

Use the latest diff version SHAs. Fetch them with:

```bash
~/.pi/agent/skills/code-review/scripts/read_mr_versions.sh <MR_NUMBER>
```

## Publish the review

Publish all pending draft notes for the current user on the MR with:

```bash
glab api --method POST \
  projects/:id/merge_requests/<MR_NUMBER>/draft_notes/bulk_publish
```

Important: `bulk_publish` publishes all pending draft notes belonging to the current user on that MR, including drafts created manually in the UI before the script ran. The posting script checks for pre-existing drafts and aborts unless `--allow-existing-drafts` is passed.

## Helper script

Use the helper to create all selected inline findings as draft notes and publish them together:

```bash
python3 ~/.pi/agent/skills/code-review/scripts/post_inline_comments.py \
  --mr <MR_NUMBER> \
  --base-sha <BASE_SHA> \
  --head-sha <HEAD_SHA> \
  --start-sha <START_SHA> \
  --comments-file /tmp/pi_mr_<MR_NUMBER>_comments_to_post.json
```

The comments file must be a JSON array:

```json
[
  {"path": "path/to/file.swift", "line": 183, "body": "Comment text here"}
]
```

Known failures:
- Nested `--raw-field` syntax does not create inline comments correctly.
- Omitting `--header content-type:application/json` for JSON payloads often causes `415 Unsupported Content-Type`.
- Wrong SHAs or wrong `new_line` usually cause GitLab to reject the inline position.
- Existing user drafts cause the helper to abort by default to avoid accidentally publishing unrelated pending review comments.
