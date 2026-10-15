# Core Data Concurrency

Core Data has its own context-confinement model. Integrate that model with Swift concurrency rather than declaring managed objects `Sendable`.

## Boundaries

`NSManagedObject` instances belong to their managed object context and should not cross actor or task boundaries. Cross boundaries with:

- `NSManagedObjectID`
- immutable `Sendable` snapshots or DTOs
- stable scalar identifiers that can be fetched in the destination context

Perform fetches and mutations through the context's scheduled `perform` API appropriate to the deployment target. Do not assume an actor alone makes direct access to a context or managed object safe.

## API design

Keep managed objects inside the persistence implementation. Expose async operations that accept and return IDs or value snapshots. Decide where saves occur and how save errors propagate; do not launch an unobserved task from a synchronous persistence callback.

When a UI layer needs live objects, keep access on the context and actor required by the framework setup, commonly a main-queue view context. Background import or processing should use its own context and merge results through object IDs or persistent-history mechanisms.

## Default isolation interactions

Generated managed-object subclasses and extensions can conflict with a module that defaults all declarations to `MainActor`. Inspect generated-code settings and target isolation before adding annotations. Prefer separating persistence implementation from a default-main-actor UI module when that matches the architecture.

## Advanced executors

A custom actor executor backed by an `NSManagedObjectContext` can align actor execution with context scheduling, but it is advanced infrastructure with availability, executor-conformance, and lifetime constraints. Use it only when existing context APIs cannot provide a clear boundary, and validate the exact implementation with current Apple documentation and the project toolchain.

Do not copy a custom executor pattern from a different Swift or OS version without compiling and testing it on every supported deployment target.

## Verification

Test:

- operations invoked from more than one caller
- save and fetch errors
- cancellation expectations, noting that underlying Core Data work may not be interruptible
- object deletion or invalidation between ID creation and destination-context fetch
- parent/child or background/view-context merge behavior

Enable Core Data concurrency debugging and Thread Sanitizer when diagnosing confinement violations, understanding that neither replaces tests of the public persistence contract.
