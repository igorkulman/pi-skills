---
name: jira-task-context
description: Fetch Jira task details from a Jira issue URL or key, follow linked Jira issues, and inspect referenced Confluence/Figma links. Use at the start of flows that begin from a Jira task, when the user provides a Jira URL/key, or when Jira issue context, dependencies, blockers, parent/subtasks, linked issues, Confluence specs, or Figma designs are needed.
compatibility: Requires network access to Jira. Uses Python 3 and Jira REST API via the bundled script. Authentication can come from JIRA_EMAIL + JIRA_API_TOKEN for Jira Cloud, or JIRA_BEARER_TOKEN/JIRA_PAT for Jira Data Center/PAT setups.
---

# Jira Task Context

Use this skill when the user gives a Jira URL/key or asks to start from a Jira task. The goal is to collect the root task details and linked Jira issue context before doing the rest of the work.

## What to do

1. Extract the Jira issue key and base URL from the user-provided URL/key.
2. Fetch the root issue details.
3. Follow linked Jira issues at least one hop by default:
   - explicit Jira issue links (`blocks`, `is blocked by`, `relates to`, etc.)
   - parent issue
   - subtasks
   - Jira issue keys/URLs referenced in the description or recent comments
4. Extract important non-Jira links from the root and followed Jira issues, especially:
   - Confluence / Atlassian wiki pages
   - Figma design, FigJam, prototype, or file links
   - product specs, API docs, screenshots, videos, or other implementation references
5. Follow those external links read-only when access/tools are available:
   - For Confluence pages, use `web_fetch` when authenticated access works; summarize requirements, decisions, constraints, screenshots/assets mentioned, and open questions.
   - For Figma links, prefer the available Figma MCP/tools to inspect the referenced file/frame/prototype. If MCP access is unavailable, try `web_fetch` for page metadata and clearly report that visual/design details could not be inspected.
   - Do not mutate Confluence, Figma, Jira, or any external system.
   - Keep traversal bounded to links directly referenced by the collected Jira issues unless the user asks for deeper discovery.
6. Summarize the collected Jira and external-artifact context for the user before moving on.

## Preferred command

From any working directory, run the bundled helper script:

```bash
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<jira-url-or-key>" --depth 1 --comments 5
```

Useful variants:

```bash
# Root issue only
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<jira-url-or-key>" --depth 0

# Follow linked issues two hops, with a strict cap
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<jira-url-or-key>" --depth 2 --max-issues 30

# If the user gave only a key, provide or rely on JIRA_BASE_URL
JIRA_BASE_URL="https://your-domain.atlassian.net" python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "ABC-123"

# Machine-readable output
python3 ~/.pi/agent/skills/jira-task-context/scripts/jira_issue_context.py "<jira-url-or-key>" --format json
```

## Authentication

Do not ask the user to paste tokens into chat and never print token values.

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

If authentication fails, tell the user which variable names are needed, not the secret values.

## Output expectations

After fetching, present a concise context summary containing:

- root issue key, title, URL, type, status, priority, assignee, reporter
- description / acceptance criteria / important comments
- linked issues with relation, status, and why they matter
- blockers/dependencies inferred from issue link relations
- Confluence/spec links followed, with relevant requirements or decisions found
- Figma/design links followed, with referenced file/frame/prototype and visual requirements found
- inaccessible or unfollowed links, with the reason and whether they block implementation
- open questions or missing information

Then continue with the user's requested flow.

## Safety and privacy

- Jira data may contain confidential product/customer information. Only fetch and summarize what is needed for the task.
- Keep max issue limits reasonable (`--max-issues`) to avoid accidentally crawling too much Jira content.
- Do not mutate Jira issues unless the user explicitly asks. This skill is read-only by default.
