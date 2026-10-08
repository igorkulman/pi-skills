# Subagent extension

This directory contains a maintained copy of Pi's official `examples/extensions/subagent` extension. It is versioned with the workflows that depend on it so a Pi or Node installation change cannot break the global extension path.

The extension registers the `subagent` tool and discovers user agents from `~/.pi/agent/agents/*.md`. Project-local agents remain disabled by default and require an explicit `agentScope` plus confirmation.

Unlike the general example, delegated agents disable extension discovery, MCP, skills, prompt templates, and themes and receive only their configured tools. They explicitly load the parent's active `pi-multi-pass` and `@gotgenes/pi-anthropic-auth` provider extensions (identified by loaded command source metadata), not its workflow/UI extensions. This preserves secondary-account registration and OAuth transport shaping without enabling the parent's tool stack. Agents without a pinned model inherit the parent session's model and thinking level.

For other custom providers or extension-defined models, opt in to trusted extension **files** using a `providerExtensions` frontmatter list. Paths are relative to the agent file's directory; absolute and `~/` paths also work. These files execute code and can register tools or hooks: use provider-only extensions, and do not list general workflow extensions. Project agents retain the existing scope/confirmation rules. Unknown provider extensions are not inherited automatically; pin a concrete built-in model if you do not want to opt in.

Completed child model/tool usage is returned in the parent tool result's `usage`, including failed runs and stopped chains. Streaming updates carry details only so they cannot double-count usage. Tool restrictions and instructions are not a filesystem sandbox; in particular, a reviewer with `bash` remains instruction-constrained.

Run the offline compatibility suite with Node 22.19+:

```bash
node --test extensions/subagent/compatibility.test.ts
```

It uses the managed Pi installation's dependency tree. For a different installation layout, set `PI_NODE_MODULES` to the directory containing Pi's runtime packages. It checks source selection, usage totals, and the registered tool's dispatch modes through mocked child processes. Live authentication/model requests require a separate smoke test.

The `code-review` workflow uses `code-review-pass` for independent candidate generation on non-trivial reviews.

When updating Pi, compare this copy with the current official example and deliberately preserve the isolation behavior.
