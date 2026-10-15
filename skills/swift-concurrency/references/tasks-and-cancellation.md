# Tasks and Cancellation

## Choose the narrowest task form

Prefer direct `await` for one operation. Use `async let` for a fixed, small number of independent child operations and a task group for a dynamic number of children.

Structured children inherit priority and task-local values, are awaited before the scope exits, and receive cancellation from the parent. A task group scope does not finish until all children finish, so every child must cooperate with cancellation.

Use `Task { ... }` to bridge a synchronous entry point only when structured concurrency cannot express the boundary. Store the handle when work outlives the call, define its owner, cancel it when the owner stops needing it, and consume or deliberately handle errors. An unstructured task does not become a child whose cancellation is automatically tied to the creating task.

`Task { ... }` inherits actor isolation, priority, and task-local values from its creation context. It does not force work off `MainActor`. `Task.detached` also discards those inherited values; use it only when that independence is explicitly wanted.

## Cancellation

Cancellation marks a task; it does not forcibly stop execution.

- Prefer cancellation-aware APIs such as clock sleeps and async sequence iteration.
- Call `Task.checkCancellation()` when cancellation should immediately throw.
- Check `Task.isCancelled` in long CPU loops and return promptly.
- Use `withTaskCancellationHandler` to cancel an underlying callback operation or release an external resource.
- Preserve `CancellationError` unless the API intentionally translates it.

A cancellation handler can race with operation setup. Synchronize access to cancellation tokens or operation handles rather than assuming setup finishes first.

## Errors and groups

Use throwing task groups when one child failure should fail the operation. Decide explicitly whether to:

- fail fast and cancel remaining work
- collect independent successes and failures
- ignore a known, documented class of errors

Always iterate or otherwise consume group results when child errors and values matter. Avoid `try?` around task values unless discarding the error is part of the contract.

## Task lifetime and memory

A task strongly retains captured values for as long as it uses them. A stored task that runs an endless stream can therefore keep its owner alive indefinitely.

Prefer this ownership shape:

1. The owner stores the task handle.
2. The task has a clear termination or cancellation path.
3. The owner cancels the task when the operation is no longer needed.
4. The task avoids repeatedly strengthening a weak owner across a long loop.

A weak capture alone is not a complete lifetime design. Inspect where `self` becomes strong and how long that strong reference remains live.

## Priorities and scheduling

Priority is a scheduling hint, not a quality-of-service guarantee or a dedicated queue. Let child tasks inherit priority unless the work has a justified independent priority.

Do not use sleeps or repeated `yield()` calls as synchronization. Model readiness with an async API, continuation, stream, actor state, or test-controlled dependency.

Never block a cooperative executor with a semaphore, condition-variable wait, or synchronous dispatch back to an executor that may already be occupied. A short synchronous lock can protect non-suspending state, but never hold it across `await`.
