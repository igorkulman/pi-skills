---
name: xcodebuild-xcsift
description: Use when building or testing Xcode/iOS/macOS projects with xcodebuild. Provides standard xcodebuild commands piped through xcsift for JSON-parsable build/test output, avoiding repeated xcsift help lookups.
compatibility: Requires Xcode command line tools and xcsift installed and available on PATH.
---

# Xcodebuild with xcsift

Use this skill whenever invoking `xcodebuild` for builds, tests, or verification.

## Core rules

- Always pipe `xcodebuild` output to `xcsift`.
- Always redirect stderr to stdout before piping:
  ```bash
  xcodebuild ... 2>&1 | xcsift ...
  ```
- Prefer `set -o pipefail` so `xcodebuild` failures are not hidden by the pipe.
- Do not call `xcsift --help` just to remember common syntax; use the templates below.
- Only check `command -v xcsift` when availability is genuinely uncertain or a command fails because `xcsift` is missing.
- Use project-local instructions first for workspace/project, scheme, destination, and test plan names.
- Prefer `-workspace <Name>.xcworkspace` whenever an `.xcworkspace` exists. Use `-project <Name>.xcodeproj` only when no workspace is available or project-local instructions explicitly require it.
- If multiple workspaces are available and project-local instructions do not identify the intended one, ask before running `xcodebuild`.
- Keep build/test commands read-only unless the user explicitly requests a mutating action.

## Common templates

### Build an Xcode workspace preferred

Use this whenever an `.xcworkspace` exists:

```bash
set -o pipefail
xcodebuild \
  -workspace <WorkspaceName>.xcworkspace \
  -scheme "<Scheme Name>" \
  -destination 'generic/platform=iOS Simulator' \
  build \
  2>&1 | xcsift --quiet
```

### Build an Xcode project fallback

Use this only when no `.xcworkspace` exists or project-local instructions explicitly require the project:

```bash
set -o pipefail
xcodebuild \
  -project <ProjectName>.xcodeproj \
  -scheme "<Scheme Name>" \
  -destination 'generic/platform=iOS Simulator' \
  build \
  2>&1 | xcsift --quiet
```

### Run tests

Prefer the workspace form when an `.xcworkspace` exists:

```bash
set -o pipefail
xcodebuild \
  -workspace <WorkspaceName>.xcworkspace \
  -scheme "<Scheme Name>" \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  test \
  2>&1 | xcsift --quiet
```

Use `-project <ProjectName>.xcodeproj` instead only when no workspace is available or project-local instructions explicitly require it.

### Include warning details

```bash
set -o pipefail
xcodebuild ... 2>&1 | xcsift --warnings
```

### Treat warnings as failures

```bash
set -o pipefail
xcodebuild ... 2>&1 | xcsift --Werror
```

### TOON output for compact summaries

```bash
set -o pipefail
xcodebuild ... 2>&1 | xcsift --format toon --quiet
```

## Evenflo iOS default

When working in the Evenflo iOS repository and no more specific project instructions override it, first check whether an `.xcworkspace` exists. If it does, use that workspace with the `Debug - Evenflo` scheme. If no workspace exists, use:

```bash
set -o pipefail
xcodebuild \
  -project SensorSafe.xcodeproj \
  -scheme "Debug - Evenflo" \
  -destination 'generic/platform=iOS Simulator' \
  build \
  2>&1 | xcsift --quiet
```

## Reporting results

After a command finishes, summarize:

- command purpose: build/test
- status: success/failure
- errors count
- failed tests count, if any
- warnings count, if present
- notable error messages or failing test names
