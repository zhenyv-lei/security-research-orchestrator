#!/usr/bin/env python3
"""Validate security-research-orchestrator run artifacts with stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RUN_REQUIRED = {
    "run_id",
    "objective",
    "scope",
    "authorization_tier",
    "active_testing_approved",
    "allowed_actions",
    "prohibited_actions",
    "completion_criteria",
    "task_ids",
    "composition_review",
    "status",
    "updated_at",
}
TASK_REQUIRED = {
    "task_id",
    "role",
    "objective",
    "research_question",
    "dependencies",
    "assigned_paths",
    "inputs",
    "allowed_actions",
    "prohibited_actions",
    "expected_outputs",
    "acceptance_criteria",
    "evidence_requirements",
    "stop_conditions",
    "escalation_conditions",
    "status",
    "attempts",
    "max_attempts",
}
EVIDENCE_REQUIRED = {
    "evidence_id",
    "task_id",
    "kind",
    "locator",
    "observation",
    "supports",
    "sensitivity",
}
FINDING_REQUIRED = {
    "finding_id",
    "task_id",
    "title",
    "affected_scope",
    "preconditions",
    "observation",
    "interpretation",
    "impact",
    "evidence_ids",
    "verification_status",
    "remediation",
    "limitations",
}
TERMINAL_TASK_STATUSES = {
    "completed",
    "incomplete",
    "needs_input",
    "needs_authorization",
    "blocked_technical",
    "policy_blocked",
    "cancelled",
}
ALL_TASK_STATUSES = TERMINAL_TASK_STATUSES | {"pending", "running", "retryable_error"}
VERDICTS = {"verified", "corroborated", "candidate", "rejected", "blocked"}


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path}: {exc}")
    return None


def require_keys(data: Any, required: set[str], path: Path, errors: list[str]) -> None:
    if not isinstance(data, dict):
        errors.append(f"expected object: {path}")
        return
    missing = sorted(required - data.keys())
    if missing:
        errors.append(f"missing keys in {path}: {', '.join(missing)}")


def validate_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    state_path = run_dir / "run-state.json"
    state = load_json(state_path, errors)
    if state is None:
        return errors
    require_keys(state, RUN_REQUIRED, state_path, errors)

    task_ids = state.get("task_ids", []) if isinstance(state, dict) else []
    if not isinstance(task_ids, list) or any(not isinstance(item, str) for item in task_ids):
        errors.append("run-state.json task_ids must be a list of strings")
        return errors

    seen_evidence: set[str] = set()
    finding_refs: list[tuple[Path, list[str]]] = []

    for task_id in task_ids:
        task_dir = run_dir / "tasks" / task_id
        task_path = task_dir / "task.json"
        task = load_json(task_path, errors)
        if task is None:
            continue
        require_keys(task, TASK_REQUIRED, task_path, errors)
        if task.get("task_id") != task_id:
            errors.append(f"task ID mismatch in {task_path}")
        status = task.get("status")
        if status not in ALL_TASK_STATUSES:
            errors.append(f"invalid task status in {task_path}: {status}")
        dependencies = task.get("dependencies", [])
        if not isinstance(dependencies, list) or any(dep not in task_ids for dep in dependencies):
            errors.append(f"unknown or malformed dependency in {task_path}")
        attempts = task.get("attempts")
        max_attempts = task.get("max_attempts")
        if not isinstance(attempts, int) or not isinstance(max_attempts, int) or attempts > max_attempts:
            errors.append(f"invalid attempt budget in {task_path}")

        evidence_path = task_dir / "evidence.jsonl"
        if evidence_path.exists():
            for line_no, line in enumerate(evidence_path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid JSONL {evidence_path}:{line_no}: {exc}")
                    continue
                require_keys(record, EVIDENCE_REQUIRED, evidence_path, errors)
                evidence_id = record.get("evidence_id")
                if evidence_id in seen_evidence:
                    errors.append(f"duplicate evidence_id: {evidence_id}")
                if isinstance(evidence_id, str):
                    seen_evidence.add(evidence_id)
                if record.get("task_id") != task_id:
                    errors.append(f"evidence task mismatch at {evidence_path}:{line_no}")

        for finding_path in sorted(task_dir.glob("finding-*.json")):
            finding = load_json(finding_path, errors)
            if finding is None:
                continue
            require_keys(finding, FINDING_REQUIRED, finding_path, errors)
            if finding.get("task_id") != task_id:
                errors.append(f"finding task mismatch in {finding_path}")
            verdict = finding.get("verification_status")
            if verdict not in VERDICTS:
                errors.append(f"invalid finding verdict in {finding_path}: {verdict}")
            evidence_ids = finding.get("evidence_ids", [])
            if not isinstance(evidence_ids, list):
                errors.append(f"evidence_ids must be a list in {finding_path}")
            else:
                finding_refs.append((finding_path, evidence_ids))

    for finding_path, evidence_ids in finding_refs:
        missing = sorted(set(evidence_ids) - seen_evidence)
        if missing:
            errors.append(f"unknown evidence IDs in {finding_path}: {', '.join(missing)}")

    if state.get("status") == "completed":
        composition = state.get("composition_review", {})
        required_checks = {
            "individual_tasks_within_scope",
            "combined_output_within_scope",
            "unnecessary_operational_detail_removed",
            "sensitive_data_redacted",
        }
        if not isinstance(composition, dict) or any(composition.get(key) is not True for key in required_checks):
            errors.append("completed run requires all composition_review checks to be true")
        for task_id in task_ids:
            task = load_json(run_dir / "tasks" / task_id / "task.json", errors)
            if isinstance(task, dict) and task.get("status") not in TERMINAL_TASK_STATUSES:
                errors.append(f"completed run has non-terminal task: {task_id}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="Path containing run-state.json and tasks/")
    args = parser.parse_args()
    errors = validate_run(args.run_dir.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: valid run artifacts at {args.run_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
