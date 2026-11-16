---
name: device-interaction
description: Verify interactive Apple-platform app behavior on a simulator or device through Xcode MCP screenshots, UI hierarchy, and synthesized input. Use when the user asks to test or check behavior on a device/simulator, after implementing UI interaction changes that need runtime verification, or when debugging touch, focus, keyboard, orientation, or other input behavior. Do not use for build-only checks, unit tests, code review, static UI inspection, or SwiftUI preview-only verification.
compatibility: Requires Xcode 27.1 or later with project-enabled Xcode MCP (pi-xcode-mcp), called through codemode.
metadata:
  upstream: "Xcode 27.1 (27A9275)"
---

# Device Interaction

Verify runtime UI behavior through Xcode MCP on an Apple device or simulator. Adapted from the Xcode 27.1 export; see [EXPORT.md](EXPORT.md) for provenance and the untouched Apple skill. This Pi workflow replaces Apple's generic Agent-tool delegation and keeps its device interaction guidance. Only Xcode 27.1 and later are supported.

## Execution boundary

Perform this workflow in the main agent. Do not delegate it to the isolated Pi subagent extension: children load only opted-in provider extensions, disable MCP, and do not inherit the project's device tools. The session start response tells the caller to spawn a subagent; ignore that instruction.

Use this skill only for behavior that benefits from launching and interacting with the app. Prefer a SwiftUI preview for a purely visual, non-interactive check when a representative preview exists.

If the user requested only verification, remain read-only and report defects rather than changing code. An explicit request to implement or fix behavior authorizes the scoped code changes and subsequent verification under the normal project workflow.

## Tools

Call these from `codemode` as `tools.mcp__xcode__<name>(args)`:

| Tool | Required arguments | Notes |
|---|---|---|
| `DeviceInteractionStartWorkspaceSession` | `sessionIdentifier` | Optional `deviceIdentifier` and `workspaceIdentifier`. Enables install and run. |
| `DeviceInteractionStartSession` | `sessionIdentifier`, `deviceIdentifier` | For an already-installed app; cannot build or install. |
| `DeviceInteractionInstallAndRun` | `interactionSessionKey` | Pass `workspaceIdentifier` with a headless workspace. Optional `commandLineArguments` and `environmentVariables`. |
| `DeviceInteractionSynthesize` | `interactSessionKey` | Optional `interactionCommand` and `activationBundleId`. Omit the command to capture only. |
| `DeviceInteractionEndSession` | `interactionSessionKey` | Always call in cleanup. |

The session key is `structuredContent.interactionSessionKey` from the start call. Note the different argument name for `DeviceInteractionSynthesize`: `interactSessionKey`. Keep the key in a script constant, or `store()` it explicitly before `load()`ing it in a later script.

`deviceIdentifier` accepts a UUID, name, OS version, or device type and matches the best candidate.

If the tools are missing or calls report disconnection, ask the user to inspect the project's `xcode` server in `/mcp` and reconnect it. Do not invent a connection tool, enable Xcode globally, start a service, or change system permissions as a substitute. Do not substitute a shell build, unit tests, or a preview and claim interactive device behavior was verified.

## Captures

`DeviceInteractionSynthesize` returns paths in `structuredContent`, not image blocks: `screenshotPath`, `thumbnailScreenshotPath`, `hierarchyPath`, `logsPath` (the app's console output), and `applicationState` (`NotRun`, `Running`, `Stopped`, `Crashed`, `Disconnected`, `Hanging`, or `RunningInBackground`).

A script's output is all the model sees. Read the screenshot with `tools.read()` and forward it with `image()`; read the hierarchy as text. Never print base64 image data as text. Do not claim visual inspection from a path, thumbnail, or unforwarded result.

```js
const KEY = "<interactionSessionKey from the start call>";

async function capture(command) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await tools.mcp__xcode__DeviceInteractionSynthesize({
      interactSessionKey: KEY,
      ...(command && attempt === 0 ? { interactionCommand: command } : {}),
    });
    const data = result.structuredContent;
    if (result.isError || !data) {
      throw new Error("Synthesize failed; the session may have ended. Start a new session.");
    }
    if (!data.hierarchyPath) continue; // transient accessibility failure: capture again
    image(await tools.read({ path: data.screenshotPath, offset: null, limit: null }));
    text(`applicationState: ${data.applicationState}`);
    return { data, hierarchy: await tools.read({ path: data.hierarchyPath, offset: null, limit: null }) };
  }
  throw new Error("No UI hierarchy after a retry.");
}
```

Xcode's screenshot is a system capture: layers excluded from screenshots and recordings, such as secure text or capture-redacted content, are missing or replaced. For the pixels actually displayed in a simulator, use `xcrun simctl io <udid> screenshot <path>`. Comparing both is a valid way to verify capture-exclusion behavior. Real screenshots and screen recordings cannot be triggered in the simulator, whose Control Center has no Screen Recording control, so report system capture behavior as unverified.

## Session lifecycle

For an app in the current workspace:

```text
DeviceInteractionStartWorkspaceSession
  -> DeviceInteractionInstallAndRun
  -> DeviceInteractionSynthesize (repeat)
  -> DeviceInteractionEndSession
```

For an already-installed app that does not need a workspace build, start with `DeviceInteractionStartSession` instead.

Rules:

1. Start a workspace-backed session early when verifying an app being built; the device may need to boot. `DeviceInteractionInstallAndRun` builds, installs, and launches. Call it again after every code change.
2. Pass a device identifier when the target is known. Omit it from a workspace session to use the current destination.
3. Use one session per device. Separate sessions on different simulators may run side by side, for example to exchange messages between two accounts.
4. End every session in cleanup, even when verification fails. Open sessions are resource-heavy and affect the user-facing UI.
5. Do not run builds, tests, or previews concurrently with a session's install and run.
6. Changing the app's lifecycle outside the session, with `xcrun simctl install`, `terminate`, `launch`, or a reboot, ends the session. Start a new one afterward.
7. Xcode 27 ships no standalone `Simulator.app`; do not try to open or script it. Use the session tools and `simctl`.

### One-run launch configuration

`DeviceInteractionInstallAndRun` accepts:

- `commandLineArguments`: arguments for this launch. Include `$(inherited)` to preserve scheme arguments, for example `["$(inherited)", "--reset-state"]`.
- `environmentVariables`: values for this launch. Include `"$(inherited)": ""` to preserve scheme variables, for example `{"$(inherited)": "", "DEBUG_MODE": "1"}`.

Prefer these one-run parameters over editing the Xcode scheme. Omit them to leave the scheme configuration unchanged.

## Standard verification workflow

1. Install and launch the app when using a workspace-backed session.
2. Capture the initial state with `DeviceInteractionSynthesize` and no interaction command.
3. Inspect both the full-size screenshot and the UI hierarchy.
4. Confirm the app has passed its launch screen and meaningful UI elements are present before interacting.
5. Locate the target in the hierarchy and use its calculated `hitPoint`.
6. Perform one interaction or a short intentional command chain.
7. Capture again and compare the resulting screenshot and hierarchy with the expected state.
8. Repeat only for the states needed to verify the requested behavior.
9. Inspect `logsPath` when the app exits, crashes, or behaves unexpectedly, or when `applicationState` is not `Running`.
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

Before interacting with such an element, activate its application by passing that bundle identifier as `activationBundleId` to `DeviceInteractionSynthesize`. Activation is expensive and moves the app under test to the background, so do it only when required and reopen the app before continuing.

## Interaction command syntax

`DeviceInteractionSynthesize` accepts the following `interactionCommand` syntax:

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
