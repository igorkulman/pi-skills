---
name: jira-update
description: Update Jira tickets from the terminal using Jira REST API. Use when the user asks to edit a Jira issue description, replace a named section such as POEditor Strings, add comments, or otherwise mutate Jira ticket fields.
compatibility: Requires network access to Jira and Jira auth via JIRA_EMAIL + JIRA_API_TOKEN for Jira Cloud, or JIRA_BEARER_TOKEN/JIRA_PAT for PAT setups. Uses Python 3 and standard library only.
---

# Jira Update

Use this skill when the user explicitly asks to update/mutate a Jira ticket.

## Safety rules

- Jira mutations are externally visible. Ask for confirmation before updating Jira unless the user already gave an explicit update instruction in the same request.
- Never ask the user to paste tokens into chat and never print token values.
- Before mutating, fetch the current issue so you know the current description/status and can preserve unrelated content.
- Prefer small, targeted updates: replace a named section, append a comment, or update a specific field.
- After mutating, verify by fetching the issue again and summarizing the changed section/field.

## Authentication

Supported environment variables:

```bash
# Jira Cloud basic auth
export JIRA_EMAIL="name@example.com"
export JIRA_API_TOKEN="..."

# Jira Data Center / PAT bearer auth
export JIRA_BEARER_TOKEN="..."
# or
export JIRA_PAT="..."

# Required only when the user supplies an issue key instead of a full URL
export JIRA_BASE_URL="https://your-domain.atlassian.net"
```

If auth fails, tell the user which variable names are needed, not secret values.

## Read issue context first

Use the existing Jira context helper for read-only context:

```bash
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<jira-url-or-key>" --depth 0 --comments 5 --max-text-chars 20000
```

For machine-readable output:

```bash
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<jira-url-or-key>" --depth 0 --comments 5 --format json --max-text-chars 20000
```

## Replace a description section

Use the bundled helper to replace the content under a Jira description heading while preserving the rest of the description. The helper works with Atlassian Document Format (ADF), supports simple Markdown input, and issues a Jira REST `PUT /rest/api/3/issue/{key}`.

```bash
python3 ~/.pi/agent/skills/jira-update/scripts/jira_update_section.py \
  "<jira-url-or-key>" \
  --heading "POEditor Strings" \
  --markdown-file /tmp/poeditor-section.md
```

Dry-run first when practical:

```bash
python3 ~/.pi/agent/skills/jira-update/scripts/jira_update_section.py \
  "<jira-url-or-key>" \
  --heading "POEditor Strings" \
  --markdown-file /tmp/poeditor-section.md \
  --dry-run
```

Markdown supported by the helper:

- headings (`# Heading`, `## Heading`)
- paragraphs
- bullet lists (`- item`)
- simple pipe tables with a separator row
- inline code using backticks
- bold using `**text**`

Example section file:

```markdown
| Key | EN translation | Context |
|---|---|---|
| `dashboard_siri_tooltip_title` | Set up Siri Commands | TipKit title on Dashboard |

## Translator notes

- Keep `Siri` as Apple product name.
- Keep action labels short.
```

The helper finds the named heading and replaces content until the next heading of the same or higher level. If the heading is missing, it appends it by default. Use `--no-append-if-missing` to fail instead.

## Add a comment

Use Jira REST API directly with Python standard library or a short one-off script. Endpoint:

```text
POST /rest/api/3/issue/{issueKey}/comment
```

Payload shape:

```json
{
  "body": {
    "type": "doc",
    "version": 1,
    "content": [
      {
        "type": "paragraph",
        "content": [
          { "type": "text", "text": "Comment text" }
        ]
      }
    ]
  }
}
```

## Field updates

Use Jira REST API directly for targeted field changes:

```text
PUT /rest/api/3/issue/{issueKey}
```

Payload examples:

```json
{ "fields": { "summary": "New summary" } }
```

```json
{ "fields": { "description": { "type": "doc", "version": 1, "content": [] } } }
```

## Verification

After every update:

1. Fetch the issue again.
2. Confirm the changed section/field is present.
3. Report the issue key, URL, HTTP status, and concise summary of what changed.
