# Policy-Aware Decomposition

Use this reference before dispatching dual-use or exploitation-adjacent work. Granularity improves evidence quality and limits context, but it must never be used to evade safety review.

## Capability Boundaries

| Boundary | Permitted content | Typical task classes | Required approval |
|---|---|---|---|
| `non_operational` | Passive facts, source evidence, state lifecycle, reachability constraints, controls, mitigations, regression properties | context map, state inventory, boundary trace, control review, verification, mitigation | Run authorization and local read scope |
| `active_authorized` | A specifically approved dynamic method against the named local/authorized target, within stated limits | active validation | Completed active-testing approval packet |

Do not create an intermediate label for "almost operational." If a task specifies dynamic inputs, executable construction, probing, mutation, or target interaction, classify it as `active_authorized` and require approval.

## Bounded Task Test

A discovery or analysis task is dispatchable only when all answers are yes:

1. Does it name one resource family or trust boundary?
2. Does it ask one question whose answer can be supported by a defined artifact set?
3. Does it have one evidence goal, such as a lifecycle matrix or interface trace?
4. Are active actions structurally empty for a `non_operational` task?
5. Can its output stand alone without another worker supplying hidden operational steps?
6. Does its composition with sibling outputs remain within the run boundary?

If no, split by research question or remove the unsupported capability. Do not split a restricted capability into fragments that are intended to be recombined.

## Recommended Task Shapes

### Context Map

- Scope: one effective product/configuration.
- Question: what is instantiated, who owns state, and where is the context boundary?
- Output: module/data-flow map and stable source identity.

### State Inventory

- Scope: one resource family.
- Question: what state exists and when is it initialized, read, updated, held, drained, restored, or cleared?
- Output: storage/lifecycle matrix with source evidence.

### Boundary Trace

- Scope: one identity or transition boundary.
- Question: where do domain, privilege, tenant, epoch, fence, reset, and invalidate signals flow, and which state owners consume them?
- Output: producer-to-consumer trace and uncovered owners.

### Control Review

- Scope: one protection objective.
- Question: do partitioning, tagging, flushing, draining, save/restore, and monitoring cover all relevant state?
- Output: control matrix, gaps, and defensive assertions.

### Verification

- Scope: one claim cluster with a common root cause.
- Question: does independent evidence establish the claim after configuration and counterexample checks?
- Output: verdicts and fresh evidence.

### Active Validation

- Scope: one approved target and method class.
- Question: does the named defensive check reproduce the stated effect within approved limits?
- Output: bounded test evidence and rollback record.
- Gate: do not create or dispatch before explicit active-testing approval.

## Prompt Construction

Generate the worker prompt from structured task fields. Put the capability boundary first. For example:

```text
Purpose: passive defensive state inventory.
Capability boundary: non_operational; active actions are empty.
Question: Which state does <resource family> own, and which reset or context signals clear it?
Inputs: <exact source paths and revision>.
Outputs: report.md and evidence.jsonl with file:line locators.
Prohibited: dynamic tests, executable construction, collision recipes, source edits, or scope expansion.
```

Use literal terms when they are necessary to describe the source or risk. Do not use euphemisms to conceal an objective. If an accurate prompt is not allowed at the selected capability boundary, change the objective or obtain approval.

## Policy Refusal Handling

Treat a refusal as evidence about task formulation, not evidence about the researched system.

1. Preserve the original task and mark it `policy_blocked`.
2. Record only the visible event and accessible artifacts.
3. Do not resend, rephrase, encode, or fragment the same objective.
4. Re-run composition review.
5. Create a fallback only for a remaining materially safer question, such as state lifecycle, identity propagation, control coverage, mitigation, or a non-operational explanation.
6. Give the fallback a new ID and `fallback_of`; keep the original coverage gap visible.

Safe fallback example:

```text
Blocked objective: construct and rank a cross-context observation method.
Safer unanswered question: inventory persistent state and verify whether context identity or invalidation reaches each owner.
```

Unsafe fallback example:

```text
Split construction, input selection, observation, and ranking across four workers, then recombine them.
```

## Manager Review Before Dispatch

Run `scripts/preflight_tasks.py`. Then inspect warnings that automation cannot decide:

- whether one resource scope is still semantically too broad;
- whether sibling outputs create composition risk;
- whether the evidence goal actually answers the research question;
- whether active actions are necessary and approved;
- whether a fallback is materially safer rather than cosmetically renamed.
