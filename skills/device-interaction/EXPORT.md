# Xcode export provenance

Source: **Xcode 27.1, build 27A9275**, `/Applications/Xcode.app`.

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun agent skills export --output-dir <fresh-directory>
```

[upstream.md](upstream.md) is the exported `device-interaction/SKILL.md`, retained for comparison, not as the active Pi entrypoint. Xcode writes the frontmatter keys in a varying order, so snapshots are compared with frontmatter as a sorted set and the body byte for byte.

The active [SKILL.md](SKILL.md) preserves Apple's session lifecycle, interaction syntax, hit-point guidance, retries, and evidence requirements. Pi-specific adaptations replace the generic Agent-tool delegation with main-agent execution, document the Xcode 27.1 native MCP tool names and arguments (only Xcode 27.1 and later are supported), and forward screenshots through codemode.

For future upgrades, export to a fresh directory rather than overwriting the active skill or an existing user export. Compare the upstream snapshot first, incorporate technical changes, preserve Pi's authorization/tooling policies, then refresh the snapshot. Do not automatically install unrelated exported skills. To compare every saved snapshot with a fresh export from the selected Xcode, run from the repository root:

```bash
scripts/check-xcode-skill-exports.sh [existing-export-dir]
```

It exits non-zero and prints a diff when a snapshot or reference differs, a reference is new, or a skill is missing from the export.

The saved upstream content remains Apple-supplied material; this provenance record does not relicense it.
