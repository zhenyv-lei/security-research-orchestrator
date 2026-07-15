# Task and Evidence Contracts

Use the bundled JSON templates as the machine-readable source of truth.

## Task Contract

Every task must define:

- `task_id`, `role`, `objective`, and one `research_question`;
- `dependencies` and `assigned_paths`;
- `inputs` with stable artifact locations;
- `allowed_actions` and `prohibited_actions`;
- `expected_outputs` and `acceptance_criteria`;
- `evidence_requirements`;
- `stop_conditions` and `escalation_conditions`;
- `status`, `attempts`, and `max_attempts`.

Reject a task if its objective is broad, its outputs overlap another worker, or success cannot be tested.

## Worker Prompt Envelope

Construct worker prompts in this order:

1. State the role and research question.
2. Provide exact inputs and scope.
3. List allowed and prohibited actions.
4. State evidence and output requirements.
5. State stop and escalation conditions.
6. Require artifact paths and a concise completion summary.

Do not include other workers' conclusions or manager preferences.

## Evidence Record

Write one JSON object per line in `evidence.jsonl`:

```json
{
  "evidence_id": "EV-SR-001-01",
  "task_id": "SR-001",
  "kind": "source_code",
  "locator": "src/auth/session.ts:142",
  "observation": "Session identifier enters the lookup without normalization.",
  "supports": ["F-SR-001-01"],
  "source_date": null,
  "sensitivity": "internal",
  "hash": null
}
```

Prefer primary artifacts: source code, configuration, logs, test output, standards, vendor advisories, and authoritative vulnerability records. Label secondary commentary as secondary.

## Finding Contract

Every finding must contain:

- stable ID and concise title;
- affected scope and preconditions;
- observation, interpretation, and impact as separate fields;
- evidence IDs;
- counter-evidence and false-positive hypotheses;
- severity and confidence with short rationales;
- verification status and verifier task ID;
- remediation and regression-check proposal;
- limitations and redactions.

Never mark a finding `verified` solely because multiple agents repeat the same claim.

