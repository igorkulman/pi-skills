---
name: analyze
description: Perform read-only investigation and implementation planning for Jira issues and user-described bugs, features, or requested changes. Use when the user invokes /analyze or asks to understand and plan work before implementation. Do not use for reviewing an existing diff, branch, or merge request.
compatibility: Requires repository read access. Jira-backed tasks also require jira-task-context authentication.
---

# Analyze

Gather enough evidence to explain the current behavior and propose a safe implementation. Stay read-only while using this skill.

## Rules

- Do not edit files, change dependencies, mutate Git state, run formatters, or update external systems.
- Inspect only what is needed to identify the relevant code path, likely change locations, risks, and verification.
- Preserve uncertainty: distinguish confirmed behavior from assumptions and ask targeted questions when an unknown blocks a safe plan.
- If the user explicitly requested implementation, complete the concise analysis first and then continue with implementation. Otherwise stop and ask for approval.
- For investigation-only requests, provide conclusions and state that no changes were made.

## Route by task source

- **Jira URL/key:** load `jira-task-context`, gather the issue and directly relevant linked context, then inspect the repository against those requirements.
- **Local changes or branch:** inspect repository status, the exact diff/base, surrounding code, and related tests.
- **Plain task or bug report:** search for the named behavior, screen, symbol, error, API, model, or feature flag, then inspect nearby implementations and tests.
- **Repository question:** inspect only the files and history needed to answer it.

Do not duplicate detailed Jira traversal in this skill; delegate it to `jira-task-context`.

## Inspection goals

Identify:

- current behavior and the relevant code path
- likely root cause, missing behavior, or requirement gap
- files and modules likely to change
- existing patterns or similar implementations to follow
- tests, previews, fixtures, and verification commands
- meaningful edge cases, compatibility concerns, and unresolved questions

Use history only when it helps explain an invariant or likely regression. Stop once the implementation path is clear enough to act safely.

## Output

Use the smallest useful subset of this structure:

```markdown
## Task understanding
- Source and goal:
- Expected behavior or acceptance criteria:

## Findings
- Current behavior / likely gap:
- Existing patterns to follow:

## Relevant files
- `path`: why it matters

## Proposed implementation
1. ...
2. ...

## Verification
- ...

## Risks / questions
- ...
```

When implementation was not explicitly requested, finish with:

```text
Proceed with implementation?
```
