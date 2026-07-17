#!/usr/bin/env python3
"""Compile a declarative research template into isolated slot tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
DEFAULT_MAX_ATTEMPTS = 2
SLOT_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
REFERENCE_RE = re.compile(r"^([A-Z][A-Z0-9_]{1,63})\.([a-z][a-z0-9_]{0,63})$")
SLOT_KINDS = {
    "locked",
    "human",
    "evidence",
    "generative",
    "derived",
    "verification",
    "synthesis",
}
SLOT_REQUIRED = {
    "slot_id",
    "kind",
    "prompt",
    "depends_on",
    "consumes",
    "produces",
    "required_keywords",
    "acceptance_criteria",
    "max_candidates",
    "stop_conditions",
    "escalation_conditions",
    "exclusive_resources",
}
TOP_REQUIRED = {
    "schema_version",
    "template_id",
    "description",
    "locked_context",
    "slots",
    "synthesis_slot",
}
LOCKED_CONTEXT_KEYS = {
    "authorization_tier",
    "active_testing_approved",
    "allowed_actions",
    "prohibited_actions",
    "data_handling",
    "output_audience",
    "terminology_profile",
}


class TemplateError(ValueError):
    """Raised when a research template violates the DSL."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TemplateError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TemplateError(f"invalid JSON {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical_hash(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _safe_child_path(parent: Path, relative: str, root: Path) -> Path:
    if not isinstance(relative, str) or not relative:
        raise TemplateError("extends must be a non-empty relative path")
    candidate = (parent / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise TemplateError(f"template inheritance escapes template root: {relative}") from exc
    return candidate


def merge_templates(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    merged = dict(parent)
    merged.update({key: value for key, value in child.items() if key not in {"slots", "locked_context", "extends"}})

    locked = dict(parent.get("locked_context", {}))
    locked.update(child.get("locked_context", {}))
    merged["locked_context"] = locked

    parent_slots = [dict(slot) for slot in parent.get("slots", [])]
    positions = {slot.get("slot_id"): index for index, slot in enumerate(parent_slots)}
    for child_slot in child.get("slots", []):
        slot_id = child_slot.get("slot_id")
        if slot_id in positions:
            parent_slots[positions[slot_id]] = dict(child_slot)
        else:
            positions[slot_id] = len(parent_slots)
            parent_slots.append(dict(child_slot))
    merged["slots"] = parent_slots
    merged["extends"] = None
    return merged


def resolve_template(
    path: Path,
    *,
    root: Path | None = None,
    stack: tuple[Path, ...] = (),
) -> dict[str, Any]:
    path = path.resolve()
    root = root or path.parent.resolve()
    if path in stack:
        chain = " -> ".join(item.name for item in (*stack, path))
        raise TemplateError(f"template inheritance cycle: {chain}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise TemplateError(f"template must be a JSON object: {path}")
    parent_ref = data.get("extends")
    if parent_ref:
        parent_path = _safe_child_path(path.parent, parent_ref, root)
        parent = resolve_template(parent_path, root=root, stack=(*stack, path))
        return merge_templates(parent, data)
    resolved = dict(data)
    resolved["extends"] = None
    return resolved


def topological_waves(slots: list[dict[str, Any]]) -> list[list[str]]:
    order = [slot["slot_id"] for slot in slots]
    dependencies = {slot["slot_id"]: set(slot["depends_on"]) for slot in slots}
    remaining = set(order)
    waves: list[list[str]] = []
    completed: set[str] = set()
    while remaining:
        wave = [slot_id for slot_id in order if slot_id in remaining and dependencies[slot_id] <= completed]
        if not wave:
            cycle_members = ", ".join(slot_id for slot_id in order if slot_id in remaining)
            raise TemplateError(f"slot dependency cycle: {cycle_members}")
        waves.append(wave)
        completed.update(wave)
        remaining.difference_update(wave)
    return waves


def resource_safe_task_waves(
    slots: list[dict[str, Any]],
    task_ids: list[str],
) -> list[list[str]]:
    """Split dependency waves deterministically when tasks share exclusive resources."""
    task_set = set(task_ids)
    by_id = {slot["slot_id"]: slot for slot in slots}
    scheduled: list[list[str]] = []
    for dependency_wave in topological_waves(slots):
        current: list[str] = []
        resources_in_use: set[str] = set()
        for slot_id in dependency_wave:
            if slot_id not in task_set:
                continue
            resources = set(by_id[slot_id]["exclusive_resources"])
            if current and resources & resources_in_use:
                scheduled.append(current)
                current = []
                resources_in_use = set()
            current.append(slot_id)
            resources_in_use.update(resources)
        if current:
            scheduled.append(current)
    return scheduled


def validate_locked_context(locked_context: Any) -> None:
    if not isinstance(locked_context, dict):
        raise TemplateError("locked_context must be an object")
    missing = LOCKED_CONTEXT_KEYS - locked_context.keys()
    unknown = locked_context.keys() - LOCKED_CONTEXT_KEYS
    if missing:
        raise TemplateError(f"locked_context missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise TemplateError(f"locked_context has unknown keys: {', '.join(sorted(unknown))}")
    if locked_context["authorization_tier"] not in {"A0", "A1", "A2"}:
        raise TemplateError("authorization_tier must be A0, A1, or A2")
    if not isinstance(locked_context["active_testing_approved"], bool):
        raise TemplateError("active_testing_approved must be a boolean")
    for key in ("allowed_actions", "prohibited_actions"):
        values = locked_context[key]
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(item, str) or not item.strip() for item in values)
        ):
            raise TemplateError(f"{key} must be a non-empty list of non-empty strings")
        wildcard = {"*", "all", "anything", "unrestricted"}
        if any(item.strip().lower() in wildcard for item in values):
            raise TemplateError(f"{key} cannot contain wildcard authorization")
    for key in ("data_handling", "output_audience"):
        if not isinstance(locked_context[key], str) or not locked_context[key].strip():
            raise TemplateError(f"{key} must be a non-empty string")
    if locked_context["terminology_profile"] not in {
        "canonical",
        "domain-precise",
        "microarchitecture-research-zh",
    }:
        raise TemplateError("terminology_profile is not a supported semantic-fidelity profile")
    if locked_context["authorization_tier"] == "A0" and locked_context["active_testing_approved"]:
        raise TemplateError("A0 locked context cannot approve active testing")


def validate_template(template: dict[str, Any]) -> None:
    missing = TOP_REQUIRED - template.keys()
    if missing:
        raise TemplateError(f"template missing keys: {', '.join(sorted(missing))}")
    if template.get("schema_version") != SCHEMA_VERSION:
        raise TemplateError(f"unsupported schema_version: {template.get('schema_version')}")
    if not isinstance(template.get("template_id"), str) or not template["template_id"]:
        raise TemplateError("template_id must be a non-empty string")
    validate_locked_context(template.get("locked_context"))
    slots = template.get("slots")
    if not isinstance(slots, list) or not slots:
        raise TemplateError("slots must be a non-empty list")

    by_id: dict[str, dict[str, Any]] = {}
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise TemplateError(f"slot {index} must be an object")
        missing_slot = SLOT_REQUIRED - slot.keys()
        if missing_slot:
            raise TemplateError(
                f"slot {slot.get('slot_id', index)} missing keys: {', '.join(sorted(missing_slot))}"
            )
        slot_id = slot.get("slot_id")
        if not isinstance(slot_id, str) or not SLOT_ID_RE.fullmatch(slot_id):
            raise TemplateError(f"invalid slot_id: {slot_id}")
        if slot_id in by_id:
            raise TemplateError(f"duplicate slot_id: {slot_id}")
        if slot.get("kind") not in SLOT_KINDS:
            raise TemplateError(f"invalid slot kind for {slot_id}: {slot.get('kind')}")
        for key in (
            "depends_on",
            "consumes",
            "produces",
            "required_keywords",
            "acceptance_criteria",
            "stop_conditions",
            "escalation_conditions",
            "exclusive_resources",
        ):
            value = slot.get(key)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise TemplateError(f"{slot_id}.{key} must be a list of strings")
        if len(slot["produces"]) != len(set(slot["produces"])):
            raise TemplateError(f"duplicate produces values in {slot_id}")
        if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", item) for item in slot["produces"]):
            raise TemplateError(f"invalid output name in {slot_id}")
        resources = slot["exclusive_resources"]
        if len(resources) != len(set(resources)) or any(not item.strip() for item in resources):
            raise TemplateError(
                f"{slot_id}.exclusive_resources must contain unique, non-empty names"
            )
        if not isinstance(slot.get("max_candidates"), int) or slot["max_candidates"] < 1:
            raise TemplateError(f"{slot_id}.max_candidates must be a positive integer")
        if not isinstance(slot.get("prompt"), str) or not slot["prompt"].strip():
            raise TemplateError(f"{slot_id}.prompt must be non-empty")
        by_id[slot_id] = slot

    for slot_id, slot in by_id.items():
        dependencies = slot["depends_on"]
        if len(dependencies) != len(set(dependencies)):
            raise TemplateError(f"duplicate dependencies in {slot_id}")
        if slot_id in dependencies:
            raise TemplateError(f"slot cannot depend on itself: {slot_id}")
        unknown = sorted(set(dependencies) - by_id.keys())
        if unknown:
            raise TemplateError(f"unknown dependencies in {slot_id}: {', '.join(unknown)}")
        for reference in slot["consumes"]:
            match = REFERENCE_RE.fullmatch(reference)
            if not match:
                raise TemplateError(f"invalid consumes reference in {slot_id}: {reference}")
            producer_id, output_name = match.groups()
            if producer_id not in by_id:
                raise TemplateError(f"unknown producer in {slot_id}: {producer_id}")
            if output_name not in by_id[producer_id]["produces"]:
                raise TemplateError(f"unknown producer output in {slot_id}: {reference}")
            if producer_id not in dependencies:
                raise TemplateError(f"consumed producer must be a dependency of {slot_id}: {reference}")

    topological_waves(slots)
    synthesis_id = template.get("synthesis_slot")
    if synthesis_id not in by_id or by_id[synthesis_id]["kind"] != "synthesis":
        raise TemplateError("synthesis_slot must reference a synthesis-kind slot")
    verification_dependencies = [
        dependency
        for dependency in by_id[synthesis_id]["depends_on"]
        if by_id[dependency]["kind"] == "verification"
    ]
    if not verification_dependencies:
        raise TemplateError("synthesis_slot must depend on at least one verification slot")


def _provided_keyword_values(slot: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
    keyword_values: dict[str, Any] = {}
    sources = [value for value in outputs.values() if isinstance(value, dict)]
    for keyword in slot["required_keywords"]:
        if keyword in outputs:
            keyword_values[keyword] = outputs[keyword]
            continue
        for source in sources:
            if keyword in source:
                keyword_values[keyword] = source[keyword]
                break
    return keyword_values


def compile_research(
    template_path: Path,
    inputs_path: Path | None,
    output_dir: Path,
    *,
    revision: int = 1,
) -> dict[str, Any]:
    if not isinstance(revision, int) or revision < 1:
        raise TemplateError("revision must be a positive integer")
    template = resolve_template(template_path)
    validate_template(template)
    inputs = read_json(inputs_path) if inputs_path else {}
    if not isinstance(inputs, dict):
        raise TemplateError("inputs must be a JSON object")

    input_locked = inputs.get("locked_context", {})
    provided_slots = inputs.get("provided_slots", {})
    if not isinstance(input_locked, dict) or not isinstance(provided_slots, dict):
        raise TemplateError("inputs.locked_context and inputs.provided_slots must be objects")

    locked_context = dict(template["locked_context"])
    unknown_locked = sorted(set(input_locked) - locked_context.keys())
    if unknown_locked:
        raise TemplateError(f"inputs cannot add unknown locked_context keys: {', '.join(unknown_locked)}")
    input_prohibited = input_locked.get("prohibited_actions")
    if input_prohibited is not None and not isinstance(input_prohibited, list):
        raise TemplateError("prohibited_actions must be a list before locked-context merge")
    locked_context.update(input_locked)
    if input_prohibited is not None:
        locked_context["prohibited_actions"] = list(
            dict.fromkeys([*template["locked_context"]["prohibited_actions"], *input_prohibited])
        )
    validate_locked_context(locked_context)

    slots = template["slots"]
    by_id = {slot["slot_id"]: slot for slot in slots}
    unknown_provided = sorted(set(provided_slots) - by_id.keys())
    if unknown_provided:
        raise TemplateError(f"inputs provide unknown slots: {', '.join(unknown_provided)}")

    for slot_id, outputs in provided_slots.items():
        if by_id[slot_id]["kind"] in {"verification", "synthesis", "locked"}:
            raise TemplateError(f"inputs cannot pre-complete {by_id[slot_id]['kind']} slot: {slot_id}")
        if not isinstance(outputs, dict):
            raise TemplateError(f"provided slot outputs must be an object: {slot_id}")
        missing_outputs = sorted(set(by_id[slot_id]["produces"]) - outputs.keys())
        if missing_outputs:
            raise TemplateError(f"provided slot {slot_id} missing outputs: {', '.join(missing_outputs)}")
        keyword_values = _provided_keyword_values(by_id[slot_id], outputs)
        missing_keywords = sorted(set(by_id[slot_id]["required_keywords"]) - keyword_values.keys())
        empty_keywords = sorted(
            key
            for key, value in keyword_values.items()
            if value is None or value == "" or value == []
        )
        if missing_keywords or empty_keywords:
            invalid = sorted(set(missing_keywords + empty_keywords))
            raise TemplateError(
                f"provided slot {slot_id} has missing or empty keyword values: {', '.join(invalid)}"
            )

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    resolved_template = dict(template)
    resolved_template["locked_context"] = locked_context
    template_hash = canonical_hash(resolved_template)
    write_json(output_dir / "resolved-template.json", resolved_template)

    slot_states: dict[str, str] = {}
    task_ids: list[str] = []
    links: list[dict[str, str]] = []

    for slot in slots:
        slot_id = slot["slot_id"]
        if slot_id in provided_slots:
            slot_states[slot_id] = "completed"
            proposal = {
                "schema_version": SCHEMA_VERSION,
                "slot_id": slot_id,
                "candidate_id": f"{slot_id}-PROVIDED",
                "filled_keywords": _provided_keyword_values(slot, provided_slots[slot_id]),
                "outputs": provided_slots[slot_id],
                "claims": [],
                "alternatives": [],
                "unknowns": [],
                "reviewed_slots": [],
                "new_slot_proposals": [],
                "status": "completed",
            }
            write_json(output_dir / "slots" / slot_id / "proposal.json", proposal)
        elif slot["kind"] == "human":
            slot_states[slot_id] = "needs_input"
        elif slot["kind"] == "locked":
            slot_states[slot_id] = "completed"
        elif slot["kind"] == "synthesis":
            slot_states[slot_id] = "blocked_dependency"
            task_ids.append(slot_id)
        else:
            slot_states[slot_id] = "pending"
            task_ids.append(slot_id)

    for slot in slots:
        for reference in slot["consumes"]:
            producer_id, output_name = reference.split(".", 1)
            links.append(
                {
                    "from_slot": producer_id,
                    "output": output_name,
                    "to_slot": slot["slot_id"],
                    "artifact": f"slots/{producer_id}/proposal.json#outputs/{output_name}",
                }
            )

    for slot in slots:
        slot_id = slot["slot_id"]
        if slot_id not in task_ids:
            continue
        task_inputs: list[dict[str, str]] = []
        for reference in slot["consumes"]:
            producer_id, output_name = reference.split(".", 1)
            artifact = f"slots/{producer_id}/proposal.json#outputs/{output_name}"
            task_inputs.append(
                {
                    "reference": reference,
                    "artifact": f"inbox/{slot_id}/{producer_id}.{output_name}.json",
                    "source_artifact": artifact,
                }
            )
        unresolved_dependencies = [
            dependency for dependency in slot["depends_on"] if slot_states[dependency] != "completed"
        ]
        status = "blocked_dependency" if unresolved_dependencies else "pending"
        if slot["kind"] == "synthesis":
            status = "blocked_dependency"
        task = {
            "schema_version": SCHEMA_VERSION,
            "task_id": slot_id,
            "slot_id": slot_id,
            "role": slot["kind"],
            "objective": slot["prompt"],
            "dependencies": slot["depends_on"],
            "inputs": task_inputs,
            "locked_context": locked_context,
            "produces": slot["produces"],
            "required_keywords": slot["required_keywords"],
            "acceptance_criteria": slot["acceptance_criteria"],
            "max_candidates": slot["max_candidates"],
            "stop_conditions": slot["stop_conditions"],
            "escalation_conditions": slot["escalation_conditions"],
            "exclusive_resources": slot["exclusive_resources"],
            "assigned_paths": [f"slots/{slot_id}/"],
            "expected_output": f"slots/{slot_id}/proposal.json",
            "unresolved_dependencies": unresolved_dependencies,
            "status": status,
            "attempts": 0,
            "max_attempts": DEFAULT_MAX_ATTEMPTS,
        }
        write_json(output_dir / "tasks" / slot_id / "task.json", task)

    task_waves = resource_safe_task_waves(slots, task_ids)

    state = {
        "schema_version": SCHEMA_VERSION,
        "template_id": template["template_id"],
        "template_revision": revision,
        "template_hash": template_hash,
        "locked_context_hash": canonical_hash(locked_context),
        "locked_context": locked_context,
        "slot_states": slot_states,
        "precompleted_slots": sorted(provided_slots),
        "task_ids": task_ids,
        "links": links,
        "waves": task_waves,
        "synthesis_slot": template["synthesis_slot"],
        "needs_input": sorted(slot_id for slot_id, status in slot_states.items() if status == "needs_input"),
        "status": "needs_input" if "needs_input" in slot_states.values() else "planning",
    }
    write_json(output_dir / "run-state.json", state)
    write_json(output_dir / "graph-expansion-proposals.json", {"schema_version": SCHEMA_VERSION, "proposals": []})
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Top-level template JSON")
    parser.add_argument("--inputs", type=Path, help="Known locked context and provided slot outputs")
    parser.add_argument("--output", type=Path, help="New run directory")
    parser.add_argument("--revision", type=int, default=1, help="Positive template revision number")
    parser.add_argument("--validate-only", action="store_true", help="Resolve and validate without compiling")
    args = parser.parse_args()

    try:
        template = resolve_template(args.template)
        validate_template(template)
        if args.validate_only:
            print(f"OK: valid template {template['template_id']} with {len(template['slots'])} slots")
            return 0
        if args.output is None:
            parser.error("--output is required unless --validate-only is used")
        state = compile_research(args.template, args.inputs, args.output, revision=args.revision)
    except (TemplateError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"OK: compiled {state['template_id']} to {args.output.resolve()} "
        f"({len(state['task_ids'])} tasks, {len(state['waves'])} waves)"
    )
    if state["needs_input"]:
        print("NEEDS_INPUT: " + ", ".join(state["needs_input"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
