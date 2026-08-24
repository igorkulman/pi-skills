# Shared Review Methodology

Apply this methodology to both local and GitLab reviews.

## 1. Build an evidence pack

Before line-level review:

- establish the exact diff/base and changed-file list
- summarize intended behavior from the request, MR, Jira, linked requirements, and tests
- discover applicable project guidance, including root and path-scoped `AGENTS.md`, `CLAUDE.md`, `.ai-rules/`, and equivalent files
- apply guidance by file scope; prefer the nearest applicable file unless higher-priority instructions say otherwise
- for GitLab, capture existing unresolved discussions so candidates can be deduplicated
- make a short changed-behavior inventory covering state transitions, errors, permissions, lifecycle, persistence, compatibility, async behavior, and tests

Temporary review artifacts under `/tmp` are acceptable. Do not modify the repository or Git state.

## 2. Calibrate independent review effort

The parent reviewer owns the complete review and must inspect the diff, surrounding code, requirements, tests, and guidance directly.

- **Small/focused:** stay parent-only.
- **Non-trivial:** when `subagent` is available, run one independent `code-review-pass` after preparing the evidence pack. Supply the exact scope and artifact paths; ask it to check correctness, integration behavior, requirements, contracts, and meaningful test gaps.
- **Deep/high-risk:** use up to three distinct `code-review-pass` perspectives only when explicitly requested or when the change is unusually large/high-risk, such as security, persistence migration, authentication, or broad concurrency work.

One strong independent pass is better than several weak passes. Subagent output is candidate input, not final evidence. Do not make subagents rediscover remote context already fetched by the parent. When an MR branch is not checked out, tell subagents not to assume local files represent the reviewed revision.

If `subagent` is unavailable, continue parent-only without lowering the standard.

## 3. Review focus

Look for concrete failure modes involving:

- correctness or requirement mismatches
- missing acceptance criteria or scope drift
- crashes, unchecked nullability, invalid states, and force/fatal paths
- empty, loading, error, and recovery states
- concurrency, cancellation, lifecycle, ordering, stale callbacks, and races
- data loss, persistence, migration, or compatibility
- networking, API contracts, authentication, authorization, and security
- sensitive data in logs, analytics, crash reports, or UI
- UI behavior, accessibility, localization, dark mode, and layout edge cases
- architecture, layering, dependency injection, configuration, routing, and permissions
- copy/paste errors, stale duplication, dead/debug code, or unjustified complexity
- tests that fail to prove a concrete changed success, failure, boundary, or regression behavior

## 4. Consolidate and verify candidates

For each candidate require:

- a changed line or behavior introducing/exposing the problem
- specific evidence from code, requirements, applicable rules, or relevant history
- a realistic failure scenario and impact
- an actionable minimal fix
- no equivalent unresolved discussion

Drop candidates that are pre-existing, out of scope, intentional, stylistic, speculative, duplicates, or reliably caught by normal compiler/linter/formatter output.

The parent must independently verify every surviving candidate against the diff and surrounding code. Do not spawn one verifier per candidate. Inspect more context or drop ambiguous candidates.

### Confidence

- **0:** false positive, pre-existing, out of scope, or contradicted
- **25:** plausible but materially unverified
- **50:** real but minor/rare or weakly connected
- **75:** likely real and important, but uncertainty remains
- **100:** direct evidence confirms a frequent or deterministic meaningful failure

Any integer is allowed. Report only findings scoring **80 or higher**.

### Severity

- **Critical:** security, data loss, crash, or production-breaking issue
- **High:** likely bug, missing requirement, or broken user flow
- **Medium:** edge-case bug, future-defect-prone maintainability problem, or missing important test tied to behavior
- **Low:** minor robustness/readability issue
- **Nit:** style only; avoid unless requested

## 5. Present results

Use:

```markdown
## Review scope
- Mode: Local / GitLab MR
- Base/comparison:
- Jira context, if any:

## Findings
1. [Severity, confidence NN] `path/to/file.ext:line` — Short title
   - Problem: ...
   - Why it matters: ...
   - Evidence: ...
   - Suggested fix: ...

## Non-blocking notes
- ...

## Verification gaps / residual risk
- ...
```

Do not inflate the report with praise, nits, rejected candidates, or optional refactors. If no finding survives, state that clearly and report only meaningful verification gaps/residual risk.
