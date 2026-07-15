---
name: security-research-orchestrator
description: Orchestrate authorized defensive security and computer-architecture research by pinning a reproducible design snapshot, decomposing work into independent evidence-bearing tasks and experiments, dispatching isolated worker agents, verifying findings, recovering from technical interruptions, and assigning a fresh synthesis agent. Use for microarchitecture or ISA security studies, RTL and simulator reviews, transient-execution or side-channel analysis in controlled environments, source-code audits, CVE investigations, threat modeling, false-positive verification, and long-running research that needs checkpoints and an evidence-backed report. Triggers include "微架构安全研究", "体系结构安全研究", "安全研究编排", "多 Agent 安全审计", "security research orchestration", and "resume security research".
---

# Security Research Orchestrator

Coordinate research; do not replace domain experts. Keep the manager responsible for authorization, task dependencies, state, composition risk, and final acceptance. Give each worker only the context and permissions required by its task contract.

## Load Resources

- Read [references/authorization-and-safety.md](references/authorization-and-safety.md) before any active testing, external interaction, or ambiguous dual-use work.
- Read [references/research-profiles.md](references/research-profiles.md) when selecting tasks for a code audit, CVE investigation, or threat model.
- Read [references/microarchitecture-research.md](references/microarchitecture-research.md) for ISA, RTL, simulator, processor-pipeline, cache, predictor, memory-system, transient-execution, or side-channel research.
- Read [references/task-and-evidence-contracts.md](references/task-and-evidence-contracts.md) before dispatching workers or accepting their artifacts.
- Read [references/review-and-synthesis.md](references/review-and-synthesis.md) before verifying findings or assigning the synthesis agent.
- Read [references/recovery-and-resume.md](references/recovery-and-resume.md) when a run is interrupted, blocked, or resumed.
- Copy templates from `assets/templates/` into a run directory; never edit the bundled templates in place.

## Core Invariants

1. Decompose by independent research question, not by fragments of sensitive capability.
2. Treat authorization and combined output risk as run-wide constraints inherited by every task.
3. Separate discovery, verification, and synthesis roles. A worker cannot verify its own finding.
4. Require traceable evidence for every accepted claim. Agent confidence alone is not evidence.
5. Preserve partial progress. Continue unrelated safe tasks when one branch fails.
6. Never retry a safety refusal through another agent, euphemistic wording, encoding, or task fragmentation.
7. Report blocked and unverified areas explicitly; never let the synthesizer infer missing operational steps.
8. Pin the repository commit, RTL/configuration, toolchain, workload, seed policy, and target class before comparing microarchitectural results.
9. Separate architectural correctness, microarchitectural behavior, security interpretation, and performance cost; evidence for one does not establish the others.

## Phase 0: Intake and Safety Gate

Collect these fields before decomposition:

- objective and research questions;
- authorized assets, repositories, versions, and environments;
- allowed and prohibited actions;
- active-testing approval, time window, and rate limits;
- sensitive-data handling and output audience;
- desired deliverable and completion criteria.
- for architecture research: ISA/privilege assumptions, design commit and configuration, simulator or hardware target, reference model, workload provenance, observables, and resource budget.

Classify the run using `references/authorization-and-safety.md`. If authorization is absent or ambiguous, restrict the run to passive public-source research, local artifact review, defensive threat modeling, and remediation analysis.

Review both individual task risk and composition risk. Reject a decomposition whose individually benign outputs would combine into a disallowed operational capability.

**🔴 CHECKPOINT · 🛑 STOP — ACTIVE TESTING**

Before scanning, dynamic probing, proof-of-concept execution, credential use, or interaction with a non-local target, show the exact target, method, expected traffic or mutation, rollback plan, and authorization evidence. Wait for explicit user approval.

Output: a completed `run-state.json` with scope, authorization tier, research profile, pinned target snapshot, constraints, task graph, artifact roots, and approval status.

## Phase 1: Build the Research Task Graph

Select a profile from `references/research-profiles.md`, then create tasks with the schema in `references/task-and-evidence-contracts.md`.

For every task:

1. State one answerable research question.
2. Define inputs, allowed actions, prohibited actions, and expected artifacts.
3. Define acceptance criteria and evidence requirements.
4. List task dependencies and files the worker may modify.
5. Assign a role: context, discovery, analysis, verification, mitigation, or synthesis.
6. Add stop and escalation conditions.
7. For experiments, name the hypothesis, variables, controls, repetitions, seed policy, observables, and resource budget in `experiments/<experiment-id>/experiment.json`.

Dispatch tasks in parallel only when they have no unresolved dependency, shared mutable file, exclusive resource, or overlapping ownership. Otherwise execute them sequentially. Reserve the manager for coordination; run workers in bounded waves that fit the available concurrency.

Before dispatch, review the graph as a whole: confirm every dependency edge, exclusive resource, shared artifact, and synthesis prerequisite. Record runnable waves in `run-state.json`; do not rely on conversational memory.

**🟡 CHECKPOINT · 🛑 STOP — TASK GRAPH**

For runs involving active testing, FPGA or silicon access, sensitive private artifacts, or material composition risk, show the task graph, runnable waves, exclusive resources, authorization inheritance, and combined-output review. Wait for explicit user approval before the first worker is dispatched.

Output: `tasks/<task-id>/task.json`, optional `experiments/<experiment-id>/experiment.json`, and a validated dependency graph in `run-state.json`.

## Phase 2: Dispatch Isolated Workers

Start a fresh worker for each independent task. Construct its context from the task contract and named source artifacts; do not pass the full manager conversation or other workers' conclusions.

Require each worker to:

- remain inside scope and permissions;
- write only inside its assigned task directory;
- distinguish observations, sourced facts, hypotheses, and conclusions;
- record evidence locators and reproducible defensive checks;
- redact secrets and personal data;
- declare unknowns, conflicts, and incomplete work;
- return a concise completion summary plus artifact paths.
- preserve exact commands, tool versions, target snapshot, seeds, exit status, and hashes for generated architecture-research artifacts.

Do not let workers hand off tasks directly. Route all new work proposals through the manager so authorization, dependencies, and composition risk remain centralized.

Output: task reports, `evidence.jsonl`, candidate `finding-*.json` files, experiment results, `artifacts/manifest.jsonl`, and updated task status.

## Phase 3: Normalize and Verify Findings

Validate run artifacts with:

```bash
python3 scripts/validate_run.py /absolute/path/to/run
```

Return malformed or unsupported findings to the originating task. Then assign a fresh verification worker for each material finding or coherent finding cluster.

Require the verifier to test the claim independently against the cited artifact, check preconditions and environmental protections, search for false-positive explanations, and issue one verdict:

- `verified` — evidence establishes the claim within stated scope;
- `corroborated` — multiple sources support the claim but a required test is unavailable;
- `candidate` — plausible but insufficiently supported;
- `rejected` — contradicted, unreachable, or based on invalid assumptions;
- `blocked` — verification requires missing authorization, input, or capability.

When two reports conflict, dispatch an independent verifier with both evidence sets but without either worker's confidence score. Preserve unresolved disagreement in the final report.

For microarchitecture findings, require a counterfactual or control configuration when feasible. Check whether the evidence establishes an architectural violation, a microarchitectural observation, or only a correlation. Prefer differential testing against a reference model for functional claims and repeated seeded trials with noise accounting for quantitative claims.

Output: normalized findings, verification verdicts, conflict records, and evidence index.

## Phase 4: Assign a Fresh Synthesis Agent

Wait for all runnable discovery and verification tasks to reach a terminal state. Start a fresh synthesis agent and provide only:

- the approved scope and completion criteria;
- normalized findings and verdicts;
- the evidence index;
- the pinned design snapshot, experiment matrix, artifact manifest, and reproducibility status;
- unresolved conflicts, blocked tasks, and coverage gaps;
- the final-report template and synthesis rules.

Do not provide hidden expected conclusions or ask the synthesizer to fill gaps. Require it to deduplicate findings, preserve evidence provenance, calibrate language to verdict strength, separate facts from inferences, and include limitations.

Run a final composition-risk review before accepting the synthesis. Remove secrets and unnecessary operational detail while preserving defensive value.

Output: `final/final-report.md` and a claim-to-evidence coverage table.

## Phase 5: Manager Acceptance

Accept the run only when:

- every task has a valid terminal status;
- every accepted claim maps to evidence and a verdict;
- every quantitative result maps to a pinned configuration, workload, seed/repetition policy, raw artifact, and analysis method;
- high-impact findings received independent verification;
- blocked work and uncertainty are visible;
- the combined report remains within authorization and safety boundaries;
- deterministic validation passes.

If a condition fails, reopen only the affected task. Do not restart completed independent work.

**🔴 CHECKPOINT · 🛑 STOP — FINAL RELEASE**

For reports containing sensitive vulnerabilities, private code, personal data, or operational testing details, show the intended audience, redaction decision, and remaining limitations. Wait for user approval before external publication or transmission.

## Failure and Recovery Matrix

| Trigger | First response | If unresolved |
|---|---|---|
| Transient API or tool error | Checkpoint artifacts and retry the identical task, maximum 2 attempts | Mark `blocked_technical`; continue independent tasks |
| Worker timeout or crash | Restart from its task contract and saved artifacts | Narrow the task without changing its objective; then mark incomplete |
| Context limit | Persist summary, evidence index, and next action | Resume with source artifacts, not conversational memory |
| Missing input or authorization | Mark `needs_input` and identify the exact missing item | Pause only dependent tasks |
| Insufficient evidence | Return the finding for one bounded evidence pass | Keep it `candidate` or `blocked` |
| Conflicting findings | Assign a fresh independent verifier | Preserve both positions and uncertainty |
| Safety or policy refusal | Mark `policy_blocked`; do not automatically retry | Create a materially safer defensive task or request human review |
| Subagents unavailable | Execute the same task contracts sequentially | Mark evaluation as non-independent |
| Validation script fails | Fix schema or artifact paths, then rerun | Do not synthesize invalid artifacts |
| Build/simulation resource exhaustion | Preserve logs, command, target snapshot, and last checkpoint; reduce only the resource plan | Do not silently change the research question or configuration |
| Reference-model or waveform mismatch | Preserve both artifacts and assign an independent triage task | Do not classify the mismatch as a security finding without a threat-model link |

## Anti-Patterns and Blacklist

Do not:

- dispatch broad tasks such as "audit everything" without acceptance criteria;
- parallelize tasks that edit the same files or depend on one another;
- expose all context and tools to every worker;
- treat agreement between agents as evidence;
- let a discovery worker self-verify or write the final verdict;
- accept a finding that lacks an evidence locator and scope statement;
- ask another agent to retry, rephrase, encode, or fragment a safety-blocked task;
- split a restricted capability into benign-looking pieces and recombine it;
- run downloaded proof-of-concept code without explicit authorization and isolation;
- include credentials, secrets, personal data, persistence, stealth, or destructive actions in outputs;
- let the synthesis agent invent missing evidence or hide incomplete coverage;
- claim completion because workers reported success without checking artifacts.
- compare results from different commits, RTL configs, toolchains, workloads, or seeds as if they were one controlled experiment;
- infer information leakage from performance variance without controls, repetitions, and a stated observation model;

## Run Layout

```text
<run-dir>/
├── run-state.json
├── experiments/
│   └── EXP-001/
│       ├── experiment.json
│       └── results/
├── tasks/
│   └── SR-001/
│       ├── task.json
│       ├── report.md
│       ├── evidence.jsonl
│       └── finding-001.json
├── artifacts/
│   └── manifest.jsonl
├── conflicts.json
├── evidence-index.json
└── final/
    └── final-report.md
```
