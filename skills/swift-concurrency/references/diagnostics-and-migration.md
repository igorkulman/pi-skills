# Diagnostics and Migration

## Settings inventory

Interpret diagnostics against the exact target configuration.

For SwiftPM, inspect:

- `// swift-tools-version:`: manifest API availability, not the target language mode by itself
- `swiftLanguageModes`: supported Swift language modes when present
- `.defaultIsolation(...)`: per-target default actor isolation on supporting PackageDescription versions
- strict-concurrency and upcoming-feature settings

For Xcode targets, inspect:

- `SWIFT_VERSION`
- `SWIFT_STRICT_CONCURRENCY`
- `SWIFT_DEFAULT_ACTOR_ISOLATION`
- `SWIFT_UPCOMING_FEATURE_*`

Existing projects may use Swift 5 language mode with strict checking enabled. Swift 6 language mode makes data-race safety diagnostics errors, but it does not automatically make every module default to `MainActor`.

## Common diagnostic triage

### “Sending ... risks causing data races”

Find the crossing boundary and all aliases to the value. Prefer a `Sendable` snapshot, moving state ownership behind an actor, or keeping the operation in one isolation domain. Use `sending` only for genuine one-way transfer.

### “Main actor-isolated ... from a nonisolated context”

Decide whether the declaration or caller owns UI state. Move the call to `MainActor`, make the API's isolation explicit, or make a member `nonisolated` only if it does not touch isolated state. Do not annotate an unrelated subsystem `@MainActor` to suppress the diagnostic.

### Actor-isolated protocol requirement mismatch

Check whether the protocol should itself be isolated, whether the conformance can be isolated on the active toolchain, or whether a genuinely nonisolated implementation is possible. Avoid `assumeIsolated` compatibility shims unless required by an older API and protected by a real invariant.

### Capturing non-`Sendable` state in an `@Sendable` closure

Capture immutable `Sendable` values, isolate mutation behind an actor, or redesign the callback boundary. Do not make an entire object unchecked-sendable because one closure needs a field.

### Async function contains no `await`

Remove `async` when it is not part of a protocol or API contract. If the signature must remain async, use the project's narrow lint suppression rather than adding a fake suspension.

## Evolving execution semantics

On toolchains supporting caller-isolated nonisolated async functions, `nonisolated(nonsending)` executes on the caller's actor. The corresponding upcoming feature can make that behavior the default. Inspect the target setting; do not infer behavior from compiler version alone.

`@concurrent` gives an async function nonisolated generic-executor semantics on supporting toolchains. Use it for an API that intentionally leaves the caller's actor, commonly substantial CPU work. Do not add it to network calls merely because they are asynchronous; an async API can suspend without blocking the caller's actor.

Default-main-actor inference is independently configured per module. It is appropriate only when the module's declarations are predominantly single-threaded/UI-bound.

## Incremental migration

1. Record the current language mode, strictness, default isolation, upcoming features, supported platforms, and dependency constraints.
2. Select one target or coherent subsystem.
3. Enable the intended checking level without unrelated architecture changes.
4. Fix diagnostics by ownership boundary: value models, protocols, state owners, then call sites.
5. Build and test that slice before increasing strictness or changing language mode elsewhere.
6. Audit compatibility escapes and exported API changes.
7. Verify all intentionally supported language modes and integration targets.

Do not combine a language-mode migration with an optional Combine-to-AsyncSequence rewrite, dependency replacement, or broad refactor unless the user requested both. Keep compatibility wrappers when they reduce blast radius, but mark their intended removal without creating external tickets automatically.

## Tool verification

Concurrency syntax and inference evolve. When available, use Xcode MCP to:

- read current Apple documentation
- type-check a minimal Swift snippet using the project's toolchain
- inspect target diagnostics
- run focused builds and tests

Treat the compiler as the authority for the active configuration. Do not generalize one successful snippet across modules with different settings.
