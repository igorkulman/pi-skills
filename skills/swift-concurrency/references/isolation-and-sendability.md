# Isolation and Sendability

## Model isolation before threads

Swift concurrency protects mutable state with isolation domains:

- a global actor such as `MainActor`
- a specific actor instance
- task-isolated values
- nonisolated code, which has no actor protection

An actor serializes access to its isolated state, but an actor method is reentrant at suspension points. Revalidate assumptions after `await` instead of treating the entire method as an atomic transaction.

`MainActor` is appropriate for UI-bound state and APIs whose contract requires main-actor access. It is not a generic repair for non-`Sendable` data. Isolating a whole type changes every caller and protocol conformance, so prefer the narrowest boundary that matches ownership.

## Actor design

Use an actor when one owner must serialize shared mutable state across concurrent callers. Keep synchronous mutations that must be atomic within one actor turn. Move slow I/O outside an actor only when doing so preserves invariants; asynchronous I/O suspends rather than blocking the actor's executor.

Avoid returning mutable reference state owned by an actor. Return immutable snapshots or value types instead.

When a protocol requirement crosses isolation domains, make isolation part of the protocol contract when possible. Do not hide a mismatch with `assumeIsolated` unless an external invariant proves the caller is already on that actor.

## `Sendable`

`Sendable` describes values whose public semantics allow safe transfer across isolation boundaries.

Good candidates include:

- immutable value types whose stored values are `Sendable`
- reference types with immutable state
- reference types whose mutable state is completely synchronized and whose synchronization invariant is documented
- actors, which protect their isolated mutable state

A conformance is an API promise, not a compiler suppression. Do not add `@unchecked Sendable` to a mutable class without proving all access is synchronized, including callbacks and indirectly referenced state.

`@Sendable` closure captures are checked as values crossing a concurrency boundary. Prefer immutable captures, capture `Sendable` snapshots, or move mutation behind an actor.

## `sending` and region-based isolation

`sending` applies to a parameter or result value whose region is transferred, rather than declaring its type universally `Sendable`. Use it only when the caller will not use the transferred value afterward and the compiler can prove the value is disconnected from other state.

Do not add `sending` as a reflexive fix. If aliases remain at the caller or the value belongs to an actor, transferring it would violate ownership and should be rejected.

## Default actor isolation

Default actor isolation is configured per module. A module can infer `MainActor` for otherwise-unannotated declarations; imported modules keep their own isolation choices. Inspect the setting before interpreting an unannotated declaration.

Default-main-actor isolation is often useful for app/UI modules. Library, domain, storage, and compute modules often need nonisolated defaults. Changing this setting is a source migration, not a warning toggle.

Modern toolchains can infer global-actor-isolated protocol conformances. Treat an isolated conformance as usable only from its isolation domain; add a nonisolated conformance only when every requirement can safely be satisfied without actor state.

## Unsafe escapes

- `@preconcurrency` defers checking for imported declarations; it does not make a dependency thread-safe.
- `@unchecked Sendable` moves the proof obligation from the compiler to the programmer.
- `nonisolated(unsafe)` removes isolation checking for that declaration.
- `MainActor.assumeIsolated` dynamically asserts an executor precondition and can trap when the assumption is false.

For each use, document the invariant beside the code and keep the escape local enough to remove later.
