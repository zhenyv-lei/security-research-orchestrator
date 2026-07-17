# Task Isolation and Linking

## Isolation Boundary

Each slot worker receives:

1. `tasks/<slot-id>/task.json`;
2. locked context;
3. only artifacts named in `inputs`;
4. `assets/templates/slot-proposal.json`;
5. write access only to `slots/<slot-id>/`.

Do not pass the manager conversation, sibling proposals, desired conclusions, or hidden expected answers.

## Link Contract

A link is a tuple:

```json
{
  "from_slot": "ARCH_MAP",
  "output": "components",
  "to_slot": "HYPOTHESES",
  "artifact": "slots/ARCH_MAP/proposal.json#outputs/components"
}
```

The compiler derives links from `consumes`. Links are immutable within a template revision.
Before dispatch, `prepare_task_inputs.py` resolves each link into a separate
`inbox/<consumer>/<producer>.<output>.json` projection. Give the worker the projection,
not the full producer proposal. Use a filesystem sandbox or worktree to enforce this
boundary when the runtime supports it.

Workers must not:

- read an undeclared output;
- infer a missing upstream value from task names;
- contact another worker;
- change a producer's proposal;
- add graph edges;
- write shared state.

## Simple Auxiliary Links

Prefer narrow links that answer one question:

```text
TARGET_SNAPSHOT.target_snapshot
    → ARCH_MAP

ARCH_MAP.components
    → HYPOTHESES

HYPOTHESES.hypotheses
    → EXPERIMENT_MATRIX

EXPERIMENT_MATRIX.experiment_matrix
    → VERIFICATION

VERIFICATION.verified_packet
    → SYNTHESIS
```

Avoid links such as `CONTEXT.everything`. If a worker needs only component names, link `ARCH_MAP.components`, not the full report.

## Scheduling

The compiler creates topological waves:

```text
wave 0: independent evidence and user-completed slots
wave 1: generative slots using wave-0 outputs
wave 2: derived experiment or comparison slots
wave 3: verification slots
wave 4: synthesis
```

Tasks in a wave may run in parallel only when they do not share:

- an exclusive tool, server, simulator, board, or dataset lock;
- a mutable output path;
- a source that cannot support concurrent access;
- an unresolved authorization dependency.

The manager owns scheduling and state. Workers never dispatch workers.

## Ownership

| Artifact | Owner |
|---|---|
| Template and revision | Manager |
| `run-state.json` | Manager |
| `task.json` | Compiler/manager |
| `proposal.json` | Assigned slot worker |
| Verification packet | Assigned verifier |
| Final report | Fresh synthesizer |

Reject a run in which two workers own the same proposal or mutable file.

## Graph Expansion

A worker may return:

```json
{
  "new_slot_proposals": [
    {
      "suggested_slot_id": "MISSING_CONTROL",
      "reason": "The current experiment lacks a negative control.",
      "depends_on": ["EXPERIMENT_MATRIX"],
      "consumes": ["EXPERIMENT_MATRIX.experiment_matrix"],
      "produces": ["control_design"],
      "scope_change": false
    }
  ]
}
```

This is a proposal, not a live edge. The manager must:

1. deduplicate it;
2. check authorization and composition risk;
3. define acceptance criteria;
4. assign ownership and resources;
5. increment the template revision;
6. recompile the graph.

Compile the child graph with an explicit `--revision`. Compatible completed proposals
remain immutable inputs only when their complete slot contract, locked context, named
inputs, and source hashes are unchanged. Record copied proposal hashes and invalidate
every changed slot plus its downstream consumers.

## Information Leakage Controls

- Redact secrets before writing proposals.
- Do not embed entire source artifacts in a slot output.
- Prefer stable locators and hashes.
- Mark sensitive outputs and intended audience.
- Ensure synthesis receives only the minimum material needed for the report.

Task isolation must never be used to split a restricted capability into benign-looking pieces for later recombination.
