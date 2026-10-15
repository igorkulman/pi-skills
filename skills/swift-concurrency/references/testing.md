# Testing Concurrent Code

## Test observable contracts

Test results, ordering guarantees, cancellation behavior, error propagation, and lifetime at the highest stable seam. Avoid tests whose only assertion is that an implementation happened to run on a particular thread.

Use the framework already configured by the target: Swift Testing or XCTest. Do not migrate frameworks as part of an unrelated concurrency fix.

Annotate a test `@MainActor` only when setup, subject, or assertions require main-actor-isolated APIs.

## Determinism

Prefer controllable dependencies over scheduler luck:

- inject a clock for debounce, timeout, and retry behavior
- suspend a fake dependency until the test explicitly resumes it
- observe actor state through an async API
- use a barrier or continuation owned by the test when exact sequencing is the behavior under test

Do not use arbitrary sleeps as synchronization. `Task.yield()` may help expose scheduling opportunities, but it does not guarantee another task ran and should not be the sole correctness mechanism.

If a specialized concurrency-testing package is already present, follow its established pattern. Do not add one without explicit authorization and a demonstrated need.

## XCTest

Use async test methods for async APIs. In an async XCTest, prefer `await fulfillment(of:timeout:)` over synchronous waiting APIs. Keep expectation fulfillment counts and inversion semantics explicit.

Consume task results so thrown errors fail the test. Cancel tasks created by the test during cleanup when an assertion can exit early.

## Swift Testing

Use async `@Test` functions directly. Prefer confirmations for callback behavior and require the expected number of confirmations. Use suite serialization only when the tested contract truly shares global state; do not serialize a suite to mask races in production code.

## Useful cases

For an owned long-lived task, test that:

- starting twice does not leak duplicate work unless duplication is intended
- cancellation reaches the underlying operation
- the owner can deallocate after stopping
- errors are surfaced through the public contract

For actors and reentrancy, test state changes across a controlled suspension point. For task groups, test partial failure and cancellation of remaining children. For streams, test finish, error, consumer cancellation, and buffering behavior.

Run a focused test repeatedly when investigating flakiness, but do not treat repeated success as proof of race freedom. Use Thread Sanitizer or Instruments when appropriate, while accounting for their runtime overhead and incomplete coverage.
