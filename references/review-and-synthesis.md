# Review and Synthesis

## Verification Gates

Apply these gates to every material finding:

1. **Scope gate** — the claim concerns an authorized asset and permitted action.
2. **Evidence gate** — every factual claim has a resolvable evidence locator.
3. **Control gate** — attacker or failure control is established, not assumed.
4. **Reachability gate** — the relevant path is reachable under stated configuration.
5. **Protection gate** — environmental and application protections are considered.
6. **Counterexample gate** — common false-positive explanations were tested.
7. **Reproducibility gate** — quantitative claims identify the snapshot, workload, seeds/repetitions, raw artifact, and analysis method.
8. **Interpretation gate** — architectural correctness, microarchitectural behavior, security impact, and mitigation cost are not conflated.

Failure at any gate prevents a `verified` verdict.

## Independent Verification

Give the verifier the claim, scope, source artifacts, and evidence records. Withhold the discovery worker's confidence score and preferred verdict. Require a reasoned verdict plus evidence IDs and unresolved assumptions.

For `verified` or `corroborated`, require a distinct completed `verification` task that depends on the finding's origin and contributes evidence cited by the finding. A resolved conflict likewise requires verifier-owned evidence and completed verifier artifacts; metadata naming a verifier is not sufficient.

Verifier evidence must explicitly list the finding ID in `supports`. Accepted findings keep observation, interpretation, impact, counter-evidence, false-positive hypotheses, severity/confidence rationales, regression checks, and limitations as substantive separate fields.

Cluster findings for verification only when they share the same root cause and evidence. Do not let clustering hide per-instance reachability differences.

## Conflict Resolution

When workers disagree:

1. Normalize both claims into the same scope and terminology.
2. Compare evidence freshness, directness, and reproducibility.
3. Assign a fresh verifier if the disagreement changes impact or remediation.
4. Preserve unresolved alternatives and state what evidence would resolve them.

## Synthesis Packet

Provide the synthesis agent only normalized artifacts:

- scope and completion criteria;
- verified, corroborated, candidate, rejected, and blocked findings;
- evidence index;
- design snapshot, experiment matrix, artifact manifest, and reproducibility status when present;
- coverage matrix;
- conflicts and limitations;
- final-report template.

Require the synthesizer to:

- lead with verified conclusions;
- calibrate verbs to verdict strength;
- deduplicate by root cause without losing affected instances;
- separate observed facts from analyst inference;
- include rejected findings when they prevent repeated false alarms;
- state incomplete coverage and policy or authorization blocks;
- avoid adding uncited technical details.

A completed v3 run has exactly one completed `synthesis` task that owns `final/final-report.md`, an exact `evidence-index.json`, a non-empty final checkpoint, substantive required report sections, and at least one row in the canonical claim-to-evidence table. Every matrix claim and evidence ID must exist, and each cited evidence record must list that claim in `supports`. The microarchitecture profile additionally requires populated design-snapshot and experiment/artifact sections.

## Acceptance Metrics

- Claim coverage: 100% of accepted factual claims map to evidence.
- Verification coverage: 100% of high-impact findings have an independent verifier.
- Task closure: 100% of tasks have a valid terminal state.
- Conflict disclosure: 100% of unresolved material conflicts appear in limitations.
- Redaction: no raw secrets or unnecessary personal data remain.
- Reproducibility: 100% of accepted quantitative claims map to a pinned snapshot and hash-verified raw artifact.
- Experiment control: every accepted microarchitecture measurement records controls or a justified deterministic design.
