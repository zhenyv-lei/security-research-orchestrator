# Research Profiles

Select the smallest profile that satisfies the research goal. Add tasks only when they answer a distinct question.

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

