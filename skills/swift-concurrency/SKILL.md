---
name: swift-concurrency
description: Implement, diagnose, review, or migrate Swift code involving async/await, actors, tasks, cancellation, Sendable, isolation diagnostics, continuations, AsyncSequence, or async tests. Use for Swift concurrency compiler errors and runtime race or task-lifetime problems. Do not use for ordinary synchronous Swift work, unrelated build failures, or project-specific migration policy when a more specific project skill applies.
compatibility: Requires Swift source access. Version-sensitive guidance requires the project's Swift language mode and toolchain; prefer available Xcode MCP documentation, snippet, build, test, and diagnostic tools.
---

# Swift Concurrency

Reason from the project's actual isolation model and compiler configuration. Do not apply concurrency annotations merely to silence diagnostics.

## Intake

Before giving version-sensitive advice or changing code, inspect the smallest relevant set of settings:

- SwiftPM: tools version, `swiftLanguageModes`, target `swiftSettings`, `.defaultIsolation(...)`, strict-concurrency settings, and upcoming features in `Package.swift`.
- Xcode: `SWIFT_VERSION`, `SWIFT_STRICT_CONCURRENCY`, `SWIFT_DEFAULT_ACTOR_ISOLATION`, and `SWIFT_UPCOMING_FEATURE_*` in project settings.
- The exact compiler diagnostic and the declaration plus call sites on both sides of the reported isolation boundary.
- Deployment targets when a proposed API has OS availability constraints.

Do not assume that the package tools version, Swift language mode, compiler version, and default actor isolation are the same thing. If a required setting cannot be determined, state the assumption and ask only when it materially changes the solution.

## Diagnostic method

1. Identify every relevant isolation domain: `@MainActor`, another global actor, an actor instance, task isolation, or nonisolated code.
2. Identify mutable state and who owns it.
3. Mark values that cross an isolation boundary and determine whether they are `Sendable`, proven disconnected for `sending`, or should not cross at all.
4. Account for suspension and actor reentrancy; values read before `await` may be stale afterward.
5. Decide whether the operation needs serialization, parallelism, or simply asynchronous waiting.
6. Fix the model at the narrowest stable boundary, then compile before addressing secondary diagnostics.

Prefer fixes in this order:

1. Keep work in its rightful isolation domain and pass immutable `Sendable` values.
2. Give shared mutable state one clear owner, often an actor or an existing global actor.
3. Add precise annotations to declarations or protocol requirements where they express the API contract.
4. Use `sending` only when ownership transfer matches the actual lifetime of the value.
5. Use compatibility escapes only as a last resort.

Never apply `@MainActor` to an entire type or module solely because it removes errors. UI state commonly belongs on `MainActor`; networking, storage, parsing, and CPU-heavy work do not automatically belong there.

## Execution rules

- Prefer structured child tasks: direct `await`, `async let`, and task groups.
- Use unstructured `Task` only when bridging from synchronous code or when an explicit owner manages its lifetime, cancellation, errors, and result.
- `Task` inherits surrounding isolation; it is not a generic “background thread” primitive.
- Use `Task.detached` only when deliberately discarding actor context, task-local values, and inherited priority is correct.
- Cancellation is cooperative. Propagate `CancellationError`, check cancellation in long loops, and cancel owned long-lived tasks.
- Never block a cooperative executor with semaphores or synchronous waits. Never hold a lock across an `await`.
- Treat `await` as a possible suspension and interleaving point, not evidence of a thread switch.
- Measure before changing isolation for performance. `@concurrent` selects generic-executor semantics on supporting toolchains; it does not promise a particular thread.

## Unsafe and compatibility features

Before using `@preconcurrency`, `@unchecked Sendable`, `nonisolated(unsafe)`, or `MainActor.assumeIsolated`:

- document the concrete invariant that makes the operation safe
- scope the escape as narrowly as possible
- explain why a checked design is not currently practical
- identify removal work; create an external ticket only when explicitly authorized

Do not add a package dependency, change strict-concurrency settings, or change default actor isolation merely to avoid fixing diagnostics unless the user explicitly requested that migration or dependency change.

## Reference routing

Read only the references needed for the task, resolving paths relative to this skill:

- `references/isolation-and-sendability.md`: actors, global actors, reentrancy, `Sendable`, `sending`, and unsafe escapes.
- `references/tasks-and-cancellation.md`: structured and unstructured tasks, cancellation, errors, priorities, and task lifetime.
- `references/diagnostics-and-migration.md`: common diagnostics, build settings, Swift language-mode migration, `@concurrent`, and default isolation.
- `references/async-streams-and-continuations.md`: callback bridging, continuations, `AsyncSequence`, and stream lifetime.
- `references/testing.md`: deterministic tests for async and actor-isolated behavior using XCTest or Swift Testing.
- `references/core-data.md`: Core Data confinement, `NSManagedObjectID`, snapshots, and advanced executor integration.

For compiler- or SDK-sensitive syntax, prefer the available Xcode MCP Apple-documentation and Swift-snippet tools over memory. Do not load every reference preemptively.

## Verification

After changing concurrency code:

1. Re-run the focused compiler diagnostic or build with the same settings that produced it.
2. Run focused tests that exercise ordering, cancellation, error propagation, or lifetime—not merely the happy-path result.
3. Use Thread Sanitizer or Instruments when runtime races, hangs, excessive task creation, or performance are part of the problem.
4. Verify supported Swift language modes separately when a package intentionally supports more than one.
5. Report unsafe escapes, assumptions, untested scheduling behavior, and unavailable verification tools.

Follow the project's Xcode verification route. A successful build proves only that the checked configuration compiled; it does not prove cancellation, ordering, lifetime, or race freedom at runtime.
