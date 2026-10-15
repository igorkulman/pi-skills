# Async Streams and Continuations

## Choose the API shape

Use an async function for one eventual result. Use `AsyncSequence` for zero or more values over time. Do not turn a one-shot callback into a stream or an event source into repeated unstructured tasks without a lifecycle.

Prefer a framework's native async API before writing a bridge.

## Checked continuations

Use `withCheckedContinuation` or `withCheckedThrowingContinuation` to bridge a callback that completes exactly once.

The bridge must guarantee:

- every path resumes exactly once
- synchronous callback completion is safe
- thrown errors and cancellation map to the intended result
- callback storage and cleanup have a defined owner
- no lock is held while resuming arbitrary code

A checked continuation detects some misuse but does not provide cancellation automatically. If the underlying operation is cancellable, connect task cancellation to it and account for the race between cancellation and operation registration.

Do not use an unsafe continuation for convenience. Reserve it for a measured case where the checked variant's diagnostics or overhead are unsuitable and the exactly-once invariant is independently proven.

## `AsyncStream` and `AsyncThrowingStream`

Define these semantics before creating a stream:

- buffering policy and behavior under producer pressure
- whether multiple consumers are supported
- what finishes the stream
- how errors terminate it
- what happens when the consumer cancels or releases iteration
- who retains the continuation and producer

Set an appropriate termination handler to detach delegates, remove observers, cancel underlying work, and release stored continuations. Finish the continuation on every terminal producer path.

Do not assume every yielded element is consumed. Buffering policies can drop values, and a slow consumer can otherwise cause unbounded memory growth.

## Sequence processing

Use `for try await` when values must be handled serially in arrival order. If each element starts concurrent work, bound that concurrency explicitly with a task group or another capacity limit; do not spawn an unlimited unstructured task per element.

Cancellation should stop iteration and propagate to owned producers. Verify behavior when cancellation occurs while no element is available.

Before adding Async Algorithms or another package, check whether the repository already uses it and whether the required operation justifies the dependency. Adding a dependency requires the same authorization and verification as any other project change.
