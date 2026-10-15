# Xcode export provenance

Source: **Xcode 27.1, build 27A9275**, `/Applications/Xcode.app`.

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun agent skills export --output-dir <fresh-directory>
```

[upstream.md](upstream.md) is the byte-for-byte exported `app-resizability/SKILL.md`, retained for comparison, not as the active Pi entrypoint. All five files in `references/` are also byte-for-byte Xcode 27.1 exports. They matched the previous installed reference files, so no technical reference content changed. Hashes are recorded in [config/xcode-skill-exports.json](../../config/xcode-skill-exports.json).

The active [SKILL.md](SKILL.md) is the Pi controller. It replaces automatic all-task expansion, forced diffs/TODOs, mandatory subagent use, and line-only edit restrictions with explicit scope and authorization, justified candidate dispositions, optional read-only delegation, coherent changes, deployment checks, and focused runtime verification. Its workflow policy governs conflicting directives in the verbatim technical references.

For future upgrades, export to a fresh directory rather than overwriting the active skill or an existing user export. Compare upstream files, incorporate technical changes without losing Pi's workflow policy, then refresh snapshots and hashes. Do not automatically install unrelated exported skills. Run from the repository root:

```bash
node --test tests/xcode-skills.test.mjs
```

The saved upstream content remains Apple-supplied material; this provenance record does not relicense it.
