# Task and Evidence Contracts

Use the bundled JSON templates as the machine-readable source of truth.

## Task Contract

Every task must define:

- `task_id`, `role`, `objective`, and one `research_question`;
- `dependencies` and `assigned_paths`;
- `inputs` with stable artifact locations;
- `allowed_actions` and `prohibited_actions`;
- `expected_outputs` and `acceptance_criteria`;
- `evidence_requirements`;
- `stop_conditions` and `escalation_conditions`;
- a structured `safety` block with `purpose`, `task_class`, `capability_boundary`, `resource_scope`, `evidence_goal`, `active_actions`, `approval_ref`, `composition_dependencies`, and `safe_fallback`;
- `status`, `attempts`, and `max_attempts`.

For `microarchitecture-security`, also require `schema_version`, `phase`, `execution_mode`, `target_snapshot`, and `resource_requirements`. Use execution mode `read-only`, `passive-research`, `local-simulation`, `formal-execution`, `fpga`, or `silicon`; executable modes require `active_validation`, and hardware modes require A2. The task snapshot must match `scope.target_snapshot`, including repository, commit, dirty state, submodules, configuration, ISA/privilege assumptions, target class, toolchain, reference model, and workloads. Every exclusive simulator, FPGA, silicon target, licensed tool, mutable checkpoint, or build directory must appear in `resource_requirements.exclusive_resources` and in the run task graph.

Reject a task if its objective is broad, its outputs overlap another worker, or success cannot be tested.

Treat each `task_id` as a safe single path segment. A completed task must have non-empty declared outputs inside `tasks/<same-task-id>/`; only a `synthesis` task that owns `final/` may declare final-report outputs. Do not satisfy one task's contract with another task's artifact.

For `context`, `discovery`, and `analysis` tasks, enforce one resource family or trust boundary and one evidence goal. Split state inventory, boundary tracing, active validation, verification, and mitigation into separate tasks. A small file count does not make a task safe; the capability boundary and combined outputs determine safety.

Use these task classes:

- `context_map`: effective implementation, configuration, trust boundaries, and ownership;
- `passive_research`: one bounded advisory, history, version, standards, or primary-source question;
- `state_inventory`: storage, lifecycle, inputs, outputs, and reset/flush coverage for one resource family;
- `boundary_trace`: identity, authorization, privilege, tenant, or context signals across one boundary;
- `control_review`: preventive, detective, recovery, and mitigation coverage;
- `active_validation`: approved dynamic action with an explicit approval packet;
- `evidence_normalization`: convert sourced observations into the common evidence/finding schema;
- `risk_ranking`: rank verdict-bearing risks without adding new discovery claims;
- `verification`: independent evidence and false-positive review;
- `mitigation`: defensive design and regression checks;
- `synthesis`: verdict-bearing artifact composition only.

Map profile steps to canonical task classes rather than inventing new schema values:

| Profile step | Task class |
|---|---|
| advisory research, change history, version analysis, standards lookup | `passive_research` |
| surface cluster, discovery worker, inventory | `state_inventory` |
| reachability, trust boundary, identity propagation | `boundary_trace` |
| environment controls, control review | `control_review` |
| finding normalization | `evidence_normalization` |
| risk ranking | `risk_ranking` |
| false-positive check, scenario verification | `verification` |
| remediation or mitigation design | `mitigation` |

## Worker Prompt Envelope

Construct worker prompts in this order:

1. State defensive purpose, task class, and capability boundary.
2. State the role and single research question.
3. Provide exact inputs and one resource scope.
4. List allowed and prohibited actions, including whether active actions are empty or approved.
5. State evidence and output requirements.
6. State stop and escalation conditions.
7. Require artifact paths and a concise completion summary.

Do not include other workers' conclusions or manager preferences.

Schema v3 binds active work to the run approval packet: `active_validation` requires `active_authorized`, non-empty `active_actions`, a matching `approval_ref`, and membership in `active_testing_approval.approved_task_ids`. Versions 1 and 2 remain readable for archival validation. Migrate a legacy run to v3 and pass `preflight_tasks.py --strict-v3` before dispatching or resuming runnable work.

## Microarchitecture Experiment Contract

Use `assets/templates/experiment.json` only for an approved `active_validation` task. Require:

- the same `approval_ref` as the task and run approval packet;
- one falsifiable hypothesis and non-empty independent, dependent, and controlled variables;
- pinned target snapshot, workloads, controls, observables, seeds/repetitions, stop criteria, and resource budget;
- expected artifact IDs before execution;
- a new `revision` whenever commands, target configuration, workload, seeds, instrumentation, or budget changes.

Write results only under `experiments/<experiment-id>/results/`. Register each realized result in `artifacts/manifest.jsonl` using `assets/templates/artifact-record.json`. The producer must own the experiment; the record must carry the matching snapshot and a populated SHA-256 hash. Planned experiments need contracts but not realized artifacts. Completed experiments and artifact-backed evidence require the manifest.

## Policy Event Contract

On a safety or policy refusal, append one record to `policy-events.jsonl` using the bundled template. Record only the visible failure message and artifact status; hidden model context is not available evidence. Mark the original task `policy_blocked` and preserve it.

A fallback must answer a materially safer defensive question. Set `fallback_of` to the blocked task, use a new task ID, update dependencies, and state the lost coverage. Do not create several smaller tasks whose combined outputs reconstruct the blocked objective.

## Evidence Record

Write one JSON object per line in `evidence.jsonl`:

```json
{
  "evidence_id": "EV-SR-001-01",
  "task_id": "SR-001",
  "kind": "source_code",
  "locator": "src/auth/session.ts:142",
  "observation": "Session identifier enters the lookup without normalization.",
  "supports": ["F-SR-001-01"],
  "artifact_id": null,
  "source_date": null,
  "sensitivity": "internal",
  "hash": null
}
```

Prefer primary artifacts: source code, configuration, logs, test output, standards, vendor advisories, and authoritative vulnerability records. Label secondary commentary as secondary.

Set `artifact_id` when an evidence record depends on a generated experiment artifact. Leave it absent or null for source-only evidence; never cite an unregistered log, waveform, counter dump, or analysis output.

## Finding Contract

Every finding must contain:

- stable ID and concise title;
- affected scope and preconditions;
- observation, interpretation, and impact as separate fields;
- evidence IDs;
- counter-evidence and false-positive hypotheses;
- severity and confidence with short rationales;
- verification status and verifier task ID;
- remediation and regression-check proposal;
- limitations and redactions.

Never mark a finding `verified` solely because multiple agents repeat the same claim.
