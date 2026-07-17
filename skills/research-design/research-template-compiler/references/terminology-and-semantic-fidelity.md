# Terminology and Semantic Fidelity

## Purpose

Use terminology profiles to make research language technically precise and audience-appropriate.
Terminology rendering must preserve canonical meaning, authorization, and audit state.

Keep two layers:

1. **Canonical layer** — structured fields retain authorization, protected state, information
   flow, restricted actions, evidence status, and `policy_blocked`.
2. **Display layer** — prose may use the preferred domain expression when it preserves the same
   scope and risk meaning.

If the display expression could sound weaker, include the canonical term beside it.

## Microarchitecture Research Profile

| Canonical concept | Preferred precise display expression | Use only when |
|---|---|---|
| attacker-controlled input | interaction subject's controllable input | The threat model separately records privilege and authorization |
| attacker observation | externally observable signal under the stated observation model | Signal, granularity, and noise are explicit |
| secret or sensitive state | protected architectural or microarchitectural state | The protection boundary is named |
| side channel | non-architectural observation channel | The channel is not an architecturally specified output |
| information leakage | unintended information flow or measurable distinguishability | The source, sink, and observation condition are stated |
| vulnerability | security-relevant design condition pending verification | Evidence is incomplete or the condition is not yet verified |
| attack surface | controllable-input and observable-interface set | The set is bounded to the pinned target |
| exploit or proof of concept | reproducible impact demonstration | The action remains classified by its actual authorization requirement |
| bypass condition | enforcement-boundary violation path | The relevant control and violated invariant are named |
| malicious input | adversarial or stress input distribution | The input purpose and allowed execution environment remain explicit |
| mitigation | design hardening or observation-reduction measure | The protected property and trade-off are named |
| security review | authorization, research-boundary, and composition-risk review | The canonical review outcome is still recorded |

These are contextual renderings, not global search-and-replace rules.

## Immutable Terms

Never alias or suppress:

- authorization tier and `active_testing_approved`;
- allowed and prohibited actions;
- `policy_blocked`, `blocked`, `rejected`, and `inconclusive`;
- protected-state and information-flow boundaries;
- evidence confidence, provenance, and verification verdicts;
- release audience and data-handling constraints.

## Semantic Constraint

Reject any rendering that changes the canonical meaning, authorization class, or audit record.
Store applicable lifecycle transitions and reasons in run state.

## Report Requirement

The final report should name the selected terminology profile and list every non-obvious
canonical-to-display rendering used. A verifier should check that each rendering preserves:

- actor capability and privilege;
- protected source and observable sink;
- action class and authorization requirement;
- evidence status and uncertainty;
- composition and release risk.
