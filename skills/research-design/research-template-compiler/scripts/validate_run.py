#!/usr/bin/env python3
"""Validate compiled research-template runs and slot proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from compile_research import (
    DEFAULT_MAX_ATTEMPTS,
    REFERENCE_RE,
    SCHEMA_VERSION,
    SLOT_ID_RE,
    canonical_hash,
    read_json,
    resource_safe_task_waves,
    topological_waves,
    validate_template,
    write_json,
)


STATE_REQUIRED = {
    "schema_version",
    "template_id",
    "template_revision",
    "template_hash",
    "locked_context_hash",
    "locked_context",
    "slot_states",
    "precompleted_slots",
    "task_ids",
    "links",
    "waves",
    "synthesis_slot",
    "needs_input",
    "status",
}
TASK_REQUIRED = {
    "schema_version",
    "task_id",
    "slot_id",
    "role",
    "objective",
    "dependencies",
    "inputs",
    "locked_context",
    "produces",
    "required_keywords",
    "acceptance_criteria",
    "max_candidates",
    "stop_conditions",
    "escalation_conditions",
    "exclusive_resources",
    "assigned_paths",
    "expected_output",
    "unresolved_dependencies",
    "status",
    "attempts",
    "max_attempts",
}
PROPOSAL_REQUIRED = {
    "schema_version",
    "slot_id",
    "candidate_id",
    "filled_keywords",
    "outputs",
    "claims",
    "alternatives",
    "unknowns",
    "reviewed_slots",
    "new_slot_proposals",
    "status",
}
PROPOSAL_STATUSES = {
    "proposed",
    "evidenced",
    "verified",
    "corroborated",
    "rejected",
    "blocked",
    "policy_blocked",
    "inconclusive",
    "completed",
}
VERIFICATION_TERMINAL = {
    "verified",
    "corroborated",
    "rejected",
    "blocked",
    "policy_blocked",
    "inconclusive",
}
TASK_STATUSES = {
    "pending",
    "blocked_dependency",
    "running",
    "completed",
    "failed",
    "policy_blocked",
}
SLOT_STATES = {
    "completed",
    "needs_input",
    "pending",
    "blocked_dependency",
    "proposed",
    "evidenced",
    "verified",
    "corroborated",
    "rejected",
    "blocked",
    "policy_blocked",
    "inconclusive",
    "running",
    "failed",
}
FULFILLING_STATES = {"completed", "proposed", "evidenced", "verified", "corroborated"}


def _require_keys(
    data: Any,
    required: set[str],
    label: str,
    errors: list[str],
    *,
    exact: bool = False,
) -> bool:
    if not isinstance(data, dict):
        errors.append(f"{label} must be an object")
        return False
    missing = sorted(required - data.keys())
    if missing:
        errors.append(f"{label} missing keys: {', '.join(missing)}")
        return False
    if exact:
        extra = sorted(data.keys() - required)
        if extra:
            errors.append(f"{label} has undeclared keys: {', '.join(extra)}")
            return False
    return True


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return "{{" in value or "}}" in value
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(key) or _contains_placeholder(item) for key, item in value.items())
    return False


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _expected_inputs(slot: dict[str, Any]) -> list[dict[str, str]]:
    inputs: list[dict[str, str]] = []
    for reference in slot["consumes"]:
        producer_id, output_name = reference.split(".", 1)
        inputs.append(
            {
                "reference": reference,
                "artifact": f"inbox/{slot['slot_id']}/{producer_id}.{output_name}.json",
                "source_artifact": f"slots/{producer_id}/proposal.json#outputs/{output_name}",
            }
        )
    return inputs


def _expected_links(template: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for slot in template["slots"]:
        for item in _expected_inputs(slot):
            producer_id, output_name = item["reference"].split(".", 1)
            links.append(
                {
                    "from_slot": producer_id,
                    "output": output_name,
                    "to_slot": slot["slot_id"],
                    "artifact": item["source_artifact"],
                }
            )
    return links


def _dependency_is_fulfilled(
    dependency_id: str,
    slots: dict[str, dict[str, Any]],
    slot_states: dict[str, str],
) -> bool:
    state = slot_states.get(dependency_id)
    if slots[dependency_id]["kind"] == "verification":
        return state in VERIFICATION_TERMINAL
    return state in FULFILLING_STATES


def refresh_run_state(run_dir: Path) -> dict[str, Any]:
    """Recompute lifecycle state and task readiness from immutable proposals."""
    run_dir = run_dir.resolve()
    state = read_json(run_dir / "run-state.json")
    template = read_json(run_dir / "resolved-template.json")
    validate_template(template)
    if state.get("template_hash") != canonical_hash(template):
        raise ValueError("resolved template hash does not match run state")

    slots = {slot["slot_id"]: slot for slot in template["slots"]}
    proposal_statuses: dict[str, str] = {}
    for slot_id in slots:
        path = run_dir / "slots" / slot_id / "proposal.json"
        if not path.exists():
            continue
        proposal = read_json(path)
        status = proposal.get("status") if isinstance(proposal, dict) else None
        if status not in PROPOSAL_STATUSES:
            raise ValueError(f"cannot refresh from invalid proposal status: {slot_id}")
        proposal_statuses[slot_id] = status

    refreshed: dict[str, str] = {}
    for wave in topological_waves(template["slots"]):
        for slot_id in wave:
            slot = slots[slot_id]
            if slot["kind"] == "locked":
                refreshed[slot_id] = "completed"
            elif slot_id in proposal_statuses:
                refreshed[slot_id] = proposal_statuses[slot_id]
            elif slot["kind"] == "human":
                refreshed[slot_id] = "needs_input"
            else:
                unresolved = [
                    dependency
                    for dependency in slot["depends_on"]
                    if not _dependency_is_fulfilled(dependency, slots, refreshed)
                ]
                refreshed[slot_id] = "blocked_dependency" if unresolved else "pending"

    for slot_id in state.get("task_ids", []):
        task_path = run_dir / "tasks" / slot_id / "task.json"
        task = read_json(task_path)
        unresolved = [
            dependency
            for dependency in slots[slot_id]["depends_on"]
            if not _dependency_is_fulfilled(dependency, slots, refreshed)
        ]
        task["unresolved_dependencies"] = unresolved
        if slot_id in proposal_statuses:
            task["status"] = "completed"
        elif task.get("attempts", 0) >= task.get("max_attempts", DEFAULT_MAX_ATTEMPTS):
            task["status"] = "failed"
        else:
            task["status"] = "blocked_dependency" if unresolved else "pending"
        write_json(task_path, task)

    state["slot_states"] = refreshed
    state["needs_input"] = sorted(
        slot_id for slot_id, status in refreshed.items() if status == "needs_input"
    )
    synthesis_status = proposal_statuses.get(template["synthesis_slot"])
    if state["needs_input"]:
        state["status"] = "needs_input"
    elif synthesis_status == "completed":
        state["status"] = "completed"
    elif "policy_blocked" in refreshed.values():
        state["status"] = "policy_blocked"
    elif proposal_statuses:
        state["status"] = "running"
    else:
        state["status"] = "planning"
    write_json(run_dir / "run-state.json", state)
    return state


def _validate_claims(claims: Any, label: str, errors: list[str]) -> None:
    if not isinstance(claims, list):
        errors.append(f"{label}.claims must be a list")
        return
    seen: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"{label}.claims[{index}] must be an object")
            continue
        required = {"claim_id", "statement", "evidence_ids", "confidence"}
        missing = required - claim.keys()
        if missing:
            errors.append(f"{label}.claims[{index}] missing: {', '.join(sorted(missing))}")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            errors.append(f"{label}.claims[{index}].claim_id must be non-empty")
        elif claim_id in seen:
            errors.append(f"{label} has duplicate claim_id: {claim_id}")
        else:
            seen.add(claim_id)
        if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
            errors.append(f"{label}.claims[{index}].statement must be non-empty")
        if not isinstance(claim.get("evidence_ids"), list):
            errors.append(f"{label}.claims[{index}].evidence_ids must be a list")


def _validate_new_slots(
    proposals: Any,
    existing_slots: dict[str, dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(proposals, list):
        errors.append(f"{label}.new_slot_proposals must be a list")
        return
    suggested_ids: set[str] = set()
    for index, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            errors.append(f"{label}.new_slot_proposals[{index}] must be an object")
            continue
        required = {"suggested_slot_id", "reason", "depends_on", "consumes", "produces", "scope_change"}
        missing = required - proposal.keys()
        if missing:
            errors.append(
                f"{label}.new_slot_proposals[{index}] missing: {', '.join(sorted(missing))}"
            )
            continue
        extra = proposal.keys() - required
        if extra:
            errors.append(
                f"{label}.new_slot_proposals[{index}] has undeclared keys: "
                f"{', '.join(sorted(extra))}"
            )
        suggested = proposal.get("suggested_slot_id")
        if not isinstance(suggested, str) or not SLOT_ID_RE.fullmatch(suggested):
            errors.append(f"{label} proposes invalid slot_id: {suggested}")
        elif suggested in existing_slots:
            errors.append(f"{label} proposes existing slot_id: {suggested}")
        elif suggested in suggested_ids:
            errors.append(f"{label} proposes duplicate slot_id: {suggested}")
        else:
            suggested_ids.add(suggested)
        if not isinstance(proposal.get("reason"), str) or not proposal["reason"].strip():
            errors.append(f"{label}.new_slot_proposals[{index}].reason must be non-empty")
        if not isinstance(proposal.get("scope_change"), bool):
            errors.append(f"{label}.new_slot_proposals[{index}].scope_change must be boolean")
        for key in ("depends_on", "consumes", "produces"):
            if not isinstance(proposal.get(key), list) or any(
                not isinstance(item, str) for item in proposal.get(key, [])
            ):
                errors.append(f"{label}.new_slot_proposals[{index}].{key} must be a list")
        dependencies = proposal.get("depends_on", [])
        if isinstance(dependencies, list):
            unknown_dependencies = sorted(
                dependency
                for dependency in dependencies
                if isinstance(dependency, str) and dependency not in existing_slots
            )
            if unknown_dependencies:
                errors.append(
                    f"{label} proposes unknown dependencies: {', '.join(unknown_dependencies)}"
                )
        produces = proposal.get("produces", [])
        if isinstance(produces, list):
            if len(produces) != len(set(item for item in produces if isinstance(item, str))):
                errors.append(f"{label} proposes duplicate outputs")
            if any(
                not isinstance(item, str)
                or not item
                or not item[0].islower()
                or not item.replace("_", "").isalnum()
                for item in produces
            ):
                errors.append(f"{label} proposes invalid output names")
        for reference in proposal.get("consumes", []) if isinstance(proposal.get("consumes"), list) else []:
            if not isinstance(reference, str) or not REFERENCE_RE.fullmatch(reference):
                errors.append(f"{label} proposes invalid consumes reference: {reference}")
                continue
            producer_id, output_name = reference.split(".", 1)
            if producer_id not in existing_slots:
                errors.append(f"{label} proposes unknown producer: {producer_id}")
            elif output_name not in existing_slots[producer_id]["produces"]:
                errors.append(f"{label} proposes unknown producer output: {reference}")
            if producer_id not in dependencies:
                errors.append(f"{label} consumes a producer outside depends_on: {reference}")


def validate_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    run_dir = run_dir.resolve()
    try:
        state = read_json(run_dir / "run-state.json")
        template = read_json(run_dir / "resolved-template.json")
    except ValueError as exc:
        return [str(exc)]

    if not _require_keys(state, STATE_REQUIRED, "run-state.json", errors):
        return errors
    try:
        validate_template(template)
    except ValueError as exc:
        errors.append(f"resolved template invalid: {exc}")
        return errors

    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported run schema_version: {state.get('schema_version')}")
    if state.get("template_id") != template.get("template_id"):
        errors.append("run template_id does not match resolved template")
    if state.get("template_hash") != canonical_hash(template):
        errors.append("resolved template hash does not match run state")
    if state.get("locked_context_hash") != canonical_hash(state.get("locked_context")):
        errors.append("locked context hash does not match run state")
    if state.get("locked_context") != template.get("locked_context"):
        errors.append("locked context differs from resolved template")

    slots = {slot["slot_id"]: slot for slot in template["slots"]}
    slot_states = state.get("slot_states")
    if not isinstance(slot_states, dict) or set(slot_states) != set(slots):
        errors.append("slot_states must contain every template slot exactly once")
        slot_states = {}
    elif any(status not in SLOT_STATES for status in slot_states.values()):
        errors.append("slot_states contains an invalid lifecycle status")
    if state.get("synthesis_slot") != template.get("synthesis_slot"):
        errors.append("synthesis_slot does not match resolved template")
    if state.get("links") != _expected_links(template):
        errors.append("run links do not exactly match declared consumes references")

    task_ids = state.get("task_ids")
    if not isinstance(task_ids, list) or any(task_id not in slots for task_id in task_ids):
        errors.append("task_ids contains unknown or malformed slot IDs")
        task_ids = []
    if len(task_ids) != len(set(task_ids)):
        errors.append("task_ids must be unique")
    precompleted = state.get("precompleted_slots")
    if (
        not isinstance(precompleted, list)
        or len(precompleted) != len(set(precompleted))
        or any(slot_id not in slots for slot_id in precompleted)
    ):
        errors.append("precompleted_slots must be a unique list of known slot IDs")
        precompleted = []
    expected_task_ids = [
        slot_id
        for slot_id, slot in slots.items()
        if slot["kind"] not in {"human", "locked"} and slot_id not in precompleted
    ]
    if task_ids != expected_task_ids:
        errors.append("task_ids do not match the task set derived from the template")
    tasks_root = run_dir / "tasks"
    task_directories = sorted(
        path.name for path in tasks_root.iterdir() if path.is_dir()
    ) if tasks_root.exists() else []
    if sorted(task_ids) != task_directories:
        errors.append("task_ids do not exactly match task contract directories")

    wave_members: list[str] = []
    waves = state.get("waves")
    if not isinstance(waves, list):
        errors.append("waves must be a list")
    else:
        for index, wave in enumerate(waves):
            if not isinstance(wave, list):
                errors.append(f"wave {index} must be a list")
                continue
            wave_members.extend(wave)
        if sorted(wave_members) != sorted(task_ids):
            errors.append("waves must schedule every task exactly once")
        expected_waves = resource_safe_task_waves(template["slots"], task_ids)
        if waves != expected_waves:
            errors.append(
                "waves differ from the dependency- and exclusive-resource-safe schedule"
            )

    proposals: dict[str, dict[str, Any]] = {}
    existing_slots = slots

    for slot_id in task_ids:
        slot = slots[slot_id]
        task_path = run_dir / "tasks" / slot_id / "task.json"
        try:
            task = read_json(task_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        label = f"tasks/{slot_id}/task.json"
        if not _require_keys(task, TASK_REQUIRED, label, errors, exact=True):
            continue
        if task.get("task_id") != slot_id or task.get("slot_id") != slot_id:
            errors.append(f"{label} has mismatched task or slot ID")
        if task.get("role") != slot["kind"]:
            errors.append(f"{label} role differs from template")
        if task.get("dependencies") != slot["depends_on"]:
            errors.append(f"{label} dependencies differ from template")
        if task.get("inputs") != _expected_inputs(slot):
            errors.append(f"{label} inputs violate slot isolation contract")
        if task.get("locked_context") != state.get("locked_context"):
            errors.append(f"{label} locked context differs from run")
        for key in (
            "produces",
            "required_keywords",
            "acceptance_criteria",
            "max_candidates",
            "stop_conditions",
            "escalation_conditions",
            "exclusive_resources",
        ):
            if task.get(key) != slot[key]:
                errors.append(f"{label} {key} differs from template")
        if task.get("objective") != slot["prompt"]:
            errors.append(f"{label} objective differs from template")
        if task.get("assigned_paths") != [f"slots/{slot_id}/"]:
            errors.append(f"{label} has invalid output ownership")
        if task.get("expected_output") != f"slots/{slot_id}/proposal.json":
            errors.append(f"{label} has invalid expected_output")
        unresolved = task.get("unresolved_dependencies")
        if (
            not isinstance(unresolved, list)
            or any(item not in slot["depends_on"] for item in unresolved)
            or len(unresolved) != len(set(unresolved))
        ):
            errors.append(f"{label} has invalid unresolved_dependencies")
        if task.get("status") not in TASK_STATUSES:
            errors.append(f"{label} has invalid task status")
        attempts = task.get("attempts")
        max_attempts = task.get("max_attempts")
        if (
            not isinstance(attempts, int)
            or not isinstance(max_attempts, int)
            or attempts < 0
            or max_attempts < 0
            or attempts > max_attempts
        ):
            errors.append(f"{label} has invalid attempt budget")
        if max_attempts != DEFAULT_MAX_ATTEMPTS:
            errors.append(f"{label} max_attempts differs from the compiled retry contract")

        proposal_path = run_dir / "slots" / slot_id / "proposal.json"
        if not proposal_path.exists():
            continue
        try:
            proposal = read_json(proposal_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        proposals[slot_id] = proposal

    for slot_id, slot in slots.items():
        proposal_path = run_dir / "slots" / slot_id / "proposal.json"
        if not proposal_path.exists():
            continue
        if slot_id not in proposals:
            try:
                proposals[slot_id] = read_json(proposal_path)
            except ValueError as exc:
                errors.append(str(exc))

    for slot_id, proposal in proposals.items():
        slot = slots[slot_id]
        label = f"slots/{slot_id}/proposal.json"
        if not _require_keys(proposal, PROPOSAL_REQUIRED, label, errors, exact=True):
            continue
        if proposal.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{label} has unsupported schema_version")
        if proposal.get("slot_id") != slot_id:
            errors.append(f"{label} has mismatched slot_id")
        if not isinstance(proposal.get("candidate_id"), str) or not proposal["candidate_id"]:
            errors.append(f"{label} candidate_id must be non-empty")
        status = proposal.get("status")
        if status not in PROPOSAL_STATUSES:
            errors.append(f"{label} has invalid status: {status}")

        keywords = proposal.get("filled_keywords")
        if not isinstance(keywords, dict):
            errors.append(f"{label}.filled_keywords must be an object")
        else:
            missing_keywords = sorted(set(slot["required_keywords"]) - keywords.keys())
            if missing_keywords:
                errors.append(f"{label} missing keywords: {', '.join(missing_keywords)}")
            blank_keywords = sorted(
                keyword
                for keyword in slot["required_keywords"]
                if keyword in keywords and _is_blank(keywords[keyword])
            )
            if blank_keywords:
                errors.append(f"{label} has blank keywords: {', '.join(blank_keywords)}")
        outputs = proposal.get("outputs")
        if not isinstance(outputs, dict):
            errors.append(f"{label}.outputs must be an object")
        else:
            missing_outputs = sorted(set(slot["produces"]) - outputs.keys())
            if missing_outputs:
                errors.append(f"{label} missing outputs: {', '.join(missing_outputs)}")
            blank_outputs = sorted(
                output
                for output in slot["produces"]
                if output in outputs and _is_blank(outputs[output])
            )
            if blank_outputs:
                errors.append(f"{label} has blank outputs: {', '.join(blank_outputs)}")
        for key in ("alternatives", "unknowns", "reviewed_slots"):
            if not isinstance(proposal.get(key), list):
                errors.append(f"{label}.{key} must be a list")
        _validate_claims(proposal.get("claims"), label, errors)
        _validate_new_slots(proposal.get("new_slot_proposals"), existing_slots, label, errors)
        keyword_object = proposal.get("filled_keywords")
        output_object = proposal.get("outputs")
        candidate_collections = [
            value
            for key, value in keyword_object.items()
            if key.startswith("candidate_") and isinstance(value, list)
        ] if isinstance(keyword_object, dict) else []
        if isinstance(output_object, dict):
            candidate_collections.extend(
                value for value in output_object.values() if isinstance(value, list)
            )
        if any(len(value) > slot["max_candidates"] for value in candidate_collections):
            errors.append(f"{label} exceeds max_candidates")
        if _contains_placeholder(proposal.get("outputs")):
            errors.append(f"{label} contains unresolved template placeholders")

        if slot["kind"] not in {"verification", "synthesis", "human"} and status in {
            "verified",
            "corroborated",
            "rejected",
        }:
            errors.append(f"{label} cannot self-assign verification status")
        if slot["kind"] == "verification":
            reviewed = proposal.get("reviewed_slots", [])
            if not reviewed:
                errors.append(f"{label} must name reviewed_slots")
            elif slot_id in reviewed:
                errors.append(f"{label} cannot review itself")
            elif any(reviewed_id not in slot["depends_on"] for reviewed_id in reviewed):
                errors.append(f"{label} reviews a slot outside its dependency contract")
            elif set(reviewed) != set(slot["depends_on"]):
                errors.append(f"{label} must review every declared dependency exactly once")
            for dependency in slot["depends_on"]:
                if dependency not in proposals:
                    errors.append(f"{label} is missing reviewed proposal: {dependency}")
            if status not in VERIFICATION_TERMINAL:
                errors.append(f"{label} verification status must be terminal")
        if slot["kind"] == "synthesis" and status == "completed":
            for dependency in slot["depends_on"]:
                dependency_proposal = proposals.get(dependency)
                if dependency_proposal is None:
                    errors.append(f"{label} is missing synthesis dependency: {dependency}")
                elif slots[dependency]["kind"] == "verification" and dependency_proposal.get(
                    "status"
                ) not in VERIFICATION_TERMINAL:
                    errors.append(f"{label} depends on non-terminal verification: {dependency}")

    for slot_id, slot in slots.items():
        proposal_exists = slot_id in proposals
        state_status = slot_states.get(slot_id)
        if slot["kind"] == "locked" and state_status != "completed":
            errors.append(f"locked slot {slot_id} must remain completed")
        if slot_id in precompleted and not proposal_exists:
            errors.append(f"precompleted slot {slot_id} is missing its proposal")
        if proposal_exists and state_status != proposals[slot_id].get("status"):
            errors.append(f"slot {slot_id} state is stale; run validate_run.py --refresh")
        if (
            not proposal_exists
            and slot["kind"] != "locked"
            and state_status
            not in {"needs_input", "pending", "blocked_dependency"}
        ):
            errors.append(f"slot {slot_id} has terminal state without a proposal")
    expected_needs_input = sorted(
        slot_id for slot_id, status in slot_states.items() if status == "needs_input"
    )
    if state.get("needs_input") != expected_needs_input:
        errors.append("needs_input does not match slot_states")
    if expected_needs_input and state.get("status") != "needs_input":
        errors.append("run status must be needs_input while human values are missing")

    expansion_path = run_dir / "graph-expansion-proposals.json"
    try:
        expansions = read_json(expansion_path)
        if not isinstance(expansions, dict) or not isinstance(expansions.get("proposals"), list):
            errors.append("graph-expansion-proposals.json must contain a proposals list")
        else:
            _validate_new_slots(
                expansions["proposals"],
                existing_slots,
                "graph-expansion-proposals.json",
                errors,
            )
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="Compiled research run directory")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Recompute slot and task readiness from proposal artifacts before validating",
    )
    args = parser.parse_args()
    if args.refresh:
        try:
            refresh_run_state(args.run_dir)
        except (ValueError, OSError) as exc:
            print(f"ERROR: {exc}")
            return 1
    errors = validate_run(args.run_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: valid research-template run at {args.run_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
