#!/usr/bin/env python3
"""Preflight security-research task graphs before worker dispatch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from validate_run import validate_run


SINGLE_RESOURCE_CLASSES = {"state_inventory", "boundary_trace"}
ACTIVE_ACTION_PATTERN = re.compile(
    r"\b(run|execute|simulate|probe|scan|measure|instrument|mutate|flash|program|access)\b",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"expected object: {path}")
    return data


def overlaps(left: str, right: str) -> bool:
    left_path = Path(left)
    right_path = Path(right)
    return left_path == right_path or left_path in right_path.parents or right_path in left_path.parents


def has_dependency_path(task_id: str, context_ids: set[str], tasks: dict[str, dict], seen: Optional[set[str]] = None) -> bool:
    if task_id in context_ids:
        return True
    seen = set() if seen is None else seen
    if task_id in seen:
        return False
    seen.add(task_id)
    return any(has_dependency_path(dep, context_ids, tasks, seen) for dep in tasks[task_id].get("dependencies", []))


def dependency_cycles(tasks: dict[str, dict]) -> list[str]:
    state = {task_id: 0 for task_id in tasks}
    stack: list[str] = []
    cycles: list[str] = []

    def visit(task_id: str) -> None:
        if state[task_id] == 1:
            start = stack.index(task_id)
            cycles.append(" -> ".join(stack[start:] + [task_id]))
            return
        if state[task_id] == 2:
            return
        state[task_id] = 1
        stack.append(task_id)
        for dependency in tasks[task_id].get("dependencies", []):
            visit(dependency)
        stack.pop()
        state[task_id] = 2

    for task_id in tasks:
        visit(task_id)
    return cycles


def is_owned_path(run_dir: Path, task_id: str, task_class: str, assigned_path: str) -> bool:
    path = Path(assigned_path)
    if path.is_absolute() or ".." in path.parts:
        return False
    roots = [Path("tasks") / task_id]
    if task_class == "synthesis":
        roots.append(Path("final"))
    if not any(path == root or root in path.parents for root in roots):
        return False
    run_root = run_dir.resolve()
    resolved = (run_root / path).resolve()
    for root in roots:
        lexical_root = run_root / root
        resolved_root = lexical_root.resolve()
        if resolved_root != lexical_root:
            continue
        if resolved_root != run_root and run_root not in resolved_root.parents:
            continue
        if resolved == resolved_root or resolved_root in resolved.parents:
            return True
    return False


def preflight(run_dir: Path, strict_v2: bool = False, strict_v3: bool = False) -> tuple[list[str], list[str]]:
    errors = validate_run(run_dir)
    warnings: list[str] = []
    if errors:
        return errors, warnings

    state = load_json(run_dir / "run-state.json")
    schema_version = state.get("schema_version", 1)
    if schema_version < 3:
        errors.append("dispatch requires schema v3; migrate legacy run artifacts before worker dispatch")
        return errors, warnings

    task_ids = state["task_ids"]
    tasks = {task_id: load_json(run_dir / "tasks" / task_id / "task.json") for task_id in task_ids}
    composition = state.get("composition_review", {})
    if composition.get("individual_tasks_within_scope") is not True:
        errors.append("dispatch requires individual_tasks_within_scope=true")
    if composition.get("combined_output_within_scope") is not True:
        errors.append("dispatch requires combined_output_within_scope=true")
    for cycle in dependency_cycles(tasks):
        errors.append(f"dependency cycle: {cycle}")
    context_ids = {
        task_id for task_id, task in tasks.items() if task.get("safety", {}).get("task_class") == "context_map"
    }
    if not context_ids:
        errors.append("task graph has no context_map task")

    owners: list[tuple[str, str]] = []
    for task_id, task in tasks.items():
        safety = task["safety"]
        task_class = safety["task_class"]
        resource_scope = safety["resource_scope"]

        if not isinstance(task.get("objective"), str) or not task["objective"].strip():
            errors.append(f"{task_id} has an empty objective")
        if not isinstance(task.get("research_question"), str) or not task["research_question"].strip():
            errors.append(f"{task_id} has an empty research_question")
        if not isinstance(task.get("assigned_paths"), list) or not task["assigned_paths"] or any(
            not isinstance(path, str) or not path.strip() for path in task.get("assigned_paths", [])
        ):
            errors.append(f"{task_id} must own at least one assigned path")

        if task_class in SINGLE_RESOURCE_CLASSES and len(resource_scope) != 1:
            errors.append(f"{task_id} {task_class} must name exactly one resource_scope item")
        if task_class in {"context_map", "state_inventory", "boundary_trace", "control_review"} and not task["inputs"]:
            errors.append(f"{task_id} has no stable input artifacts")
        if not task["expected_outputs"]:
            errors.append(f"{task_id} has no expected outputs")
        if safety.get("capability_boundary") == "non_operational":
            for action in task.get("allowed_actions", []):
                if isinstance(action, str) and ACTIVE_ACTION_PATTERN.search(action):
                    warnings.append(
                        f"{task_id} non_operational allowed_action may describe active work: {action}"
                    )
        if task_id not in context_ids and context_ids and not has_dependency_path(task_id, context_ids, tasks):
            warnings.append(f"{task_id} has no dependency path to a context_map task")

        fallback_of = task.get("fallback_of")
        if fallback_of is not None:
            if fallback_of not in tasks:
                errors.append(f"{task_id} fallback_of references unknown task {fallback_of}")
            elif tasks[fallback_of].get("status") != "policy_blocked":
                errors.append(f"{task_id} fallback_of task {fallback_of} is not policy_blocked")

        for assigned_path in task["assigned_paths"]:
            if not is_owned_path(run_dir, task_id, task_class, assigned_path):
                errors.append(f"assigned path escapes task ownership: {task_id}:{assigned_path}")
            for other_path, owner in owners:
                if overlaps(assigned_path, other_path):
                    errors.append(f"assigned path overlap: {task_id}:{assigned_path} and {owner}:{other_path}")
            owners.append((assigned_path, task_id))

    if warnings and schema_version >= 3:
        approved_warnings = {
            item["warning"] for item in state.get("preflight_exceptions", []) if isinstance(item, dict) and "warning" in item
        }
        for warning in warnings:
            if warning not in approved_warnings:
                errors.append(f"unapproved preflight warning: {warning}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument(
        "--strict-v3",
        action="store_true",
        help="Explicitly request the current dispatch schema (already enforced by default)",
    )
    args = parser.parse_args()

    try:
        errors, warnings = preflight(args.run_dir.resolve(), strict_v3=args.strict_v3)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: dispatch preflight passed at {args.run_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
