# Global Pi Workflow

## Change safety and authorization

- Treat this section as the source of truth for mutation authorization; skills may add scope or evidence requirements but must not require a redundant confirmation.
- Inspect relevant code, tests, project guidance, and repository state before making non-trivial changes.
- For investigation, explanation, planning, review, or context lookup, remain read-only.
- If implementation was not explicitly requested, present a concise approach, risks, and verification plan, then ask for approval.
- An explicit request to implement, fix, update, or make a change authorizes the scoped local edits and ordinary verification after inspection. Do not ask for a second confirmation solely because a skill was loaded.
- Do not stage or commit changes unless the user directly requests it.
- Preserve unrelated user changes.
- Destructive Git or filesystem operations require an explicit request for that action. Preview the exact effect when practical, and never stash changes automatically.
- Externally visible mutations require explicit authorization for the specific action. A direct request in the same message counts; otherwise present the exact action and ask before executing it.

## Workflow routing

- For Jira-backed implementation tasks, use `analyze`; for Jira-only context lookup, use `jira-task-context`.
- For code reviews, branch reviews, local-change reviews, and GitLab MR reviews, use `code-review` and remain read-only.
- For GitLab access, use `gitlab-glab` and the authenticated `glab` CLI.
- For MR reviewer-comment work, use `mr-comment-resolution`.
- For commits, use `git-commit`.
- For Xcode-specific builds, tests, diagnostics, SwiftUI previews, Apple documentation, and Swift snippets, prefer the available Xcode MCP tools.
- Fall back to shell `xcodebuild` only when Xcode MCP is unavailable or does not expose the required operation. A real build or test failure reported by Xcode MCP is not a reason to rerun the same check through the shell, and the two routes must not run concurrently.
- When invoking shell `xcodebuild`, use `xcodebuild-xcsift` and pipe output through `xcsift`.
- Access GitHub resources through authenticated `gh`, not unauthenticated web fetching. If access fails, check `gh auth status` rather than falling back to public web access.

## Verification

Before finalizing non-trivial implementation:

1. Re-read the request and any Jira, specification, or design context used.
2. Inspect the final diff against the requested behavior and acceptance criteria.
3. Identify and run focused tests, or state exactly why they were not run.
4. Do not treat a successful build as proof that tests or product behavior are correct.
5. For visual SwiftUI changes, render and inspect representative previews when Xcode MCP is available. Compare the rendered snapshot with the supplied screenshot, Figma design, or requested state before claiming visual correctness.
