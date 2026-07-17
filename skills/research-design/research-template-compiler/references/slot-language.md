# Slot Language

The Research Template Compiler uses JSON data only. It does not evaluate Python, shell, Mako, Jinja, or arbitrary expressions.

## Template Object

```json
{
  "schema_version": "1.0",
  "template_id": "base-research",
  "description": "General evidence-driven research",
  "extends": null,
  "locked_context": {
    "authorization_tier": "A0",
    "active_testing_approved": false,
    "allowed_actions": ["passive research"],
    "prohibited_actions": ["unauthorized active testing"],
    "data_handling": "minimum necessary",
    "output_audience": "requester",
    "terminology_profile": "domain-precise"
  },
  "slots": [],
  "synthesis_slot": "SYNTHESIS"
}
```

`extends` may name one JSON file in the same template tree. Parent slots are inherited. A child slot with the same `slot_id` replaces the parent slot. Paths that escape the top-level template directory are invalid.

`terminology_profile` controls display wording only. It cannot change canonical slot IDs,
authorization, prohibited actions, lifecycle statuses, or the meaning of a task contract.

## Slot Object

```json
{
  "slot_id": "HYPOTHESES",
  "kind": "generative",
  "prompt": "Generate distinct falsifiable hypotheses.",
  "depends_on": ["CONTEXT"],
  "consumes": ["CONTEXT.system_model"],
  "produces": ["hypotheses"],
  "required_keywords": [
    "candidate_hypotheses",
    "strongest_alternative",
    "falsification_conditions"
  ],
  "acceptance_criteria": [
    "Each hypothesis is falsifiable.",
    "Alternatives are materially distinct."
  ],
  "max_candidates": 5,
  "stop_conditions": ["Required context is missing."],
  "escalation_conditions": ["A new asset or active method is required."],
  "exclusive_resources": []
}
```

## Kinds and Freedom

| Kind | Filled by | Freedom | Typical output |
|---|---|---|---|
| `locked` | Compiler/user | None after compilation | Authorization or policy |
| `human` | User | User-controlled | Question, scope, audience |
| `evidence` | Worker from sources | Low | Snapshot, inventory, excerpts |
| `derived` | Worker from declared inputs | Medium | Matrix, taxonomy, comparison |
| `generative` | Worker | High but bounded | Hypotheses, alternatives |
| `verification` | Fresh verifier | Low/medium | Verdict packet |
| `synthesis` | Fresh synthesizer | Medium | Complete report |

Use high freedom only when multiple valid answers exist. Evidence and verification slots must remain source-bound.

## Dependencies and Links

`depends_on` controls scheduling. `consumes` controls information flow.

```json
{
  "depends_on": ["ARCH_MAP"],
  "consumes": [
    "ARCH_MAP.components",
    "TARGET_SNAPSHOT.target_snapshot"
  ]
}
```

Every reference must use `SLOT_ID.output_name`. The producer must declare that name in `produces`. A dependency may exist without a consumed value, but every consumed value creates an implicit dependency and must also appear in `depends_on`.

Do not use free-form paths or conversational references as links.

## Required Keywords vs Outputs

- `required_keywords` are reasoning obligations exposed in the proposal, such as `strongest_alternative`.
- `produces` are stable interface values consumed by downstream tasks, such as `hypotheses`.

A keyword may be explanatory while an output is machine-linked. Both must be present.

## Candidate Limits

Use `max_candidates` to prevent unbounded generation. Prefer:

- 1 for evidence extraction or synthesis;
- 2–5 for hypotheses and alternatives;
- one item per controlled experiment cell for derived matrices.

## Proposal Object

```json
{
  "schema_version": "1.0",
  "slot_id": "HYPOTHESES",
  "candidate_id": "HYPOTHESES-C1",
  "filled_keywords": {
    "candidate_hypotheses": ["..."],
    "strongest_alternative": "...",
    "falsification_conditions": ["..."]
  },
  "outputs": {
    "hypotheses": ["..."]
  },
  "claims": [
    {
      "claim_id": "CL-HYP-001",
      "statement": "...",
      "evidence_ids": [],
      "confidence": "low"
    }
  ],
  "alternatives": ["..."],
  "unknowns": ["..."],
  "reviewed_slots": [],
  "new_slot_proposals": [],
  "status": "proposed"
}
```

Allowed statuses are `proposed`, `evidenced`, `verified`, `corroborated`, `rejected`, `blocked`, `inconclusive`, and `completed`.

Verification proposals must identify `reviewed_slots`, emit declared verdict outputs, and use a terminal review status. Synthesis proposals must wait for terminal verification dependencies.

## Template Challenge

Generative templates should include a slot or keyword for:

- questions the template failed to ask;
- a materially different decomposition;
- anchoring or measurement bias;
- new-slot proposals.

This prevents template completion from becoming rote form filling.
