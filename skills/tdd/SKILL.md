---
name: tdd
description: Implement the current analyzed task test-first through observable behavior, one red-green-refactor slice at a time.
compatibility: Requires an established task with a meaningful automated test seam and runnable project tests. Uses Xcode MCP first for Xcode projects and the xcodebuild-xcsift fallback only when MCP cannot perform the operation.
disable-model-invocation: true
---

# Test-Driven Development

Implement the task already established in the conversation using test-driven development. Invoking this skill is authorization to make the scoped test and production-code changes; it is not authorization to stage, commit, push, change external systems, or broaden the task.

## Operating contract

- Consume the latest `analyze` findings and testing approach when present. Do not ask the user to restate the ticket or approve routine red-green-refactor cycles.
- Ask only when a missing product decision or material architecture choice prevents a safe implementation. Group currently known blocking questions, then resume automatically after the answer.
- Test observable behavior through the highest practical stable seam, not private implementation details.
- Work in vertical slices: one behavior, one failing test, the minimum implementation, then refactor while green.
- Preserve unrelated changes and follow repository guidance.
- Never commit automatically. Leave code review and committing as explicit subsequent workflows.

## 1. Establish the first slice

Use the analysis to identify:

- the acceptance criterion being implemented
- the recommended test seam
- the first observable behavior
- the focused test target and execution route
- any part requiring non-automated verification

If no analysis is present but the task is clear, inspect only enough code and tests to establish these facts. If there is no meaningful automated seam, stop and explain why TDD is unsuitable rather than manufacturing an implementation-coupled test.

For a partially testable task, apply TDD only to the behavior with a valid seam. Retain the analysis's preview, hardware, manual, or other verification for the remainder.

Completion criterion: one narrow observable behavior and the test that should prove it are identified without an unresolved requirement or seam decision.

## 2. Red

Write one focused test before its production implementation.

A useful test:

- describes caller- or user-visible behavior
- exercises a public or otherwise stable interface
- uses an independent expected result from the requirement or a known example
- fails if the behavior regresses while surviving internal refactoring
- mocks or fakes only true system boundaries such as network APIs, persistence, time, randomness, or hardware

Prefer existing test helpers and boundary fakes. Do not introduce a new abstraction solely to make a test possible unless the analyzed plan already established that seam.

Run only the focused test and confirm that it fails for the intended missing behavior, not because of unrelated setup, environment, or syntax problems. A compilation failure is useful red evidence only when the planned behavior intentionally requires a new public interface.

Completion criterion: the focused test has run and produced the expected red signal.

## 3. Green

Implement only enough production behavior to satisfy the current test. Avoid speculative support for later slices and avoid unrelated cleanup.

Run the same focused test through the same execution route until it passes. Fix failures within the current slice without asking for routine confirmation.

Completion criterion: the focused test passes and no requirement beyond the current slice was implemented speculatively.

## 4. Refactor

Improve names, duplication, and structure exposed by the slice while preserving behavior. Re-run the focused test after refactoring and keep it green. Skip refactoring when the implementation is already clear.

Completion criterion: the slice is clear, scoped, and green.

## 5. Repeat and verify

Repeat red, green, and refactor for the next observable behavior. Do not write all tests up front; let each completed slice inform the next.

For Xcode projects:

1. Prefer Xcode MCP's focused test tools for red-green cycles.
2. Use Xcode MCP for broader tests, builds, diagnostics, and SwiftUI previews when available.
3. Fall back to shell `xcodebuild` through the `xcodebuild-xcsift` workflow only when MCP is unavailable or lacks the required operation.
4. Treat a real MCP compilation or test failure as a result to fix, not a reason to switch execution routes. Never run both routes concurrently.

After all slices are green, run the broader focused verification identified by the analysis and inspect the final diff for scope. Perform the non-automated verification where available; never claim a fake hardware adapter proves behavior against a physical device or that logic tests prove visual correctness.

Report:

- behaviors implemented
- tests added or changed
- red and green evidence
- execution route used
- broader verification and any manual/device verification still needed
- residual risks

Finish by recommending `/skill:code-review`. Do not stage or commit.
