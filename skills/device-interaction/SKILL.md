---
name: device-interaction
description: Verify interactive Apple-platform app behavior on a simulator or device through Xcode MCP screenshots, UI hierarchy, and synthesized input. Use when the user asks to test or check behavior on a device/simulator, after implementing UI interaction changes that need runtime verification, or when debugging touch, focus, keyboard, orientation, or other input behavior. Do not use for build-only checks, unit tests, code review, static UI inspection, or SwiftUI preview-only verification.
compatibility: Requires project-enabled Xcode MCP advertising device-session and synthesis tools, and Pi's native MCP discovery through codemode or tool_search.
metadata:
  upstream: "Xcode 27.1 (27A9275)"
---

# Device Interaction

Verify runtime UI behavior through Xcode MCP on an Apple device or simulator. Adapted from a fresh Xcode 27.1 export; see [EXPORT.md](EXPORT.md) for provenance and the untouched Apple skill. This Pi workflow replaces Apple's generic Agent-tool delegation and keeps its device interaction guidance.

## Execution boundary

Perform this workflow in the main agent. Do not delegate it to the isolated Pi subagent extension: children load only opted-in provider extensions, disable MCP, and do not inherit the project's device tools.

Use this skill only for behavior that benefits from launching and interacting with the app. Prefer a SwiftUI preview for a purely visual, non-interactive check when a representative preview exists.

If the user requested only verification, remain read-only and report defects rather than changing code. An explicit request to implement or fix behavior authorizes the scoped code changes and subsequent verification under the normal project workflow.

## Required tools

Discover the project's native MCP tools, then inspect their current argument schemas before calling them. With `pi-xcode-mcp`, native names use `mcp__xcode__<operation>` and are callable through `codemode` even when absent from direct tool declarations. Do not use legacy mirrored aliases or assume a fixed package-maintained tool set.

Discover and describe the relevant tools in a read-only codemode script:

```js
const deviceTools = ALL_TOOLS.filter(({ name }) =>
  name.startsWith("mcp__xcode__") && /DeviceInteraction|DeviceEventSynthesize/.test(name)
);
text(deviceTools);
for (const { name } of deviceTools) text(await describeTool(name));
```

Look for these advertised operations:

- `DeviceInteractionStartWorkspaceSession`
- `DeviceInteractionStartSession`
- `DeviceInteractionInstallAndRun`
- `DeviceInteractionSynthesize` (or `DeviceEventSynthesize` when that is the advertised name)
- `DeviceInteractionEndSession`

The live Xcode 27.1 probe advertised `DeviceInteractionSynthesize`, despite the exported skill naming `DeviceEventSynthesize`. Select the operation actually present, inspect its schema, and use its returned session key and current parameter names; do not require both aliases.

If codemode is unavailable but `tool_search` exists, discover and load the native tools there and inspect their returned schemas. If discovery is empty or calls report disconnection, ask the user to inspect the project's `xcode` server in `/mcp` and reconnect it there if necessary. Do not invent a connection tool, enable Xcode globally, start a service, or change system permissions as a substitute.

If required tools remain unavailable, report that project-local Xcode MCP or the current Xcode version does not expose the necessary device operations. Do not substitute a shell build, unit tests, or a preview and claim interactive device behavior was verified.

## Screenshots through codemode

A script's output is all the model sees. Calling a tool without forwarding its content does not expose its screenshot for visual inspection. After a native MCP call, forward image blocks with `image()` and text blocks with `text()`. Check `isError` and the operation's returned status/diagnostics; treat reported build, launch, or interaction failures as failures even if transport succeeded.

This helper handles an MCP `CallToolResult` returned by a preceding native tool call:

```js
function showMcpResult(result) {
  for (const block of result.content ?? []) {
    if (block.type === "image") image(block);
    else if (block.type === "text") text(block.text);
  }
  if (result.isError) throw new Error("Xcode MCP reported an error; inspect the forwarded diagnostics.");
}
```

Call `showMcpResult(result)` in the same script that receives the result. Inspect `structuredContent` when it supplies session identifiers, paths, or status not included in the text blocks, forwarding only the relevant fields. Never print base64 image data as text. If Xcode returns a screenshot path instead of an image block, read that path with the available `read` tool; inside codemode, pass the returned image block to `image()`. Read the hierarchy path separately. Do not claim visual inspection from a path, thumbnail, or unforwarded result.

## Session lifecycle

For an app in the current workspace:

```text
DeviceInteractionStartWorkspaceSession
  -> DeviceInteractionInstallAndRun
  -> DeviceInteractionSynthesize / DeviceEventSynthesize (whichever is advertised)
  -> DeviceInteractionEndSession
```

These are operation names; call the discovered native identifiers using their inspected schemas. For an already-installed app that does not need a workspace build, use `DeviceInteractionStartSession` instead.

Rules:

1. Start a workspace-backed session early when verifying an app being built. `DeviceInteractionInstallAndRun` requires that session and includes the build.
2. Pass a device identifier when the target is known. Omit it to use the current destination. When discovery is needed and the tool schema supports it, pass an empty device identifier to list available targets.
3. Retain the returned session identifier and use it for every subsequent operation.
4. End the session in cleanup even when verification fails. Open sessions are resource-heavy.
5. Keep a session exclusive to this verification flow. Do not run concurrent build, test, preview, or device operations against it.

### One-run launch configuration

`DeviceInteractionInstallAndRun` may support the following parameters; verify them in the advertised schema:

- `commandLineArguments`: arguments for this launch. Include `$(inherited)` to preserve scheme arguments, for example `["$(inherited)", "--reset-state"]`.
- `environmentVariables`: values for this launch. Include `"$(inherited)": ""` to preserve scheme variables, for example `{"$(inherited)": "", "DEBUG_MODE": "1"}`.

Prefer these one-run parameters over editing the Xcode scheme. Omit them to leave the scheme configuration unchanged.

## Standard verification workflow

1. Install and launch the app when using a workspace-backed session.
2. Capture the initial state with the discovered synthesis tool using an empty interaction command when its schema permits.
3. Inspect both the screenshot and UI hierarchy, forwarding image content when using codemode. If the tool returns file paths, read the hierarchy and full-size screenshot when needed.
4. Confirm the app has passed its launch screen and meaningful UI elements are present before interacting.
5. Locate the target in the hierarchy and use its calculated `hitPoint`.
6. Perform one interaction or a short intentional command chain.
7. Capture again and compare the resulting screenshot and hierarchy with the expected state.
8. Repeat only for the states needed to verify the requested behavior.
9. Inspect runtime output when the app exits, crashes, or behaves unexpectedly.
10. End the session and report the evidence, result, and any unverified areas.

Always report UI problems plausibly caused by code, including overlapping or unreadable text, unexpected cropping, wrong colors, broken alignment, and controls rendered off-screen.

## Reading UI hierarchies

Hierarchy entries include element frames and calculated hit points:

```text
UIView {{100, 200}, {60, 30}}, hitPoint: {130.0, 215.0}
  UIButton "Login" {{110, 205}, {30, 20}}, hitPoint: {125.0, 215.0}
  UIButton "Help" {{140, 205}, {20, 20}}, hitPoint: {150.0, 215.0}, activationBundleId: com.example.app
```

- `{100, 200}` is the origin.
- `{60, 30}` is the width and height.
- `hitPoint: {130.0, 215.0}` is the preferred interaction coordinate.

Always try the hierarchy's `hitPoint` first. Estimate coordinates from the screenshot only after a hit-point interaction has no effect and a fresh capture confirms it failed.

Elements marked `isRemoteLeafPlaceholder` do not expose their children. Screenshot-estimated coordinates may be necessary for those elements.

### Multiple applications

When overlapping windows belong to different applications, hierarchy lines may include `activationBundleId`.

Before interacting with such an element, activate its application by passing that bundle identifier to the discovered synthesis tool when its schema supports `activationBundleId`. Application activation is expensive, so do it only when required.

## Interaction command syntax

Xcode 27.1 exports the following `interactionCommand` syntax for the device synthesis operation. Follow the current advertised schema and report unsupported commands rather than assuming other Xcode versions match:

| Command | Action |
|---|---|
| `t <x> <y> [duration]` | Tap, optionally holding for a duration. |
| `d <x> <y>` | Double tap. |
| `t <x1> <y1> f <x2> <y2> [duration]` | Swipe. |
| `drag <x1> <y1> <x2> <y2> [holdDuration] [moveDuration]` | Press, hold, and drag. |
| `mt [x1 y1, ...] dur ...` | Multi-touch keyframe sequence. |
| `b h/p/u/d [duration]` | Home, Power, Volume Up, or Volume Down. |
| `b c/s/a [duration]` | watchOS Digital Crown, side, or Action button. |
| `sender keyboard kbd <text>` | Type text; this must be the final command in a chain. |
| `w <duration>` | Wait briefly without another action. |
| `orientation faceDown/faceUp/landscapeLeft/landscapeRight/portrait/portraitUpsideDown` | Set iOS orientation. |
| `c <rotations>` | Rotate the watchOS Digital Crown; sign controls direction. |
| `r up/down/left/right/select/menu/playpause/home` | Press a tvOS Siri Remote button. |

Examples:

```text
t 100 200
d 200 300
t 200 600 f 200 200 0.3
drag 100 300 100 100 0.5 1.5
mt [100 300, 300 300] 0.5 [175 300, 225 300] 0.5
sender keyboard kbd hello world
sender keyboard kbd submit\u{000A}
orientation landscapeLeft
b h
r right r right r select
```

For multi-touch, each bracketed keyframe lists active finger coordinates. The following duration is travel time to the next keyframe; the final duration is the hold before lifting. A missing or empty finger slot ends that touch.

## Platform-specific behavior

### iOS and iPadOS

Use hierarchy hit points for taps, swipes, drags, keyboard input, hardware buttons, and orientation changes. Recapture after rotation before using coordinates because layout and hit points may move.

### watchOS

Use `b c`, `b s`, and `b a` for hardware buttons and `c <rotations>` for Digital Crown input. Confirm availability because some devices do not have an Action button.

### tvOS

tvOS is focus-based; coordinate taps and swipes do not apply.

1. Read the hierarchy to identify the currently focused element and available focus targets.
2. Calculate the directional presses needed to reach the target.
3. Chain obvious navigation presses into one command, such as `r right r right r select`.
4. Capture afterward to confirm focus or navigation reached the expected state.
5. Use `r menu` to navigate back.

## Timing and retries

- **Launch:** If the first capture is empty or still shows a launch screen, capture once more before interacting.
- **Animations:** After an interaction, rely on the fresh capture rather than adding arbitrary delays.
- **Failed input:** Recapture and retry once using the updated hierarchy hit point. If it still fails, report the failure instead of retrying indefinitely.
- **Loading:** When a spinner or loading state is visible, make one later capture. Do not interact with controls that are still loading.
- **Unclear target:** Re-read nested hierarchy elements. A nearby `Switch`, `Slider`, or other child may be the actual control.
- **Insufficient image detail:** Inspect the full-size screenshot rather than judging from a thumbnail.

## Judge the result

Distinguish:

- **Functional bug:** A control does not respond, navigation reaches the wrong screen, expected data or UI is missing, or the app crashes/exits.
- **Visual/layout bug:** Text overlaps or truncates unexpectedly, content is off-screen, colors are wrong, or alignment is broken.
- **Transient state:** Loading indicators, short animations, and keyboard transitions are not bugs; capture after they settle.
- **Expected behavior:** Intentional empty states, controls disabled by incomplete input, and permission dialogs are not bugs unless they conflict with requirements.

## Report

Summarize:

- target device or simulator
- launch configuration, when non-default
- interactions performed
- screenshots/hierarchy states inspected
- expected versus observed behavior
- pass/fail result and concrete defects
- crashes or relevant runtime output
- anything not verified

Never claim device verification from a successful build alone.
