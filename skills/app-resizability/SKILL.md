---
name: app-resizability
description: Investigate or fix layouts that must adapt to live window resizing, Split View, Stage Manager, multiple windows, or foldable iPhone readiness. Use for context-sensitive screen, orientation, idiom, scene lifecycle, and safe-area migrations in UIKit or SwiftUI. Match the requested scope; readiness does not automatically authorize every migration.
metadata:
  upstream: "Xcode 27.1 (27A9275)"
---

# App Resizability

Use the Xcode 27.1 technical references to address the actual resizing problem, not to mechanically replace every matching API. See [EXPORT.md](EXPORT.md) for export provenance and the untouched Apple controller.

## Execution boundary and scope

- For investigation, planning, or review, remain read-only. Do not add TODOs, write tracking files, or change project settings during analysis.
- An explicit request to implement, fix, or modernize authorizes the scoped changes and ordinary verification after inspection. Do not require another approval solely because this skill was loaded.
- Honor named screens, files, APIs, and acceptance criteria. A broad readiness request calls for an initial audit and a justified selection of work, not automatic execution of every task below.
- Preserve unrelated changes. Do not stage, commit, push, or change system permissions without the applicable explicit authorization.
- Ask when a concrete product or compatibility decision blocks safe implementation, such as changing public API, orientation behavior, supported OS versions, or window policy. Do not ask about an already specified approach or a routine, safe in-scope replacement.

## Using the upstream references

Read only the references relevant to the selected work before editing. They are preserved verbatim as technical pattern/checklist sources, not as mutation authorization or work-scheduling policy. This controller governs scope, delegation, file coverage, and verification when a reference says otherwise.

In particular, do not follow upstream demands for non-empty diffs, mandatory TODOs, blanket API replacement, or changes based on class-name heuristics alone. A reference's suggested signature or compatibility wrapper is a candidate, not a requirement to expand an already context-aware API. Allow necessary related edits for observation, callers, tests, and complete migration patterns; do not restrict changes to lines containing the old API.

## Task Registry

| Requested problem | Reference | What to establish |
|---|---|---|
| Screen scale, bounds, or coordinate-space assumptions | [uiscreen-task.md](references/uiscreen-task.md) | Which local view, window, scene, or supplied value owns the geometry; whether derived output is cached |
| Orientation used as a proxy for available space | [orientation-task.md](references/orientation-task.md) | Layout intent versus actual rotation, capture, or orientation-locking behavior |
| Application versus scene lifecycle | [scene-lifecycle-task.md](references/scene-lifecycle-task.md) | Current lifecycle, generated/static/dynamic configuration, and ownership of one-time versus per-scene work |
| Insets, bars, keyboard avoidance, or corner clipping | [safe-area-task.md](references/safe-area-task.md) | The affected view's own geometry, intended full-bleed content, asymmetry, and when insets update |
| Device class used as a proxy for available space | [idiom-task.md](references/idiom-task.md) | Space-dependent layout versus genuine device/platform/product decisions |

Scene lifecycle adoption and multiple-window support are different changes. Do not disable existing multiple-scene support or assume a single-window migration proves multiple-window correctness.

## Core Principles

1. **Closest valid context.** Prefer the consuming view's traits, bounds, safe area, or SwiftUI environment. Inject context into non-view code when necessary rather than walking global scene/window state.
2. **Classify intent first.** A search hit is not proof of a defect. Keep legitimate hardware queries, analytics, platform branches, rotation transforms, and intentional edge-to-edge content when they are outside the requested problem.
3. **Dynamic inputs need dynamic updates.** Inspect whether a value or rendered output is cached. Pair a replacement with recalculation/invalidation where required, or move the read to its appropriate point of use. SwiftUI environment updates, UIKit automatic trait tracking, and explicit observation have different requirements.
4. **Respect deployment targets.** Check platform and OS availability before adopting an exported pattern. Do not assume a single file targets the latest SDK. Preserve supported older-OS behavior; use current SDK declarations or Apple documentation through available Xcode MCP tools when guidance is ambiguous.
5. **Complete, minimal changes.** Include necessary observation, configuration, call-site, and test changes together. Preserve guards, branches, fallback semantics, public contracts, and project conventions. Do not invent literal geometry or add unrelated cleanup to make a warning disappear.
6. **Evidence over diff count.** A file may be unchanged because it is correct, unrelated, unsupported, already migrated, or blocked. Record the reason; do not force a diff or a TODO merely to show progress.

## Workflow

### Phase 1: Establish context and detect candidates

Read project guidance and repository state, then identify the affected target, framework, deployment floor, and requested behavior. Search only the relevant scope using the selected task references. For broad requests, inspect the relevant layout/lifecycle areas and summarize the tasks that evidence justifies.

For project-level readiness or configuration work, inspect launch-screen declarations, supported orientations, full-screen opt-outs, and scene configuration using the actual target/configuration's resolved build settings when available, plus the relevant plist, project, and xcconfig sources. Missing keys in one file do not establish the effective configuration. For a file-only task, do not search for an unrelated project or report these project-wide prerequisites.

Treat configuration findings as evidence to report, not permission to alter them. In particular, do not remove `UIRequiresFullScreen`, add `UIRequiresFullScreenIgnoredStartingWithVersion`, or change multiple-scene/orientation policy without that behavior being part of the authorized work.

### Phase 2: Analyze and select changes

For each candidate, inspect the real type hierarchy, callers, lifecycle, caching, and existing observation. Determine the question the code is asking and identify the smallest behavior-correct replacement.

Track inspected files and their disposition in memory or in the response: change, already correct, outside scope, or blocked with a reason. Do not create repository tracking files unless requested.

If implementation is not authorized, present the findings, approach, risks, and verification plan, then ask to proceed. Otherwise continue with the inspected, scoped work. Ask only about unresolved decisions that materially change behavior or compatibility.

Delegation is optional. A configured read-only reviewer can help inspect candidates or a diff, but cannot implement migrations or run device verification. Keep MCP-dependent work in the main agent; isolated subagents do not inherit the project's Xcode tools. Lack of an appropriate subagent does not block this workflow.

### Phase 3: Implement when authorized

Work in small coherent batches, applying the relevant patterns and the Core Principles above. For each batch, check affected callers, all branches, platform guards, initialization paths, and invalidation. Do not leave half a pattern applied.

Report unsafe or undecidable candidates instead of mechanically inserting TODOs. Add an actionable TODO only when it is useful, in scope, and not a substitute for a feasible authorized fix.

### Phase 4: Verify the selected behavior

Prefer available Xcode MCP build/test/diagnostic tools. Use `xcodebuild-xcsift` only when MCP is unavailable or cannot perform the required operation; do not rerun a real MCP build/test failure through the shell, or run both routes concurrently.

Run focused tests for the changed layout decisions, invalidation, or lifecycle behavior where applicable. A successful build does not prove resizing works.

For visual SwiftUI changes, render and inspect representative previews when Xcode MCP is available. For live resizing, rotation, keyboard, or multiple-window behavior, follow `device-interaction` and inspect representative runtime states:

- initial display and a resize while the app is running, not just launches at different sizes
- narrow/wide or compact/regular configurations relevant to the affected screen
- asymmetric insets, bars, keyboard, and left-to-right/right-to-left layouts when affected
- independent scenes and lifecycle transitions when scene/window behavior changed
- cached rendering after a trait/display change when scale-dependent output changed

Use only the applicable states. If the tooling cannot resize a window or exercise a required state, report it as unverified rather than substituting a preview, orientation change, or build as proof.

### Phase 5: Final verification and report

Re-read the request, inspect the final diff, run `git diff --check`, and account for the in-scope candidates. Coverage means every candidate has a justified disposition, not that every searched file has a diff.

Summarize the changes, preserved behavior, tests and visual/runtime evidence, unchanged or blocked candidates with reasons, and exactly what remains unverified. Do not claim full readiness from static API migration alone.
