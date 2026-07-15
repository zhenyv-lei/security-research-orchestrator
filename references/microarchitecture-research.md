# Microarchitecture and Architecture Research

Use this reference for processor, ISA, RTL, simulator, cache, predictor, memory-system, transient-execution, and side-channel studies. Keep the generic authorization, task, evidence, verification, and recovery rules in force.

## Layered Research Layout

Model the run as five layers. This mirrors a processor project that separates design sources, agile tooling, reference validation, ready workloads, and generated results.

1. **Design snapshot** — repository, commit, submodules, RTL generator/configuration, ISA and privilege assumptions.
2. **Research tooling** — build scripts, simulator, instrumentation, analysis scripts, and their versions.
3. **Reference validation** — ISA model, differential testing, assertions, formal harnesses, or trusted baselines.
4. **Workloads and stimuli** — binaries, checkpoints, traces, generators, seeds, provenance, and hashes.
5. **Artifacts and conclusions** — logs, counters, waveforms, traces, statistical summaries, evidence records, findings, and report.

Never let generated artifacts overwrite design inputs or bundled workloads. Workers may read shared inputs, but each task writes to its own task or experiment result directory.

## Target Snapshot

Pin these fields before an experiment becomes runnable:

- repository path and commit; record dirty state and submodule commits;
- RTL generator and configuration name or parameter set;
- ISA extensions, privilege model, core count, cache/memory hierarchy, and relevant security controls;
- target class: static RTL, formal model, cycle simulator, FPGA, or silicon;
- compiler, simulator, reference model, and analysis-tool versions;
- workload or checkpoint path, provenance, hash, and expected completion signal;
- clock/reset assumptions, random seed policy, repetition count, and resource limits.

If any comparison changes more than its declared independent variables, treat it as a new experiment or mark the result confounded.

## Pipeline

### 1. Research Frame

Define the security property, threat model, attacker-controlled inputs, observable outputs, secrets or protected state, and explicit non-goals. Distinguish:

- architectural state and ISA-visible correctness;
- microarchitectural state and timing/resource behavior;
- a security-relevant channel or invariant;
- performance, power, and area effects of a mitigation.

### 2. Design and Tool Mapping

Map the relevant pipeline stages, queues, predictors, caches, translation structures, coherence paths, privilege transitions, speculation boundaries, flush behavior, and counters. Locate existing assertions, difftest hooks, debug probes, and performance events before requesting new instrumentation.

### 3. Hypothesis and Experiment Matrix

For each experiment, record:

- one falsifiable hypothesis;
- independent, dependent, controlled, and nuisance variables;
- baseline and counterfactual configurations;
- stimulus/workload and seed/repetition policy;
- observables such as commits, exceptions, counters, traces, waveforms, latency distributions, or difftest events;
- pass, fail, inconclusive, stop, and resource-exhaustion criteria.

Use an experiment matrix rather than broad prompts. Parallelize cells only when they do not share an exclusive simulator build, mutable checkpoint, FPGA image, or output path.

### 4. Build and Calibration Gate

Before a measurement wave:

1. reproduce the pinned build;
2. record exact commands, versions, and exit codes;
3. run a smoke workload and reference-model check;
4. verify counters/probes change as expected;
5. estimate runtime, storage, and variance on a small sample.

Do not interpret security results from an uncalibrated build or a failing reference check.

### 5. Evidence Collection

Prefer the smallest artifact that establishes the claim while retaining raw data needed for independent review. Register each artifact in `artifacts/manifest.jsonl` with its producer, target snapshot, tool version, path, hash, sensitivity, and retention decision.

Typical evidence kinds include `rtl`, `config`, `build_log`, `simulation_log`, `difftest`, `assertion`, `counter`, `trace`, `waveform`, `checkpoint`, `analysis`, and `paper`.

### 6. Independent Verification

Use a fresh verifier and, where feasible, a distinct method:

- functional mismatch: reproduce and compare with a reference model or assertion;
- timing/channel claim: repeat trials, include negative controls, quantify variance, and check confounders;
- transient-state claim: connect stimulus, speculative state, squash/commit behavior, and the stated observable;
- mitigation claim: confirm the security property and check functional plus performance regressions.

A waveform screenshot alone is illustrative, not sufficient evidence. A statistical difference alone is not a security finding until tied to attacker control, protected state, and a reproducible observation model.

## Suggested Task Graph

Use only the nodes needed for the question:

1. `research-frame` → threat model, property, scope, completion criteria.
2. `design-snapshot` → commits, configuration, target, tools, workloads.
3. `architecture-map` → affected components and existing observability.
4. `hypothesis-design` → falsifiable hypotheses and experiment matrix.
5. `build-calibration` → reproducible build, smoke check, variance/resource estimate.
6. `experiment-*` → independent matrix cells with isolated results.
7. `analysis-normalization` → common units, exclusions, raw-to-derived provenance.
8. `independent-verification` → counterfactual, repeat, reference, or alternate method.
9. `mitigation-evaluation` → security, functional, and performance regression checks.
10. `synthesis` → evidence-backed conclusions, limitations, and reproducibility packet.

Do not parallelize `experiment-*` before the target snapshot and calibration gate are accepted.

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
