---
name: pragmatic-testing
description: Assess test value before adding, changing, reviewing, or deleting tests and test doubles, in TDD or ordinary implementation. Identify realistic regressions, independent expectations, appropriate seams, and evidence needed to prune tests safely.
---

# Pragmatic Testing

Optimize for regression protection, not test count or coverage percentage. Apply these rules in both test-first and ordinary implementation; this skill does not replace TDD's red-green-refactor cycle.

Loading this skill does not authorize changes. During investigation, review, or audit, remain read-only. Follow the enclosing task's authorization and repository guidance.

## Before writing or changing a test

Identify, briefly in the plan, test name, or a useful comment:

1. **The contract:** which caller- or user-observable behavior is required?
2. **The plausible bug:** which concrete mistake would make this test fail? Prefer a reversed comparison, missing filter, incorrect precedence, lost write, or wrong interleaving. Merely deleting the function or leaving it unimplemented is not enough.
3. **The real path:** does the test exercise the production behavior, rather than fixture construction or a double's copy of the rule?
4. **The independent expectation:** what requirement, independently checked example, invariant, or external reference determines the answer?
5. **The added protection:** which distinct behavior, boundary, failure mode, or integration contract does it protect, and would it survive a behavior-preserving internal refactor?

If an answer is missing, improve the scenario or seam rather than adding a ceremonial assertion. Do not invent a product rule: ask when the required result is unclear. Read [the examples](references/examples.md) before applying these rules for the first time in a task.

## Choose the seam and scope

- Test a rule at the stable interface of the component that owns it. Choose the highest practical seam that proves the behavior without unnecessary setup or implementation coupling; do not force every rule through the UI.
- Avoid replaying the same rule's full case matrix at every layer. A higher-level test should prove a distinct wiring or integration contract.
- Overlapping execution is not automatically redundancy: a domain test and an integration test can catch different mistakes. Explain the protection, not just which lines run.
- Prefer a few meaningful scenarios over exhaustive restatements of the implementation. There is no fixed test budget. Boundaries, errors, concurrency, recovery, security, and financial rules may need many cases.
- Parameterize cases that express the same rule with different inputs. Keep distinct behaviors and interleavings intelligible; a table is not a way to hide a giant suite behind one test name.
- Pure forwarding or compiler-enforced structure may need no new test. Name the existing test or static check that catches a plausible mistake. If none exists, state the verification gap rather than claiming coverage. Do not dismiss a new product rule as trivial just because its implementation is short.

## Expectations and assertions

- Use independently derived literals or independently justified properties. Never copy production branching or call the production helper to calculate its own expected result.
- A characterization test may record current behavior for refactoring. Label it as such; copied output is not proof that the behavior meets the requirement.
- Assert the contract, including meaningful negative effects and outcomes, not every intermediate value. Whole-result assertions are useful when the whole result is contractual, not when they pin incidental fields.
- A test that echoes a stubbed value earns its place only if it proves a distinct contract, such as correct request parameters or failure propagation. An identity assertion alone is not enough.
- Do not assert fixture contents, language guarantees, or setter/getter mechanics unless production logic adds a meaningful rule.

## Test doubles and asynchronous work

- Reuse the project's existing mocks, fakes, and helpers; do not mandate a generator or introduce an abstraction merely to enable a test.
- Stub collaborators as needed, but keep the rule under test in real production code. A double may control scheduling, return values, and errors; it must not implement the filtering, retry, pricing, or other product algorithm the test claims to cover.
- Use the real implementation for contracts such as database constraints, filesystem atomicity, or parser semantics. Isolate it with temporary resources or the project's integration harness.
- Verify observable effects and required interactions: writes, purchases, navigation, mutations, or the absence of an irreversible action after failure. Read call counts are usually incidental unless caching, single-flight, debounce, or another explicit contract makes them meaningful.
- For asynchronous behavior, control time or scheduling where appropriate and await a bounded completion signal. Avoid sleeps and loose assertions such as "at least one item" when the contract requires a complete result. Preserve tests of meaningful ordering, cancellation, races, and hangs.

## Establish that the test detects a bug

- In TDD, retain the enclosing skill's witnessed red on the intended missing behavior, then green after implementation.
- For bug fixes with a meaningful runnable seam, run the reproduction on unfixed code and observe the reported failure before fixing it. A later mutation tests a regression hypothesis, not whether the original bug was reproduced.
- An initial red does not alone prove sensitivity to a subtle wrong implementation. When effectiveness remains uncertain, use a targeted mutation: temporarily introduce the named plausible mistake into production and run the focused test. It must fail for that mistake, not from compilation or setup failure. A surviving mutation means the assertion, scenario, or seam needs attention.
- Mutation checks are selective, not mandatory for every assertion. Prefer them for indirect tests, complex doubles, risky rules, and claims that a replacement test preserves protection.
- Only mutate during authorized implementation or verification, never during read-only review. Snapshot the exact pre-mutation contents, apply one small mutation at a time, restore in cleanup even after failure, and confirm restoration by content comparison or hash. Preserve unrelated edits; never stash, reset, or use Git checkout to restore files. Do not overlap mutations or share a mutated workspace with other checks. If safe restoration cannot be assured, do not mutate.
- Report what ran, the intended and observed failure, and the restored green result. If execution is unavailable, state that effectiveness remains unverified.

## Auditing or pruning existing tests

Report candidates before editing unless the requested task already authorizes the scoped cleanup. For each candidate, identify the claimed bug, relevant bug-fix history, and the stronger protection that would remain.

- Rewrite a weak test if it is the only protection for a meaningful path. Do not delete it merely because its current assertions or waiting strategy are poor.
- Preserve distinct integration contracts, real-bug regressions, failure-mode tests, and race/hang proofs unless equivalent protection is demonstrated.
- Never weaken assertions or change production behavior to meet a deletion target. Discovering a production refactor opportunity does not authorize an unrelated refactor.

For an authorized prune:

1. Record the pre-change test result and coverage before editing. Compare the same relevant test scope and configuration afterward, preferably per function or branch. Use the actual pre-prune state, including relevant local edits, not blindly the merge base.
2. Investigate every coverage drop, especially paths falling to zero. Each needs restored or rewritten protection, or an explicit contract-based reason. Equal coverage alone does not prove equivalent assertions.
3. Target plausible mutations at changed tests and paths where coverage fell. Before pruning, identify which removed or rewritten test detects each mistake; afterward identify the retained or replacement test that detects it. Restore or improve protection when a formerly detected mistake survives.
4. Report the removed tests, retained contracts, coverage changes, mutation results, and gaps. Independent review is useful, but neither reviewer agreement nor a small mutation sample proves the entire suite equivalent. If baseline, coverage, or mutation evidence is unavailable, explicitly mark preservation of protection as unverified.

Use the project's normal test route. For Xcode, prefer Xcode MCP; use `xcodebuild-xcsift` only when MCP is unavailable or cannot perform the needed operation. Never rerun a real MCP test failure through the shell.

## Provenance

Adapted from the principles in [Pragmatic Testing for Agents](https://sergdort.github.io/pragmatic-testing-for-agents/) and its [companion skill](https://gist.github.com/sergdort/bf5bc692937f9789e4a121ecb47be6ed), with project-independent tooling, scoped authorization, and preservation of unrelated changes.
