---
name: gitlab-glab
description: Use GitLab from the terminal with the glab CLI. Use when the user asks about GitLab projects, merge requests, issues, CI/CD pipelines, jobs, labels, releases, repository metadata, or GitLab API queries.
compatibility: Requires the glab CLI installed and authenticated for the relevant GitLab host.
---

# GitLab via glab

Use `glab` for GitLab operations instead of scraping the web or guessing URLs. Prefer non-interactive, scriptable commands and JSON output when available.

## First checks

```bash
command -v glab && glab --version
glab auth status              # checks host from git remote/current context
# glab auth status --all      # when multiple GitLab hosts may be configured
git remote -v                 # understand the GitLab host and project
git branch --show-current
```

If authentication is missing, ask the user to run interactive login or provide how to do it; do not ask for or print tokens:

```bash
glab auth login               # interactive; detects hosts from git remotes
glab auth login --hostname gitlab.example.com
```

Do not run `glab auth status --show-token` unless the user explicitly requests it.

## Repository context

Most commands infer the repo from the current git remote. To target another project, pass `-R group/project`, `-R group/subgroup/project`, a full GitLab URL, or a Git URL.

Useful repo commands:

```bash
glab repo view --output json
glab repo view -R group/project --output json
glab label list --output json --per-page 100
```

For API calls in a repository, prefer placeholders so glab resolves and URL-encodes correctly:

```bash
glab api projects/:fullpath
glab api projects/:fullpath/repository/branches/:branch
```

Use `--hostname` on `glab api` only when the host cannot be inferred.

## Output handling

- Prefer `--output json` where supported, then pipe to `jq` for filtering.
- For GitLab API calls, use `glab api --paginate --output ndjson ... | jq ...` for long lists.
- Avoid commands that open a browser, editor, or TUI (`--web`, bare `glab ci view`, commands without required `-m`/`--message`) unless the user explicitly wants that.

## Merge requests

Read/list:

```bash
glab mr list --assignee=@me --output json --per-page 100
glab mr list --reviewer=@me --output json --per-page 100
glab mr list --source-branch "$(git branch --show-current)" --output json
glab mr view <iid-or-branch> --output json
glab mr view <iid-or-branch> --comments --output json
glab mr diff <iid-or-branch> --color=never
```

Create/update:

```bash
glab mr create --fill --draft --target-branch main --yes
glab mr create --title "..." --description "..." --source-branch feature --target-branch main --label label --reviewer username --yes
glab mr update <iid-or-branch> --ready --yes
glab mr update <iid-or-branch> --title "..." --description "..." --yes
```

Create MR from the current branch:

```bash
# 1. Inspect and push the source branch if needed
git branch --show-current
git status --short
git push -u origin "$(git branch --show-current)"

# 2. Put multiline descriptions in a temp file to avoid shell quoting issues
cat > /tmp/mr_description.md <<'EOF'
## What

...
EOF

# 3. Create the MR non-interactively. Use --assignee for assignees.
# Omit --reviewer entirely when the user asked for no reviewers.
glab mr create \
  --source-branch "$(git branch --show-current)" \
  --target-branch <target-branch> \
  --title "<title>" \
  --description "$(cat /tmp/mr_description.md)" \
  --assignee <username> \
  --yes

# 4. Verify assignees/reviewers/branches after creation
glab mr view <iid-or-branch> --output json | jq '{iid,title,web_url,assignees,reviewers,target_branch,source_branch}'
```

Comment:

```bash
glab mr note create <iid-or-branch> --message "..." --unique
```

Merge only when the user explicitly requests it; a direct merge request in the same message is sufficient authorization:

```bash
glab mr merge <iid-or-branch> --squash --remove-source-branch --yes
glab mr merge <iid-or-branch> --auto-merge --yes
```

## Issues

Read/list:

```bash
glab issue list --assignee=@me --output json --per-page 100
glab issue list --label bug --output json --per-page 100
glab issue view <iid> --output json
glab issue view <iid> --comments --output json
```

Create/update/comment:

```bash
glab issue create --title "..." --description "..." --label label --yes
glab issue update <iid> --label label
glab issue update <iid> --unlabel label
glab issue note <iid> --message "..."
glab issue close <iid>
glab issue reopen <iid>
```

## CI/CD pipelines and jobs

```bash
glab ci status --output json
glab ci status --branch main --output json
glab ci list --ref "$(git branch --show-current)" --output json --per-page 100
glab ci list --status failed --output json --per-page 100
glab ci trace <job-id-or-name> --branch "$(git branch --show-current)"
glab ci retry <job-id>
glab ci trigger <job-id>
glab ci cancel pipeline <pipeline-id>
glab ci lint
```

For a specific pipeline use:

```bash
glab ci view --pipelineid <pipeline-id> --web   # browser only if requested
```

Prefer `ci status`, `ci list`, and `ci trace` in agent sessions because `ci view` is interactive by default.

## GitLab API escape hatch

Use `glab api` when a high-level command lacks a feature.

REST examples:

```bash
glab api projects/:fullpath/merge_requests --paginate --output ndjson
glab api projects/:fullpath/merge_requests/<iid>/notes --paginate --output ndjson
glab api projects/:fullpath/issues/<iid>/notes --paginate --output ndjson
glab api --method POST projects/:fullpath/merge_requests/<iid>/notes --field body="..."
```

GraphQL example:

```bash
glab api graphql -f query='query { currentUser { username } }'
```

`glab api` defaults to GET without parameters and POST when `--field`/`--raw-field` is used. Use `--method` to override. Use `--field key=value` for typed JSON values and placeholders, `--raw-field key=value` for strings, and `--input`/`--form` for raw bodies or file uploads.

## Safety rules

- Ask for confirmation before destructive or externally visible mutations unless the user already gave an explicit instruction in the same request. This includes merge, close/reopen/delete, create/update comments, labels, issues, MRs, pipeline retry/cancel/trigger, and API POST/PUT/PATCH/DELETE.
- Never expose tokens. Do not echo environment variables such as `GITLAB_TOKEN`, `GITLAB_ACCESS_TOKEN`, or `OAUTH_TOKEN`.
- Summarize what command was run and the GitLab object affected. Include IDs/IIDs and URLs when available.
