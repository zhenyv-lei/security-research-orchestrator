# Microarchitecture and Architecture Research

Use this reference for processor, ISA, RTL, simulator, cache, predictor, memory-system, FPGA, silicon, transient-execution, and side-channel studies. Set `research_profile` to `microarchitecture-security`; keep the schema v3 authorization, task safety, evidence, verification, and recovery rules in force.

Static source mapping and state-lifecycle review may use `non_operational` tasks. Simulation, formal execution, FPGA/silicon access, probing, target mutation, or measurement must use a separately approved `active_validation` task. Never use an experiment contract to bypass the active-testing checkpoint.

Use `read-only` or `passive-research` for non-operational work, `local-simulation` or `formal-execution` for A1/A2 lab execution, and `fpga` or `silicon` only with A2. The execution mode must agree with `target_snapshot.target_class`.

## Layered Research Layout

Model the run as five layers. This mirrors a processor project that separates design sources, agile tooling, reference validation, ready workloads, and generated results.

1. **Design snapshot** — repository, commit, submodules, RTL generator/configuration, ISA and privilege assumptions.
2. **Research tooling** — build scripts, simulator, instrumentation, analysis scripts, and their versions.
3. **Reference validation** — ISA model, differential testing, assertions, formal harnesses, or trusted baselines.
4. **Workloads and stimuli** — binaries, checkpoints, traces, generators, seeds, provenance, and hashes.
5. **Artifacts and conclusions** — logs, counters, waveforms, traces, statistical summaries, evidence records, findings, and report.

Never let generated artifacts overwrite design inputs or bundled workloads. Workers may read shared inputs, but each task writes to its own task or experiment result directory.

## Target Snapshot

Pin these fields in `scope.target_snapshot` before component tasks are dispatched:

- repository path and commit; record dirty state and submodule commits;
- RTL generator and configuration name or parameter set;
- ISA extensions, privilege model, core count, cache/memory hierarchy, and relevant security controls;
- target class: static RTL, formal model, cycle simulator, FPGA, or silicon;
- compiler, simulator, reference model, and analysis-tool versions;
- workload or checkpoint path, provenance, hash, and expected completion signal;
- clock/reset assumptions, random seed policy, repetition count, and resource limits.

Copy the snapshot identity into every microarchitecture task, experiment, and artifact record. The validator rejects cross-layer drift. If any comparison changes more than its declared independent variables, create a new experiment revision or mark the result confounded.

## Pipeline

### 1. Research Frame

Define the security property, threat model, attacker-controlled inputs, observable outputs, secrets or protected state, and explicit non-goals. Distinguish:

- architectural state and ISA-visible correctness;
- microarchitectural state and timing/resource behavior;
- a security-relevant channel or invariant;
- performance, power, and area effects of a mitigation.

### 2. Design and Tool Mapping

Map the relevant pipeline stages, queues, predictors, caches, translation structures, coherence paths, privilege transitions, speculation boundaries, flush behavior, and counters. Locate existing assertions, difftest hooks, debug probes, and performance events before requesting new instrumentation.

### 3. Approval and Experiment Matrix

Before writing executable commands or dispatching measurement, bind the owning task and experiment to the same `active_testing_approval.approval_id`. The task must appear in `approved_task_ids`, use `active_validation` plus `active_authorized`, and declare its active actions.

For each experiment, record:

- one falsifiable hypothesis;
- independent, dependent, controlled, and nuisance variables;
- baseline and counterfactual configurations;
- stimulus/workload and seed/repetition policy;
- observables such as commits, exceptions, counters, traces, waveforms, latency distributions, or difftest events;
- pass, fail, inconclusive, stop, and resource-exhaustion criteria.

Use `assets/templates/experiment.json` to declare the matrix. Name independent variables with stable identifiers, give every assignment a unique `CELL-*` record using exactly those keys and non-null scalar values, then realize the cell x workload x seed x repetition cross-product. Parallelize cells only when they do not share an exclusive simulator build, mutable checkpoint, FPGA image, hardware target, or output path. Keep each cell within one approved method class, and keep every experiment CPU, memory, wall-time, storage, and exclusive-resource budget within the owning task's reservation and graph resources.

### 4. Build and Calibration Gate

After approval and before a measurement wave:

1. reproduce the pinned build;
2. record exact commands, versions, and exit codes;
3. run a smoke workload and reference-model check;
4. verify counters/probes change as expected;
5. estimate runtime, storage, and variance on a small sample.

Do not interpret security results from an uncalibrated build or a failing reference check.

### 5. Evidence Collection

Prefer the smallest artifact that establishes the claim while retaining raw data needed for independent review. Write artifacts under `experiments/<experiment-id>/results/`. Register each one in `artifacts/manifest.jsonl` with its producer, experiment revision and canonical contract hash, cell, seed, repetition, target snapshot, tool version, path, SHA-256 hash, sensitivity, and retention decision.

Typical evidence kinds include `source_code`, `configuration`, `build_log`, `simulation_log`, `formal_log`, `difftest`, `counter`, `trace`, `waveform`, `checkpoint`, `analysis`, `report`, and `standard`.

### 6. Independent Verification

Use a fresh verifier and, where feasible, a distinct method:

- functional mismatch: reproduce and compare with a reference model or assertion;
- timing/channel claim: repeat trials, include negative controls, quantify variance, and check confounders;
- transient-state claim: connect stimulus, speculative state, squash/commit behavior, and the stated observable;
- mitigation claim: confirm the security property and check functional plus performance regressions.

A waveform screenshot alone is illustrative, not sufficient evidence. A statistical difference alone is not a security finding until tied to attacker control, protected state, and a reproducible observation model.

## Suggested Task Graph

Use only the nodes needed for the question:

1. `context_map` → threat model, property, effective configuration, design snapshot, and observability.
2. `state_inventory` → one component or resource family and its lifecycle.
3. `boundary_trace` or `control_review` → one identity/flush boundary or protection objective.
4. `active_validation` → one approved calibration or experiment cell with isolated results.
5. `evidence_normalization` → common units, exclusions, and raw-to-derived provenance.
6. `verification` → counterfactual, repeat, reference, or alternate method.
7. `mitigation` → security, functional, and performance regression checks.
8. `synthesis` → evidence-backed conclusions, limitations, and reproducibility packet.

Do not dispatch `active_validation` before the target snapshot, approval packet, task graph, and deterministic preflight are accepted.

## Architecture-Specific Finding Questions

Before accepting a finding, answer:

- Which architectural or microarchitectural state is involved?
- What input or scheduling influence does the threat actor control?
- What protected state affects the observation?
- What exact observation is available, at what privilege and granularity?
- Does the effect survive controls, repetition, and an independent method?
- Is the result functional, security-relevant, performance-only, or inconclusive?
- Which commit, config, target, toolchain, workload, and seed produced it?
- What mitigation invariant and regression checks would falsify the proposed fix?

## Resource and Recovery Rules

- Treat simulator builds, FPGA boards, licensed tools, large-memory nodes, and shared checkpoints as exclusive resources when applicable.
- Checkpoint after build, calibration, each experiment cell, and analysis normalization.
- On timeout or resource exhaustion, retry the identical experiment within its budget. A smaller workload, changed seed count, altered instrumentation, or different config is a new recorded experiment revision.
- Preserve partial logs and artifact hashes. Never label a truncated run as a completed negative result.
- A policy-blocked experiment is not retryable. Replace it only with a materially safer defensive or local-toy objective and keep the coverage gap visible.
- If a command, workload, seed count, instrumentation point, target configuration, or resource budget changes, increment the experiment revision and re-run validation.

Run both gates before dispatch and again before synthesis:

```bash
python3 scripts/preflight_tasks.py /absolute/path/to/run --strict-v3
python3 scripts/validate_run.py /absolute/path/to/run
```
