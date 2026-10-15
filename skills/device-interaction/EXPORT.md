# Xcode export provenance

Source: **Xcode 27.1, build 27A9275**, `/Applications/Xcode.app`.

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun agent skills export --output-dir <fresh-directory>
```

[upstream.md](upstream.md) is the byte-for-byte exported `device-interaction/SKILL.md`, retained for comparison, not as the active Pi entrypoint. Export hashes are recorded in [config/xcode-skill-exports.json](../../config/xcode-skill-exports.json).

The active [SKILL.md](SKILL.md) preserves Apple's session lifecycle, interaction syntax, hit-point guidance, retries, and evidence requirements. Pi-specific adaptations replace the generic Agent-tool delegation with main-agent execution, discover native MCP tools and current schemas, and forward screenshots through codemode.

For future upgrades, export to a fresh directory rather than overwriting the active skill or an existing user export. Compare the upstream snapshot first, incorporate technical changes, preserve Pi's authorization/tooling policies, then refresh the snapshot and hashes. Do not automatically install unrelated exported skills. Run from the repository root:

```bash
node --test tests/xcode-skills.test.mjs
```

The saved upstream content remains Apple-supplied material; this provenance record does not relicense it.
