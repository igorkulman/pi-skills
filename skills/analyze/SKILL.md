---
name: analyze
description: Perform read-only investigation and implementation planning for Jira issues and user-described bugs, features, or requested changes. Use when the user invokes /analyze or asks to understand and plan work before implementation. Do not use for reviewing an existing diff, branch, or merge request.
compatibility: Requires repository read access. Jira-backed tasks also require jira-task-context authentication.
---

# Analyze

Gather enough evidence to explain the current behavior and propose a safe implementation. Stay read-only while using this skill.

## Rules

- Do not edit files, change dependencies, mutate Git state, run formatters, or update external systems.
- Inspect only what is needed to identify the relevant code path, likely change locations, risks, and verification.
- Preserve uncertainty: distinguish confirmed behavior from assumptions and ask targeted questions when an unknown blocks a safe plan.
- If the user explicitly requested implementation, complete the concise analysis first and then continue with implementation. Otherwise stop and ask for approval.
- For investigation-only requests, provide conclusions and state that no changes were made.

## Route by task source

- **Jira URL/key:** load `jira-task-context`, gather the issue and directly relevant linked context, then inspect the repository against those requirements.
- **Local changes or branch:** inspect repository status, the exact diff/base, surrounding code, and related tests.
- **Plain task or bug report:** search for the named behavior, screen, symbol, error, API, model, or feature flag, then inspect nearby implementations and tests.
- **Repository question:** inspect only the files and history needed to answer it.

Do not duplicate detailed Jira traversal in this skill; delegate it to `jira-task-context`.

## Inspection goals

Identify:

- current behavior and the relevant code path
- likely root cause, missing behavior, or requirement gap
- files and modules likely to change
- existing patterns or similar implementations to follow
- tests, previews, fixtures, and verification commands
- whether the change is a good TDD candidate, the observable seam to test, and the first behavior to drive test-first
- meaningful edge cases, compatibility concerns, and unresolved questions

Use history only when it helps explain an invariant or likely regression. Stop once the implementation path is clear enough to act safely.

## Assess TDD suitability

Classify the proposed change instead of merely checking whether some code can be tested:

- **Yes:** an automated test can express the requested observable behavior through an existing or clearly appropriate stable seam.
- **Partial:** only part of the change has a meaningful automated seam, such as testable state logic combined with visual UI work.
- **No:** the change is primarily visual, generated, configuration-only, or depends on an unavailable environment with no useful local substitute.

Name the highest practical seam that proves behavior without coupling the test to implementation details. Identify the first narrow behavior that could be driven red-to-green, an existing or proposed test target, and the focused execution route or command that would run it. If no suitable seam exists, explain the constraint and give the strongest practical verification instead. Do not invent a test target or execution route; mark unknowns explicitly.

For **Yes**, recommend continuing with `/skill:tdd`. For **Partial**, identify exactly which behavior should use TDD and how the remainder should be verified. For **No**, recommend normal implementation with the listed verification.

## Plan vertical slices

For work containing multiple independently deliverable behaviors, replace a layer-by-layer implementation plan with ordered vertical slices:

- each slice delivers a narrow, complete, observable behavior rather than only changing one technical layer
- each slice names its observable result, genuine blockers, and independent verification
- blocker-free slices come first; do not invent dependencies merely because one implementation order feels familiar
- include prerequisite refactoring only when it is required to make a behavioral slice safe, and state which behavior it enables
- size each slice so it can be implemented and verified within one focused session

Avoid horizontal plans such as “change model, then manager, then UI, then tests.” For a small ticket with only one behavior, keep the concise numbered implementation steps instead of adding slicing ceremony.

## Output

Use the smallest useful subset of this structure. Use `## Proposed implementation` for a small single-behavior task or replace it with `## Implementation slices` for larger work; do not emit both.

```markdown
## Task understanding
- Source and goal:
- Expected behavior or acceptance criteria:

## Findings
- Current behavior / likely gap:
- Existing patterns to follow:

## Relevant files
- `path`: why it matters

## Proposed implementation
1. ...
2. ...

## Implementation slices
1. Slice title
   - Observable result:
   - Blocked by: None / slice reference
   - Verification:

## Testing approach
- TDD suitability: Yes / Partial / No
- Recommended implementation mode: `/skill:tdd` / mixed / normal
- Rationale:
- Recommended test seam:
- First observable behavior:
- Focused test target and execution route:
- Additional verification:

## Risks / questions
- ...
```

When implementation was not explicitly requested, finish with:

```text
Proceed with implementation?
```
