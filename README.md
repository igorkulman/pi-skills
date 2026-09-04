# Pi Skills

A collection of reusable skills I use in my daily software development workflow with [Pi](https://pi.dev/).

I use coding agents for more than code generation. The goal of these skills is to turn recurring engineering tasks into explicit, repeatable workflows: gather the right context, understand the problem before changing code, implement the change, review it, verify feedback, and interact safely with the surrounding development tools.

These are my actual working skills rather than a demo framework. They have grown out of day-to-day use across production codebases.

## Workflow

A typical task can move through several small, composable workflows:

```text
Jira task / bug report
        ↓
     analyze
        ↓
tdd when suitable /
normal implementation
        ↓
   code-review
        ↓
review feedback / MR comments
        ↓
mr-comment-resolution
        ↓
      verify
        ↓
    git-commit
```

Not every task uses every step. The skills are deliberately independent so the agent can load only the workflow and context relevant to the current job. `resolve-merge-conflicts` is a standalone recovery path for an ongoing rebase or merge rather than a step in the main flow.

A recurring principle is to separate investigation from mutation. For example, `analyze` is read-only and produces an evidence-based implementation plan before changes are made, while review and verification workflows default to read-only until an external action is explicitly requested.

## Included skills

| Skill | Purpose |
|---|---|
| `analyze` | Read-only investigation and implementation planning before changing code. |
| `code-review` | Reviews local changes, branches, or GitLab merge requests and reports concrete, verified findings. |
| `git-commit` | Creates structured Git commits from local changes, including staging and commit messages. |
| `git-redate` | Rewrites author and committer timestamps for selected commits. |
| `gitlab-glab` | Interacts with GitLab projects, merge requests, issues, pipelines, jobs, releases, and APIs through `glab`. |
| `jira-task-context` | Builds development context from Jira issues, linked issues, and referenced documentation. |
| `jira-update` | Updates Jira tickets, descriptions, fields, and comments. |
| `mr-comment-resolution` | Analyzes and addresses GitLab merge-request feedback and resolves completed discussions. |
| `resolve-merge-conflicts` | Resolves all conflicts in an ongoing rebase or merge and automatically continues it to completion. |
| `tdd` | Implements an analyzed task through observable behavior, one red-green-refactor slice at a time. |
| `verify` | Re-checks review findings against updated code and verifies whether requested changes were addressed. |
| `xcodebuild-xcsift` | Falls back to shell `xcodebuild` with structured `xcsift` output when Xcode MCP cannot perform the operation. |

Some skills include supporting references or scripts where a reliable workflow needs more than prompt instructions alone.

## Supporting extensions and agents

The GitLab `code-review` workflow uses the bundled `review-findings-selector` extension to choose which findings to post. Non-trivial reviews can also use the bundled `subagent` extension and `code-review-pass` agent for an isolated independent pass. These resources are versioned with the skills so the complete review workflow can be installed reproducibly.

Machine-managed integrations such as Herdr and separately packaged integrations such as `pi-xcode-mcp` remain outside this repository.

## Design principles

- **Context before code.** Gather requirements and inspect the relevant implementation before proposing changes.
- **Read-only by default.** Investigation, review, and verification should not unexpectedly mutate code or external systems.
- **Evidence over guesses.** Distinguish confirmed behavior from assumptions and keep uncertainty visible.
- **Explicit external actions.** Posting review comments, resolving discussions, approving changes, or updating Jira should happen only when requested.
- **Composable workflows.** Keep individual skills focused so they can be combined rather than building one large agent prompt.
- **Use existing engineering tools.** Git, Jira, GitLab, Xcode, tests, and CI remain the sources of truth; the agent orchestrates them rather than replacing them.

## Installation

Clone the repository, then link its skills and global workflow instructions into Pi:

```bash
git clone git@github.com:igorkulman/pi-skills.git ~/Projects/open-source/pi-skills
mkdir -p ~/.pi/agent/extensions ~/.pi/agent/agents
ln -s ~/Projects/open-source/pi-skills/skills ~/.pi/agent/skills
ln -s ~/Projects/open-source/pi-skills/config/AGENTS.md ~/.pi/agent/AGENTS.md
ln -s ~/Projects/open-source/pi-skills/extensions/review-findings-selector.ts ~/.pi/agent/extensions/review-findings-selector.ts
ln -s ~/Projects/open-source/pi-skills/extensions/subagent ~/.pi/agent/extensions/subagent
ln -s ~/Projects/open-source/pi-skills/agents/code-review-pass.md ~/.pi/agent/agents/code-review-pass.md
```

If any destination already exists, move it aside before creating the symlink.

Run `/reload` in an existing Pi session after changing the links, skills, or global instructions.

## Structure

Global Pi workflow and safety instructions live in `config/AGENTS.md`. Reusable Pi tools live in `extensions/`, and specialized subagent prompts live in `agents/`. Each skill keeps its controller in `SKILL.md`; more involved skills may route to additional reference documents or bundled helper scripts instead of putting every detail into the main skill definition.

## License

MIT
