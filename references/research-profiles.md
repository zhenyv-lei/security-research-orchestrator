# Research Profiles

Select the smallest profile that satisfies the research goal. Add tasks only when they answer a distinct question.

## Source-Code Security Audit

Set `research_profile` to `source-code-security-audit`.

1. `context_map`: map architecture, trust boundaries, entry points, critical assets, and build/test paths.
2. `passive_research`: identify security-relevant changes when version history is available.
3. `state_inventory`: partition review by one independent component or vulnerability class per task.
4. `state_inventory`: inspect each assigned cluster without editing shared artifacts.
5. `evidence_normalization`: convert candidate issues into the common finding schema.
6. `verification`: independently trace reachability, control, protections, and assumptions.
7. `mitigation`: verify proposed fixes and regression checks.
8. `synthesis`: combine only normalized, verdict-bearing findings.

Do not parallelize before `context_map` identifies stable component boundaries.

## CVE and Supply-Chain Investigation

Set `research_profile` to `cve-supply-chain-investigation`.

1. `state_inventory`: record product, package, version, platform, configuration, and dependency path.
2. `passive_research`: collect primary vendor advisories and authoritative vulnerability records.
3. `passive_research`: compare affected and fixed version constraints.
4. `boundary_trace`: determine whether vulnerable code or configuration is present and reachable.
5. `control_review`: identify compensating controls and deployment-specific blockers.
6. `verification`: independently confirm applicability and evidence quality.
7. `mitigation`: prioritize upgrade, configuration, detection, and temporary mitigation.
8. `synthesis`: distinguish theoretical exposure from verified applicability.

## Threat Modeling and Architecture Review

Set `research_profile` to `threat-modeling-architecture-review`.

1. `context_map`: document assets, actors, data flows, trust boundaries, and dependencies.
2. `passive_research`: enumerate security assumptions and missing architecture evidence.
3. `state_inventory`: assign one independent trust boundary or abuse case per worker.
4. `control_review`: map preventive, detective, and recovery controls.
5. `verification`: validate realistic preconditions without operationalizing attacks.
6. `risk_ranking`: score impact, likelihood, uncertainty, and control strength.
7. `mitigation`: propose testable changes and owners.
8. `synthesis`: include residual risk and unmodeled areas.

## Shared-State and Microarchitecture Review

Use this defensive profile for hardware predictors, caches, queues, allocators, schedulers, runtime caches, or other state shared across tenants or contexts.

For RTL, simulator, FPGA, silicon, timing, or quantitative work, also load `microarchitecture-research.md`, set `research_profile` to `microarchitecture-security`, and pin the target snapshot before component tasks are dispatched.

1. `context_map`: identify the effective commit/configuration, instance count, ownership, context boundary, reset/flush events, target class, tools, and workloads.
2. `state_inventory`: assign one worker per independent resource family; record storage, lifecycle, identity inputs, pending updates, and replacement/adaptive state.
3. `boundary_trace`: trace context, privilege, tenant, ASID/VMID, epoch, fence, reset, and invalidate signals from producer to every state owner.
4. `control_review`: map partitioning, tagging, flushing, draining, save/restore, and observability controls.
5. `verification`: independently test persistence and isolation claims against source and configuration counterexamples.
6. `mitigation`: cover main entries plus history, replacement, thresholds, region metadata, and pending writes; define regression properties.
7. `active_validation`: create only after an explicit approval packet; bind every calibration or experiment contract to that task and preserve controls, seeds, resource budget, raw artifacts, and hashes.
8. `evidence_normalization`: link raw artifacts to sourced observations and keep architectural, microarchitectural, security, and performance claims distinct.
9. `synthesis`: report state facts, verified isolation gaps, reproducibility status, blocked validation, and mitigations without reconstructing unavailable operational steps.

Do not assign a worker a combined request such as "map the resource, derive a collision, build a probe, and rank exploitability." Those are different task classes and may not all be authorized or necessary.

## Routing Rules

Schema v3 accepts only the four profile identifiers above. Do not invent aliases or use a generic/empty value; select the closest bounded profile and record out-of-profile questions as limitations.

- Use one worker when the question requires full-system context or shared mutable state.
- Use parallel workers for independent components, advisory sources, or trust boundaries.
- Use a separate verifier for high-impact or ambiguous findings.
- Use a fresh synthesizer after evidence normalization; never use it for discovery.
