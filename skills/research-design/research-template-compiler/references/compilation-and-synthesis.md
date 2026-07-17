# Compilation, Verification, and Synthesis

## Compilation Lifecycle

1. Resolve parent templates.
2. Merge slots by `slot_id`.
3. Validate schema, IDs, kinds, outputs, links, and cycles.
4. Apply known human values.
5. Freeze locked context and template hash.
6. Mark missing human slots `needs_input`.
7. Generate one task contract per agent-fillable slot.
8. Compute topological waves.
9. Persist the resolved template and run state.
10. Materialize narrow per-task inbox projections only when dependencies are available.

Never evaluate code from a template or field value.

## Completion Lifecycle

```text
pending
├── needs_input
├── proposed
│   ├── evidenced
│   │   ├── verified
│   │   ├── corroborated
│   │   ├── rejected
│   │   └── inconclusive
│   └── blocked
└── policy_blocked
```

Generative and derived workers normally return `proposed` or `evidenced`. Only a verification slot may issue review verdicts. A synthesis slot returns `completed` only after consuming terminal verification packets.

## Verification Packet

A verifier should produce:

```json
{
  "reviewed_slots": ["HYPOTHESES", "EXPERIMENT_MATRIX"],
  "outputs": {
    "verified_packet": {
      "supported": [],
      "contradicted": [],
      "unresolved": [],
      "evidence_ids": [],
      "limitations": []
    }
  },
  "status": "verified"
}
```

Verification questions:

- Are all required upstream outputs present?
- Are observations separated from interpretations?
- Do claims map to evidence?
- Are alternatives and counterexamples considered?
- Are assumptions, configurations, and units consistent?
- Did the template omit a material question?
- Would combined slot outputs exceed authorization or safety boundaries?

## Synthesis Gate

Before dispatching synthesis, require:

- all synthesis dependencies have proposals;
- every verification dependency has a terminal review status;
- blocked and inconclusive slots are preserved;
- accepted graph expansions are recorded;
- locked context has not changed;
- no undeclared slot output is needed.

Synthesis must not read raw sibling conversations. It consumes proposal artifacts and verification packets.

## Slot Coverage

The final coverage artifact should contain:

```json
{
  "template_id": "microarchitecture-security",
  "template_revision": 1,
  "slots": [
    {
      "slot_id": "HYPOTHESES",
      "status": "verified",
      "proposal": "slots/HYPOTHESES/proposal.json",
      "used_outputs": ["hypotheses"],
      "limitations": []
    }
  ],
  "unresolved_slots": [],
  "blocked_slots": []
}
```

## Recovery

On resume:

1. run `validate_run.py <run> --refresh` to recompute state from proposals;
2. validate `run-state.json` and the resolved template hash;
3. verify completed proposal paths and IDs;
4. recompute runnable slots from declared dependencies;
5. preserve compatible completed proposals by contract and source hash, not filename;
6. retry only identical failed contracts within the fixed attempt budget;
7. recompile with an incremented `--revision` if any slot, edge, locked field, or output interface changes.

Do not recover from conversational memory.

## Partial Delivery

Partial synthesis is allowed only when the report explicitly states:

- completed and verified coverage;
- missing, blocked, and inconclusive slots;
- which conclusions cannot be drawn;
- exact evidence or user input needed to resume;
- whether the remaining omissions affect safety or validity.

## Example: Microarchitecture Research

```text
SCOPE (human)
  ↓
TARGET_SNAPSHOT (evidence)
  ↓
ARCH_MAP (evidence)
  ├──→ HYPOTHESES (generative)
  └──→ OBSERVATION_MODEL (generative)
              ↓
      EXPERIMENT_MATRIX (derived)
              ↓
         VERIFICATION
              ↓
           SYNTHESIS
```

The hypothesis worker does not receive raw RTL unless declared. It consumes the architecture map. The experiment worker consumes hypotheses and the observation model. The verifier receives the named proposals and source locators. The synthesizer receives the verified packet.
