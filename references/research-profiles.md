# Research Profiles

Select the smallest profile that satisfies the research goal. Add tasks only when they answer a distinct question.

## Microarchitecture and ISA Security Research

Use `references/microarchitecture-research.md` as the detailed playbook.

1. `research-frame`: define the security property, threat model, architectural assumptions, and non-goals.
2. `design-snapshot`: pin commits, submodules, RTL/configuration, target class, toolchain, reference model, workloads, and resource limits.
3. `architecture-map`: map relevant structures, speculation/flush boundaries, privilege transitions, observables, and existing validation hooks.
4. `hypothesis-design`: create falsifiable hypotheses and a controlled experiment matrix.
5. `build-calibration`: reproduce the build, run smoke and reference checks, and estimate variance/resources.
6. `experiment-workers`: execute independent matrix cells into isolated result directories.
7. `analysis-normalization`: preserve raw-to-derived provenance and normalize units, exclusions, and confounders.
8. `independent-verification`: repeat with counterfactuals, a reference model, or an alternate method.
9. `mitigation-evaluation`: check security, functional, and performance regressions.
10. `synthesis`: report the pinned snapshot, experiment coverage, verdicts, and reproducibility limits.

Do not dispatch experiment workers until `design-snapshot`, `hypothesis-design`, and `build-calibration` are accepted.

## Source-Code Security Audit

1. `context-map`: map architecture, trust boundaries, entry points, critical assets, and build/test paths.
2. `change-history`: identify security-relevant changes when version history is available.
3. `surface-clusters`: partition review by independent component or vulnerability class.
4. `discovery-workers`: inspect assigned clusters without editing shared artifacts.
5. `finding-normalization`: convert candidate issues into the common finding schema.
6. `false-positive-check`: independently trace reachability, control, protections, and assumptions.
7. `mitigation-review`: verify proposed fixes and regression checks.
8. `synthesis`: combine only normalized, verdict-bearing findings.

Do not parallelize before `context-map` identifies stable component boundaries.

## CVE and Supply-Chain Investigation

1. `inventory`: record product, package, version, platform, configuration, and dependency path.
2. `advisory-research`: collect primary vendor advisories and authoritative vulnerability records.
3. `version-analysis`: compare affected and fixed version constraints.
4. `reachability`: determine whether vulnerable code or configuration is present and reachable.
5. `environment-controls`: identify compensating controls and deployment-specific blockers.
6. `verification`: independently confirm applicability and evidence quality.
7. `remediation`: prioritize upgrade, configuration, detection, and temporary mitigation.
8. `synthesis`: distinguish theoretical exposure from verified applicability.

## Threat Modeling and Architecture Review

1. `system-model`: document assets, actors, data flows, trust boundaries, and dependencies.
2. `assumption-audit`: enumerate security assumptions and missing architecture evidence.
3. `threat-clusters`: assign independent trust boundaries or abuse cases to workers.
4. `control-review`: map preventive, detective, and recovery controls.
5. `scenario-validation`: validate realistic preconditions without operationalizing attacks.
6. `risk-ranking`: score impact, likelihood, uncertainty, and control strength.
7. `mitigation-design`: propose testable changes and owners.
8. `synthesis`: include residual risk and unmodeled areas.

## Routing Rules

- Use one worker when the question requires full-system context or shared mutable state.
- Use parallel workers for independent components, advisory sources, or trust boundaries.
- Use a separate verifier for high-impact or ambiguous findings.
- Use a fresh synthesizer after evidence normalization; never use it for discovery.
- Treat simulator builds, FPGA boards, licensed tools, high-memory nodes, and mutable checkpoints as exclusive resources.
- Group architecture tasks by independent question or experiment cell, not by arbitrary RTL file ranges.
