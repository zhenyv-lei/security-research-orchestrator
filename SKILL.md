---
name: security-research-orchestrator
description: Orchestrate authorized defensive security and computer-architecture research by defining scope, decomposing work into independent evidence-bearing tasks and approved experiments, dispatching isolated worker agents, verifying findings, and preserving resumable state. Use for multi-agent source-code audits, CVE and supply-chain investigations, threat modeling, defensive microarchitecture or ISA studies, RTL and simulator reviews, false-positive verification, and long-running research that needs reproducible artifacts and a final evidence-backed report. Triggers include "安全研究编排", "微架构安全研究", "多 Agent 安全审计", "拆分安全研究", "security research orchestration", "coordinate security audit", and "resume security research".
---

# Security Research Orchestrator

Coordinate research; do not replace domain experts. Keep the manager responsible for authorization, task dependencies, state, composition risk, and final acceptance. Give each worker only the context and permissions required by its task contract.

## Load Resources

- Read [references/authorization-and-safety.md](references/authorization-and-safety.md) before any active testing, external interaction, or ambiguous dual-use work.
- Read [references/research-profiles.md](references/research-profiles.md) when selecting tasks for a code audit, CVE investigation, or threat model.
- Read [references/microarchitecture-research.md](references/microarchitecture-research.md) for ISA, RTL, simulator, processor-pipeline, cache, predictor, memory-system, FPGA, silicon, or side-channel research.
- Read [references/task-and-evidence-contracts.md](references/task-and-evidence-contracts.md) before dispatching workers or accepting their artifacts.
- Read [references/review-and-synthesis.md](references/review-and-synthesis.md) before verifying findings or assigning the synthesis agent.
- Read [references/recovery-and-resume.md](references/recovery-and-resume.md) when a run is interrupted, blocked, or resumed.
- Read [references/policy-aware-decomposition.md](references/policy-aware-decomposition.md) before creating worker tasks for dual-use, shared-state, vulnerability, or exploitation-adjacent research.
- Copy templates from `assets/templates/` into a run directory; never edit the bundled templates in place.

## Core Invariants

1. Decompose by independent research question, not by fragments of sensitive capability.
2. Treat authorization and combined output risk as run-wide constraints inherited by every task.
3. Separate discovery, verification, and synthesis roles. A worker cannot verify its own finding.
4. Require traceable evidence for every accepted claim. Agent confidence alone is not evidence.
5. Preserve partial progress. Continue unrelated safe tasks when one branch fails.
6. Never retry a safety refusal through another agent, euphemistic wording, encoding, or task fragmentation.
7. Report blocked and unverified areas explicitly; never let the synthesizer infer missing operational steps.
8. Treat task granularity as a quality and isolation control, never as a way to lower or bypass safety review.
9. Give a discovery worker one resource family, one answerable question, and one evidence goal. Keep operational testing in a separately approved task.
10. Pin commit, RTL configuration, toolchain, target class, workload, and seed policy before comparing microarchitectural results.
11. Separate architectural correctness, microarchitectural observation, security interpretation, and mitigation cost; evidence for one does not establish the others.

## Phase 0: Intake and Safety Gate

Collect these fields before decomposition:

- objective and research questions;
- authorized assets, repositories, versions, and environments;
- allowed and prohibited actions;
- active-testing approval, time window, and rate limits;
- sensitive-data handling and output audience;
- desired deliverable and completion criteria.
- for architecture research: ISA and privilege assumptions, design commit and configuration, simulator or hardware target, reference model, workload provenance, observables, and resource budget.

Classify the run using `references/authorization-and-safety.md`. If authorization is absent or ambiguous, restrict the run to passive public-source research, local artifact review, defensive threat modeling, and remediation analysis.

Review both individual task risk and composition risk. Reject a decomposition whose individually benign outputs would combine into a disallowed operational capability.

Classify the requested output and each proposed task using `references/policy-aware-decomposition.md`. Keep passive state inventory, boundary tracing, control review, active validation, and synthesis as distinct task classes. If active testing is not approved, exclude active actions from worker contracts rather than embedding them as optional steps.

**🔴 CHECKPOINT · 🛑 STOP — ACTIVE TESTING**

Before scanning, dynamic probing, proof-of-concept execution, credential use, or interaction with a non-local target, show the exact target, method, expected traffic or mutation, rollback plan, and authorization evidence. Wait for explicit user approval.

For `microarchitecture-security`, set `research_profile`, complete `scope.target_snapshot`, and preserve the general authorization packet in addition to the v3 active-testing packet. Static RTL inspection may remain `non_operational`; simulation, formal execution, FPGA, silicon, probing, or measurement is active work and requires approval.

Use integer schema `3` for every dispatchable run and task. Set exactly one supported profile: `source-code-security-audit`, `cve-supply-chain-investigation`, `threat-modeling-architecture-review`, or `microarchitecture-security`. Unknown versions and profiles fail closed. Every v3 run carries the common authorization packet, task graph, artifact roots, and resume state; profile selection never disables those gates.

Output: a completed `run-state.json` with scope, authorization tier, constraints, approval status, and any required target snapshot.

## Phase 1: Build the Research Task Graph

Select a profile from `references/research-profiles.md`, then create tasks with the schema in `references/task-and-evidence-contracts.md`.

Start with one `context_map` task. Do not dispatch component discovery until it establishes the effective implementation, configuration, trust boundaries, and stable resource ownership.

For every task:

1. State one answerable research question.
2. Define inputs, allowed actions, prohibited actions, and expected artifacts.
3. Define acceptance criteria and evidence requirements.
4. List task dependencies and files the worker may modify.
5. Assign a role: context, discovery, analysis, verification, mitigation, or synthesis.
6. Add stop and escalation conditions.
7. Complete the structured `safety` block: defensive purpose, task class, capability boundary, resource scope, evidence goal, active actions, composition dependencies, and safe fallback.

For a microarchitecture profile, also complete `phase`, `execution_mode`, `target_snapshot`, and `resource_requirements`. Make the task snapshot match the run snapshot. If a task will execute or measure a target, classify it as `active_validation`, bind it to the approval packet, and create at least one `experiments/<experiment-id>/experiment.json` with one falsifiable hypothesis, controls, variables, explicit variable-assignment cells, workloads, seeds/repetitions, observables, stop criteria, and a resource budget bounded by the task reservation.

Apply the bounded-task test before dispatch:

- one resource family or trust boundary for discovery/analysis;
- one research question ending in a testable evidence claim;
- one primary artifact set and one owned task directory;
- no combined request to inventory state, construct a method, validate it, and judge impact;
- no active action inside a `non_operational` task.

Use separate follow-on tasks when a result creates a new question. A state inventory may feed a boundary verifier or mitigation review; it must not silently expand into operational validation.

Dispatch tasks in parallel only when they have no unresolved dependency, shared mutable file, exclusive resource, or overlapping ownership. Otherwise execute them sequentially. Reserve the manager for coordination; run workers in bounded waves that fit the available concurrency.

Run the deterministic preflight before dispatch:

```bash
python3 scripts/preflight_tasks.py /absolute/path/to/run --strict-v3
```

Preflight always requires schema v3, even when the flag is omitted. Use `validate_run.py` only to read legacy v1/v2 archives; migrate before dispatch. Fix errors before starting workers. Treat warnings as manager review items and record accepted exceptions in `run-state.json`.

**🔴 CHECKPOINT · 🛑 STOP — TASK GRAPH**

For active testing, FPGA/silicon access, sensitive private artifacts, or material composition risk, show the dependency graph, runnable waves, exclusive resources, target snapshot, authorization inheritance, and combined-output review. Wait for explicit approval before dispatching the first worker.

Output: `tasks/<task-id>/task.json` files, an updated dependency graph in `run-state.json`, optional approved experiment contracts, and a passing preflight.

## Phase 2: Dispatch Isolated Workers

Start a fresh worker for each independent task. Construct its context from the task contract and named source artifacts; do not pass the full manager conversation or other workers' conclusions.

Build the worker prompt directly from the task contract in this order: defensive purpose and capability boundary, one research question, exact inputs, allowed/prohibited actions, evidence/output requirements, then stop conditions. Use literal terminology; never disguise a blocked objective. If the prompt still bundles multiple task classes, return it to Phase 1 instead of dispatching it.

Require each worker to:

- remain inside scope and permissions;
- write only inside its assigned task directory;
- distinguish observations, sourced facts, hypotheses, and conclusions;
- record evidence locators and reproducible defensive checks;
- redact secrets and personal data;
- declare unknowns, conflicts, and incomplete work;
- return a concise completion summary plus artifact paths.
- for approved architecture experiments, record exact commands, tool versions, target snapshot, seeds, exit status, and hashes for generated artifacts.

Do not let workers hand off tasks directly. Route all new work proposals through the manager so authorization, dependencies, and composition risk remain centralized.

Write each generated experiment artifact under its owning `experiments/<experiment-id>/results/` directory and register it in `artifacts/manifest.jsonl`. Bind the record to the experiment revision, canonical contract hash, cell ID, seed, and repetition index. Do not place generated output beside design inputs or shared workloads.

Output: task reports, `evidence.jsonl`, candidate `finding-*.json` files, experiment results and manifest records when approved, and updated task status.

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

For microarchitecture findings, require a counterfactual or control configuration when feasible. A waveform screenshot or performance delta is not by itself a security finding: connect stimulus, state transition, squash or commit behavior, observable, threat model, and confounder checks. Quantitative claims require repeated trials or a justified deterministic design.

Output: normalized findings, verification verdicts, conflict records, and evidence index.

## Phase 4: Assign a Fresh Synthesis Agent

Wait for all runnable discovery and verification tasks to reach a terminal state. Start one fresh synthesis agent and provide only:

- the approved scope and completion criteria;
- normalized findings and verdicts;
- the evidence index;
- the pinned design snapshot, experiment matrix, artifact manifest, and reproducibility status when present;
- unresolved conflicts, blocked tasks, and coverage gaps;
- the final-report template and synthesis rules.

Do not provide hidden expected conclusions or ask the synthesizer to fill gaps. Require it to deduplicate findings, preserve evidence provenance, calibrate language to verdict strength, separate facts from inferences, and include limitations.

Run a final composition-risk review before accepting the synthesis. Remove secrets and unnecessary operational detail while preserving defensive value.

Output: a substantive `final/final-report.md` and claim-to-evidence coverage table. A completed v3 run also requires an exact `evidence-index.json`, one completed `synthesis` task that owns the final report, and a non-empty resume checkpoint.

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
| Safety or policy refusal | Mark `policy_blocked`, append `policy-events.jsonl`, preserve visible failure artifacts, and do not retry | Create a materially safer defensive task with `fallback_of`, or request human review |
| Subagents unavailable | Execute the same task contracts sequentially | Mark evaluation as non-independent |
| Validation script fails | Fix schema or artifact paths, then rerun | Do not synthesize invalid artifacts |
| Build, simulation, or hardware resource exhaustion | Preserve logs, command, snapshot, and checkpoint; retry only within the recorded budget | Create a new experiment revision for changed workloads, seeds, instrumentation, or configuration |
| Reference-model, assertion, or waveform mismatch | Preserve both artifacts and assign independent triage | Do not classify the mismatch as a security finding without a threat-model link |

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
- use an unknown profile or cosmetic fallback wording to bypass a stricter contract;
- place dynamic intent only in objectives, research questions, or translated action text while declaring the task non-operational;
- compare results from different commits, RTL configurations, toolchains, workloads, or seeds as one controlled experiment;
- infer leakage or exploitability from timing or counter variance without controls, repetitions, and an explicit observation model.

## Run Layout

```text
<run-dir>/
├── run-state.json
├── policy-events.jsonl
├── blocked-worker-log.md
├── experiments/
│   └── EXP-001/
│       ├── experiment.json
│       └── results/
├── artifacts/
│   └── manifest.jsonl
├── tasks/
│   └── SR-001/
│       ├── task.json
│       ├── report.md
│       ├── evidence.jsonl
│       └── finding-001.json
├── conflicts.json
├── evidence-index.json
└── final/
    └── final-report.md
```
