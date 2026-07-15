# Recovery and Resume

Persist state after every task transition and before any retry. Treat `run-state.json` and task artifacts as authoritative; conversation history is not durable state.

## Failure Classes

| Class | Trigger | Retry rule | Recorded outcome |
|---|---|---|---|
| `transient` | API timeout, temporary tool error | Retry identical task at most twice | `blocked_technical` |
| `worker_failure` | Crash or malformed output | Restart once from task contract | `incomplete` |
| `context_limit` | Context exhaustion | Resume from artifacts and compact state | `incomplete` |
| `missing_input` | Required artifact absent | No automatic retry | `needs_input` |
| `authorization` | Required approval absent | No automatic retry | `needs_authorization` |
| `insufficient_evidence` | Acceptance criteria unmet | One bounded evidence pass | Finding verdict `candidate` or `blocked`; task `incomplete` when no accepted output remains |
| `conflict` | Material incompatible findings | Fresh independent verifier | Conflict record plus verifier task; preserve unresolved disagreement in limitations |
| `policy` | Safety or policy refusal | Never retry the same objective | `policy_blocked` |

## Resume Procedure

1. Load `run-state.json` and validate it.
2. Verify referenced task and evidence artifacts exist.
3. Recompute runnable tasks from dependencies and terminal states.
4. Do not reopen completed tasks unless their evidence became invalid.
5. Restart only retryable tasks within their attempt budget.
6. Route missing input, authorization, and policy blocks to the manager.
7. Continue independent safe tasks.
8. Record the resume timestamp and reason.

## Safe Fallback Rules

A fallback must change the objective to a materially safer defensive question. Record `fallback_of` and preserve the original blocked task. Examples include detection, mitigation, patch validation in a toy fixture, or non-operational explanation.

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
