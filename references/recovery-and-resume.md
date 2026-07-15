# Recovery and Resume

Persist state after every task transition and before any retry. Treat `run-state.json` and task artifacts as authoritative; conversation history is not durable state.

## Failure Classes

| Class | Trigger | Retry rule | Terminal status |
|---|---|---|---|
| `transient` | API timeout, temporary tool error | Retry identical task at most twice | `blocked_technical` |
| `worker_failure` | Crash or malformed output | Restart once from task contract | `incomplete` |
| `context_limit` | Context exhaustion | Resume from artifacts and compact state | `incomplete` |
| `missing_input` | Required artifact absent | No automatic retry | `needs_input` |
| `authorization` | Required approval absent | No automatic retry | `needs_authorization` |
| `insufficient_evidence` | Acceptance criteria unmet | One bounded evidence pass | `candidate` or `blocked` |
| `conflict` | Material incompatible findings | Fresh independent verifier | `incomplete` plus a conflict record when disagreement remains |
| `policy` | Safety or policy refusal | Never retry the same objective | `policy_blocked` |
| `resource_exhaustion` | Build, simulation, storage, or hardware budget exceeded | Retry the identical experiment only within its recorded budget | `blocked_technical` |
| `snapshot_drift` | Commit, RTL config, target, toolchain, workload, or seed plan changed | Do not retry under the old record; create a new revision | `incomplete` |
| `reference_mismatch` | Difftest, assertion, waveform, or trusted model disagrees | Preserve both artifacts and assign independent triage | `incomplete` |

## Resume Procedure

1. Load `run-state.json` and validate it.
2. If it uses integer schema v1/v2 or the former microarchitecture draft string `"1.1"`, preserve a snapshot, migrate its contracts to integer schema v3, and pass strict-v3 preflight before dispatching runnable work. Never reinterpret an old active-testing boolean as a v3 approval packet.
3. Verify referenced task and evidence artifacts exist.
4. For microarchitecture runs, verify the target snapshot, task graph, experiment revisions, artifact manifest paths, and hashes before reusing results.
5. Recompute runnable tasks from dependencies and terminal states.
6. Do not reopen completed tasks unless their evidence became invalid.
7. Restart only retryable tasks within their attempt and resource budgets.
8. Route missing input, authorization, and policy blocks to the manager.
9. Continue independent safe tasks.
10. Record the resume timestamp and reason.

For every v3 profile, keep `resume.completed_tasks`, `retryable_tasks`, and `blocked_tasks` as exact, duplicate-free projections of task status; keep `next_actions` as non-empty strings. A completed run requires a non-empty checkpoint ID. Do not treat resume validation as a microarchitecture-only feature.

## Safe Fallback Rules

A fallback must change the objective and research question to a materially safer defensive question. Record `fallback_of` and preserve the original blocked task. Normalized punctuation/case-only renames fail validation; semantic similarity still requires manager review. A fallback for blocked active work must be `non_operational`. Examples include detection, mitigation, patch validation in a toy fixture, or non-operational explanation.

For every policy refusal:

1. Set the original task to `policy_blocked`; do not consume another attempt on the same objective.
2. Append the visible event to `policy-events.jsonl` and summarize accessible artifacts with `assets/templates/blocked-worker-log.md`.
3. Re-run composition review over the remaining graph.
4. Ask whether an unanswered defensive question remains. Prefer `state_inventory`, `boundary_trace`, `control_review`, or `mitigation` fallbacks.
5. Create a new task only when its objective and expected outputs are materially safer, set `fallback_of`, and update dependent tasks.
6. Preserve the capability and evidence gap in verification and synthesis.

Never:

- send the same blocked task to another worker;
- disguise the objective with euphemisms or encoding;
- split a blocked capability across workers;
- ask the synthesizer to reconstruct missing steps;
- erase the blocked status after a fallback succeeds.

## Completion Under Partial Failure

Permit partial delivery when independent tasks completed and limitations are explicit. Include:

- completed coverage;
- blocked and incomplete tasks;
- impact on confidence and conclusions;
- exact input or authorization required to resume;
- safe fallback work already performed.
