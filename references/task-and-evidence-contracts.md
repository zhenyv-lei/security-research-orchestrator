# Task and Evidence Contracts

Use the bundled JSON templates as the machine-readable source of truth.

## Task Contract

Every task must define:

- `task_id`, `role`, `objective`, and one `research_question`;
- `schema_version`, `phase`, and `execution_mode`;
- `dependencies` and `assigned_paths`;
- `inputs` with stable artifact locations;
- a pinned `target_snapshot` and bounded `resource_requirements` for executable architecture tasks; non-architecture passive tasks may set `target_snapshot` to `null`;
- `allowed_actions` and `prohibited_actions`;
- `expected_outputs` and `acceptance_criteria`;
- `evidence_requirements`;
- `stop_conditions` and `escalation_conditions`;
- `status`, `attempts`, and `max_attempts`.

Reject a task if its objective is broad, its outputs overlap another worker, or success cannot be tested.

## Task Graph Contract

Record graph edges, runnable waves, and exclusive resources in `run-state.json`.

- Every edge is `[dependency_task_id, dependent_task_id]`.
- A wave may contain only tasks whose dependencies terminate successfully before that wave starts.
- A task appears in at most one planned wave.
- Tasks sharing a mutable path or exclusive resource cannot occupy the same wave.
- The graph must be acyclic and include every dispatched task.

Review and accept the complete graph before dispatch. Recompute it after a task becomes blocked, changes scope, or creates a new dependency.

## Experiment Contract

Use `assets/templates/experiment.json` for a controlled architecture experiment. Every experiment must define:

- a stable ID, owning task, revision, and one falsifiable hypothesis;
- independent, dependent, controlled, and nuisance variables;
- the pinned target snapshot, workloads, controls, and observables;
- seed and repetition policy;
- command plan and expected artifacts;
- acceptance, inconclusive, stop, and `resource_exhaustion_criteria`;
- a resource budget and exclusive resources;
- status.

Changing an independent variable within the declared matrix creates a new cell. Changing a controlled variable, target snapshot, instrumentation, or workload creates a new experiment revision and must remain comparable only when justified.

## Worker Prompt Envelope

Construct worker prompts in this order:

1. State the role and research question.
2. Provide exact inputs and scope.
3. List allowed and prohibited actions.
4. State evidence and output requirements.
5. State stop and escalation conditions.
6. Require artifact paths and a concise completion summary.

Do not include other workers' conclusions or manager preferences.

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
  "source_date": null,
  "sensitivity": "internal",
  "hash": null
}
```

Prefer primary artifacts: source code, configuration, logs, test output, standards, vendor advisories, and authoritative vulnerability records. Label secondary commentary as secondary.

For architecture research, use precise evidence kinds such as `rtl`, `config`, `build_log`, `simulation_log`, `difftest`, `assertion`, `counter`, `trace`, `waveform`, `checkpoint`, and `analysis`. Evidence derived from a generated artifact must reference its artifact ID.

## Artifact Manifest

Write one object per line to `artifacts/manifest.jsonl` using `assets/templates/artifact-record.json`. Each artifact records its producer, optional experiment, kind, relative path, hash, target snapshot, tool versions, workload IDs, seed, timestamp, sensitivity, and retention decision.

Do not cite a generated file that is absent from the manifest. Every manifest path must resolve inside the run directory and match its recorded hash. When a large raw artifact must remain in managed external storage, register a small in-run pointer record containing its stable external locator, external content hash, access conditions, and retention decision; cite the pointer artifact.

## Finding Contract

Every finding must contain:

- stable ID and concise title;
- affected scope and preconditions;
- security property, threat model, architectural state, microarchitectural state, and observation model when applicable;
- observation, interpretation, and impact as separate fields;
- evidence IDs;
- counter-evidence and false-positive hypotheses;
- counterfactual or control results for quantitative microarchitecture claims;
- severity and confidence with short rationales;
- verification status and verifier task ID;
- remediation and regression-check proposal;
- limitations and redactions.

Never mark a finding `verified` solely because multiple agents repeat the same claim.

For a `verified` finding, `verifier_task_id` must name a different task. High-impact architecture findings require an independent method or a documented reason why only corroboration is possible.
