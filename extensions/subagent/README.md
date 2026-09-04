# Subagent extension

This directory contains a maintained copy of Pi's official `examples/extensions/subagent` extension. It is versioned with the workflows that depend on it so a Pi or Node installation change cannot break the global extension path.

The extension registers the `subagent` tool and discovers user agents from `~/.pi/agent/agents/*.md`. Project-local agents remain disabled by default and require an explicit `agentScope` plus confirmation.

Unlike the general example, delegated agents run without extensions, skills, prompt templates, or themes and receive only their configured tools. This keeps independent review passes isolated from the parent workflow. Agents without a pinned model inherit the parent session's model and thinking level.

The `code-review` workflow uses `code-review-pass` for independent candidate generation on non-trivial reviews.

When updating Pi, compare this copy with the current official example and deliberately preserve the isolation behavior.
