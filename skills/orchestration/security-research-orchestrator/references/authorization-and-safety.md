# Authorization and Safety

Read this file before active testing, external interaction, or ambiguous dual-use work.

## Authorization Tiers

| Tier | Evidence | Allowed work |
|---|---|---|
| A0 — Unconfirmed | No ownership or authorization evidence | Public-source research, local read-only review, threat modeling, remediation guidance |
| A1 — Local lab | User-controlled isolated fixtures or toy targets | Bounded local validation that cannot affect third parties |
| A2 — Authorized target | Target, method, time window, and limits are explicit | Only the approved active actions inside the stated window |

Default to A0. Never infer authorization from target accessibility, public exposure, employment, or possession of a URL.

## Composition Review

Review the requested goal twice: before task dispatch and before final synthesis.

Record:

```json
{
  "individual_tasks_within_scope": true,
  "combined_output_within_scope": true,
  "unnecessary_operational_detail_removed": true,
  "sensitive_data_redacted": true
}
```

If separate outputs would combine into credential theft, stealth, persistence, destructive access, unauthorized exploitation, or another disallowed capability, reject that decomposition. Replace it with defensive analysis, detection, mitigation, or a toy-environment validation.

## Active-Testing Approval Packet

Present all fields before requesting approval:

- exact target and owner;
- authorization source;
- command or method class;
- traffic volume, mutation, and expected side effects;
- containment and rollback;
- sensitive data that may be observed;
- stop condition and time window.

Record approval in `run-state.json` using this structure; a boolean alone is not sufficient:

```json
{
  "active_testing_approved": false,
  "active_testing_approval": {
    "approval_id": "",
    "approved": false,
    "approved_task_ids": [],
    "target": "",
    "owner": "",
    "authorization_source": "",
    "method_class": "",
    "time_window": "",
    "rate_limits": "",
    "mutation": "",
    "expected_traffic_or_side_effects": "",
    "containment": "",
    "rollback": "",
    "sensitive_data_exposure": "",
    "stop_conditions": []
  }
}
```

When approved, require canonical authorization tier `A1` or `A2` and non-empty values for every packet field. Keep `approved` equal to `active_testing_approved`. List every approved active task in `approved_task_ids`; each task must use the same `approval_id` in its safety block.

Do not place dynamic intent in a `non_operational` objective, research question, or allowed-action string while leaving `active_actions` empty. The validator recognizes common English and Chinese execution, simulation, probing, mutation, collection, and measurement verbs, but deterministic matching is only a lower bound; the manager still reviews semantic intent.

For simulator, formal, FPGA, or silicon work, also bind every experiment to that task with the same `approval_id`. Local simulation or formal execution requires at least A1. FPGA or silicon execution requires A2 with the exact board/device, image/configuration, owner, time window, side effects, rollback, and stop conditions. Access to a simulator or hardware board does not by itself establish approval. An A0 microarchitecture run remains limited to supplied artifacts and read-only source/configuration analysis.

## Safety-Blocked Tasks

Treat a safety refusal as terminal for that task definition. Do not route it to another worker or change wording to obtain the same capability.

Create a replacement task only when its objective is materially safer, such as:

- explain root cause without exploit construction;
- identify detection signals and mitigations;
- validate a patch in a local toy fixture;
- assess configuration exposure from supplied artifacts;
- produce a non-operational summary.

Link the replacement with `fallback_of`, preserve the original `policy_blocked` status, and disclose the coverage gap.

## Data Handling

- Store only the minimum evidence necessary.
- Replace secrets with stable redaction tokens such as `[REDACTED-TOKEN-01]`.
- Record the location and type of a secret, not its value.
- Do not transmit private artifacts to external services without explicit approval.
- Remove personal data and unnecessary exploit detail from synthesis outputs.
