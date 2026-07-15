#!/usr/bin/env python3
"""Validate security-research-orchestrator run artifacts with stdlib only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


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
RUN_V2_REQUIRED = {"schema_version", "policy_event_log"}
RUN_V3_REQUIRED = {"schema_version", "policy_event_log", "active_testing_approval", "conflicts_file", "preflight_exceptions"}
ACTIVE_APPROVAL_REQUIRED = {
    "approval_id",
    "approved",
    "approved_task_ids",
    "target",
    "owner",
    "authorization_source",
    "method_class",
    "time_window",
    "rate_limits",
    "mutation",
    "expected_traffic_or_side_effects",
    "containment",
    "rollback",
    "sensitive_data_exposure",
    "stop_conditions",
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
TASK_SAFETY_REQUIRED = {
    "purpose",
    "task_class",
    "capability_boundary",
    "resource_scope",
    "evidence_goal",
    "active_actions",
    "composition_dependencies",
    "safe_fallback",
}
TASK_SAFETY_V3_REQUIRED = {"approval_ref"}
POLICY_EVENT_REQUIRED = {
    "event_id",
    "task_id",
    "timestamp",
    "failure_class",
    "visible_message",
    "artifact_status",
    "decision",
    "fallback_task_id",
    "coverage_gap",
}
CONFLICT_REQUIRED = {
    "conflict_id",
    "task_ids",
    "normalized_claim",
    "evidence_ids",
    "status",
    "verifier_task_id",
    "resolution",
    "limitations",
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
    "verifier_task_id",
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
TASK_CLASSES = {
    "context_map",
    "passive_research",
    "state_inventory",
    "boundary_trace",
    "control_review",
    "active_validation",
    "evidence_normalization",
    "risk_ranking",
    "verification",
    "mitigation",
    "synthesis",
}
CAPABILITY_BOUNDARIES = {"non_operational", "active_authorized"}
AUTHORIZATION_TIERS = {"A0", "A1", "A2"}
CONFLICT_STATUSES = {"open", "resolved", "unresolved"}
TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
TEXT_OUTPUT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}


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


def resolve_run_path(run_dir: Path, value: Any, field: str, errors: list[str]) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty path string")
        return None
    relative = Path(value)
    if not relative.parts or relative == Path(".") or relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{field} escapes run directory: {value}")
        return None
    run_root = run_dir.resolve()
    resolved = (run_root / relative).resolve()
    if resolved != run_root and run_root not in resolved.parents:
        errors.append(f"{field} escapes run directory: {value}")
        return None
    return resolved


def expected_output_path(
    run_dir: Path,
    task_id: str,
    task: dict[str, Any],
    value: Any,
    errors: list[str],
) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"invalid expected output for {task_id}")
        return None
    relative = Path(value)
    if not relative.parts or relative == Path(".") or relative.is_absolute() or ".." in relative.parts:
        errors.append(f"expected output escapes run directory for {task_id}: {value}")
        return None
    own_root = Path("tasks") / task_id
    task_class = task.get("safety", {}).get("task_class")
    if relative.parts[0] == "tasks":
        if relative != own_root and own_root not in relative.parents:
            errors.append(f"expected output is outside output ownership for {task_id}: {value}")
            return None
        candidate = relative
        allowed_root = own_root
    elif relative.parts[0] == "final":
        if task_class != "synthesis":
            errors.append(f"expected output is outside output ownership for {task_id}: {value}")
            return None
        candidate = relative
        allowed_root = Path("final")
    else:
        candidate = own_root / relative
        allowed_root = own_root

    assigned_paths = task.get("assigned_paths", [])
    if not isinstance(assigned_paths, list) or not any(
        isinstance(assigned, str)
        and (
            Path(assigned) == candidate
            or Path(assigned) in candidate.parents
            or candidate in Path(assigned).parents
        )
        for assigned in assigned_paths
    ):
        errors.append(f"expected output is outside assigned ownership for {task_id}: {value}")
        return None

    output_path = resolve_run_path(run_dir, str(candidate), f"expected output for {task_id}", errors)
    if output_path is None:
        return None
    run_root = run_dir.resolve()
    lexical_root = run_root / allowed_root
    resolved_root = lexical_root.resolve()
    if resolved_root != lexical_root or (
        output_path != resolved_root and resolved_root not in output_path.parents
    ):
        errors.append(f"expected output is outside output ownership for {task_id}: {value}")
        return None
    return output_path


def output_has_content(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    if path.suffix.lower() not in TEXT_OUTPUT_SUFFIXES:
        return True
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except UnicodeDecodeError:
        return False


def validate_completed_task_outputs(
    run_dir: Path,
    task_id: str,
    task: dict[str, Any],
    errors: list[str],
) -> None:
    outputs = task.get("expected_outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append(f"completed task has no expected_outputs contract: {task_id}")
        return
    if any(not isinstance(output, str) for output in outputs) or len(outputs) != len(set(outputs)):
        errors.append(f"completed task expected_outputs must be unique strings: {task_id}")
        return
    for output in outputs:
        output_path = expected_output_path(run_dir, task_id, task, output, errors)
        if output_path is not None and not output_has_content(output_path):
            errors.append(f"completed task output is missing or empty: {task_id}:{output}")


def validate_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    state_path = run_dir / "run-state.json"
    state = load_json(state_path, errors)
    if state is None:
        return errors
    require_keys(state, RUN_REQUIRED, state_path, errors)

    schema_version = state.get("schema_version", 1) if isinstance(state, dict) else 1
    if not isinstance(schema_version, int) or schema_version < 1:
        errors.append("run-state.json schema_version must be a positive integer")
        schema_version = 1
    if schema_version >= 2:
        require_keys(state, RUN_V2_REQUIRED, state_path, errors)
        policy_event_log = state.get("policy_event_log")
        if not isinstance(policy_event_log, str) or not policy_event_log.strip():
            errors.append("v2 run-state.json policy_event_log must be a non-empty path string")
    if schema_version >= 3:
        require_keys(state, RUN_V3_REQUIRED, state_path, errors)
        if state.get("authorization_tier") not in AUTHORIZATION_TIERS:
            errors.append("v3 authorization_tier must be one of A0, A1, or A2")
        active_approval = state.get("active_testing_approval")
        require_keys(active_approval, ACTIVE_APPROVAL_REQUIRED, state_path, errors)
        if isinstance(active_approval, dict):
            approved = active_approval.get("approved")
            if not isinstance(approved, bool) or not isinstance(state.get("active_testing_approved"), bool):
                errors.append("active testing approval flags must be booleans")
            if approved is not state.get("active_testing_approved"):
                errors.append("active_testing_approval.approved must match active_testing_approved")
            stop_conditions = active_approval.get("stop_conditions")
            if not isinstance(stop_conditions, list) or any(not isinstance(item, str) for item in stop_conditions):
                errors.append("active_testing_approval.stop_conditions must be a list of strings")
            approved_task_ids = active_approval.get("approved_task_ids")
            if not isinstance(approved_task_ids, list) or any(not isinstance(item, str) for item in approved_task_ids):
                errors.append("active_testing_approval.approved_task_ids must be a list of strings")
                approved_task_ids = []
            elif len(approved_task_ids) != len(set(approved_task_ids)):
                errors.append("active_testing_approval.approved_task_ids must not contain duplicates")
            if approved is True:
                tier = state.get("authorization_tier", "")
                if tier not in {"A1", "A2"}:
                    errors.append("active testing requires authorization tier A1 or A2")
                for field in ACTIVE_APPROVAL_REQUIRED - {"approved", "approved_task_ids", "stop_conditions"}:
                    value = active_approval.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"approved active testing requires non-empty {field}")
                if not stop_conditions:
                    errors.append("approved active testing requires at least one stop condition")
                if not approved_task_ids:
                    errors.append("approved active testing requires approved_task_ids")
            elif approved is False and approved_task_ids:
                errors.append("unapproved active testing packet must not list approved_task_ids")
            preflight_exceptions = state.get("preflight_exceptions")
            if not isinstance(preflight_exceptions, list) or any(
                not isinstance(item, dict)
                or not isinstance(item.get("warning"), str)
                or not item.get("warning", "").strip()
                or not isinstance(item.get("rationale"), str)
                or not item.get("rationale", "").strip()
                or not isinstance(item.get("approved_by"), str)
                or not item.get("approved_by", "").strip()
                or not isinstance(item.get("timestamp"), str)
                or not item.get("timestamp", "").strip()
                for item in preflight_exceptions
            ):
                errors.append("v3 preflight_exceptions must contain warning, rationale, approved_by, and timestamp")

    raw_task_ids = state.get("task_ids", []) if isinstance(state, dict) else []
    if not isinstance(raw_task_ids, list):
        errors.append("run-state.json task_ids must be a list of strings")
        return errors
    task_ids: list[str] = []
    seen_task_ids: set[str] = set()
    for item in raw_task_ids:
        if (
            not isinstance(item, str)
            or not TASK_ID_PATTERN.fullmatch(item)
            or ".." in item
        ):
            errors.append(f"invalid task ID in run-state.json: {item!r}")
            continue
        if item in seen_task_ids:
            errors.append(f"duplicate task ID in run-state.json: {item}")
            continue
        seen_task_ids.add(item)
        task_ids.append(item)

    seen_evidence: set[str] = set()
    evidence_owners: dict[str, str] = {}
    finding_refs: list[tuple[Path, list[str], str, str, Any]] = []
    policy_blocked_tasks: set[str] = set()
    task_records: dict[str, dict[str, Any]] = {}
    run_root = run_dir.resolve()

    for task_id in task_ids:
        task_dir = run_root / "tasks" / task_id
        if task_dir.resolve() != task_dir:
            errors.append(f"task directory escapes run ownership for task ID: {task_id}")
            continue
        task_path = task_dir / "task.json"
        task = load_json(task_path, errors)
        if task is None:
            continue
        task_records[task_id] = task
        require_keys(task, TASK_REQUIRED, task_path, errors)
        if task.get("task_id") != task_id:
            errors.append(f"task ID mismatch in {task_path}")
        status = task.get("status")
        if status not in ALL_TASK_STATUSES:
            errors.append(f"invalid task status in {task_path}: {status}")
        if status == "policy_blocked":
            policy_blocked_tasks.add(task_id)
        dependencies = task.get("dependencies", [])
        if not isinstance(dependencies, list) or any(dep not in task_ids for dep in dependencies):
            errors.append(f"unknown or malformed dependency in {task_path}")
        attempts = task.get("attempts")
        max_attempts = task.get("max_attempts")
        if not isinstance(attempts, int) or not isinstance(max_attempts, int) or attempts > max_attempts:
            errors.append(f"invalid attempt budget in {task_path}")
        fallback_of = task.get("fallback_of")
        if fallback_of is not None and (
            not isinstance(fallback_of, str) or fallback_of not in task_ids
        ):
            errors.append(f"unknown or malformed fallback_of in {task_path}")

        if schema_version >= 2:
            safety = task.get("safety")
            require_keys(safety, TASK_SAFETY_REQUIRED, task_path, errors)
            if schema_version >= 3:
                require_keys(safety, TASK_SAFETY_V3_REQUIRED, task_path, errors)
            if isinstance(safety, dict):
                task_class = safety.get("task_class")
                boundary = safety.get("capability_boundary")
                resource_scope = safety.get("resource_scope")
                evidence_goal = safety.get("evidence_goal")
                active_actions = safety.get("active_actions")
                approval_ref = safety.get("approval_ref")
                composition_dependencies = safety.get("composition_dependencies")

                if safety.get("purpose") != "defensive":
                    errors.append(f"v2 task purpose must be defensive in {task_path}")
                if task_class not in TASK_CLASSES:
                    errors.append(f"invalid task_class in {task_path}: {task_class}")
                if boundary not in CAPABILITY_BOUNDARIES:
                    errors.append(f"invalid capability_boundary in {task_path}: {boundary}")
                if not isinstance(resource_scope, list) or any(not isinstance(item, str) for item in resource_scope):
                    errors.append(f"resource_scope must be a list of strings in {task_path}")
                if not isinstance(evidence_goal, str) or not evidence_goal.strip():
                    errors.append(f"evidence_goal must be non-empty in {task_path}")
                if not isinstance(active_actions, list) or any(not isinstance(item, str) for item in active_actions):
                    errors.append(f"active_actions must be a list of strings in {task_path}")
                elif boundary == "non_operational" and active_actions:
                    errors.append(f"non_operational task has active_actions in {task_path}")
                elif active_actions and state.get("active_testing_approved") is not True:
                    errors.append(f"task has active_actions without run approval in {task_path}")
                if task_class == "active_validation" and boundary != "active_authorized":
                    errors.append(f"active_validation task must use active_authorized boundary in {task_path}")
                if boundary == "active_authorized" and task_class != "active_validation":
                    errors.append(f"active_authorized boundary requires active_validation in {task_path}")
                if task_class == "active_validation" and not active_actions:
                    errors.append(f"active_validation task requires active_actions in {task_path}")
                if boundary == "active_authorized" and state.get("active_testing_approved") is not True:
                    errors.append(f"active_authorized task lacks run approval in {task_path}")
                if schema_version >= 3 and boundary == "active_authorized":
                    approval = state.get("active_testing_approval", {})
                    if approval_ref != approval.get("approval_id"):
                        errors.append(f"active task approval_ref mismatch in {task_path}")
                    if task_id not in approval.get("approved_task_ids", []):
                        errors.append(f"active task absent from approved_task_ids in {task_path}")
                if schema_version >= 3 and boundary == "non_operational" and approval_ref is not None:
                    errors.append(f"non_operational task must have null approval_ref in {task_path}")
                if not isinstance(composition_dependencies, list) or any(
                    dep not in task_ids for dep in composition_dependencies
                ):
                    errors.append(f"unknown or malformed composition dependency in {task_path}")

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
                if not isinstance(evidence_id, str) or not evidence_id.strip():
                    errors.append(f"invalid evidence_id at {evidence_path}:{line_no}")
                elif evidence_id in seen_evidence:
                    errors.append(f"duplicate evidence_id: {evidence_id}")
                if isinstance(evidence_id, str) and evidence_id.strip():
                    seen_evidence.add(evidence_id)
                    evidence_owners.setdefault(evidence_id, task_id)
                if record.get("task_id") != task_id:
                    errors.append(f"evidence task mismatch at {evidence_path}:{line_no}")
                for field in ("locator", "observation"):
                    value = record.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"evidence {field} must be non-empty at {evidence_path}:{line_no}")
                supports = record.get("supports")
                if not isinstance(supports, list) or not supports or any(
                    not isinstance(item, str) or not item.strip() for item in supports
                ):
                    errors.append(f"evidence supports must be a non-empty list of strings at {evidence_path}:{line_no}")

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
            if not isinstance(evidence_ids, list) or any(
                not isinstance(evidence_id, str) or not evidence_id.strip() for evidence_id in evidence_ids
            ):
                errors.append(f"evidence_ids must be a list of strings in {finding_path}")
            else:
                if not evidence_ids:
                    errors.append(f"finding must cite at least one evidence ID in {finding_path}")
                finding_refs.append(
                    (
                        finding_path,
                        evidence_ids,
                        task_id,
                        verdict,
                        finding.get("verifier_task_id"),
                    )
                )

    for task_id, task in task_records.items():
        if task.get("status") == "completed":
            validate_completed_task_outputs(run_root, task_id, task, errors)

    if schema_version >= 3:
        active_approval = state.get("active_testing_approval", {})
        if isinstance(active_approval, dict) and active_approval.get("approved") is True:
            approval_id = active_approval.get("approval_id")
            for approved_task_id in active_approval.get("approved_task_ids", []):
                approved_task = task_records.get(approved_task_id)
                if approved_task is None:
                    errors.append(f"approved_task_ids references unknown task: {approved_task_id}")
                    continue
                safety = approved_task.get("safety", {})
                if (
                    safety.get("task_class") != "active_validation"
                    or safety.get("capability_boundary") != "active_authorized"
                    or safety.get("approval_ref") != approval_id
                ):
                    errors.append(
                        f"approved_task_ids entry is not a matching active_validation task: {approved_task_id}"
                    )

    for finding_path, evidence_ids, origin_task_id, verdict, verifier_task_id in finding_refs:
        missing = sorted(set(evidence_ids) - seen_evidence)
        if missing:
            errors.append(f"unknown evidence IDs in {finding_path}: {', '.join(missing)}")
        if verdict in {"verified", "corroborated"}:
            verifier_task = task_records.get(verifier_task_id) if isinstance(verifier_task_id, str) else None
            verifier_evidence = [
                evidence_id
                for evidence_id in evidence_ids
                if evidence_owners.get(evidence_id) == verifier_task_id
            ]
            if (
                verifier_task is None
                or verifier_task_id == origin_task_id
                or verifier_task.get("safety", {}).get("task_class") != "verification"
                or verifier_task.get("status") != "completed"
                or origin_task_id not in verifier_task.get("dependencies", [])
                or not verifier_evidence
            ):
                errors.append(
                    f"{verdict} finding requires an independent verifier with completed artifacts and cited verifier evidence: "
                    f"{finding_path}"
                )

    if schema_version >= 2:
        policy_event_tasks: set[str] = set()
        seen_policy_event_ids: set[str] = set()
        policy_fallback_links: list[tuple[str, str]] = []
        policy_event_path = resolve_run_path(
            run_dir,
            state.get("policy_event_log", "policy-events.jsonl"),
            "policy_event_log",
            errors,
        )
        if policy_event_path is not None and policy_event_path.exists():
            for line_no, line in enumerate(policy_event_path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid JSONL {policy_event_path}:{line_no}: {exc}")
                    continue
                require_keys(event, POLICY_EVENT_REQUIRED, policy_event_path, errors)
                event_id = event.get("event_id")
                if not isinstance(event_id, str) or not event_id.strip():
                    errors.append(f"invalid policy event ID at {policy_event_path}:{line_no}")
                elif event_id in seen_policy_event_ids:
                    errors.append(f"duplicate policy event ID: {event_id}")
                else:
                    seen_policy_event_ids.add(event_id)
                event_task = event.get("task_id")
                if event_task not in task_ids:
                    errors.append(f"unknown policy event task at {policy_event_path}:{line_no}: {event_task}")
                if event.get("failure_class") != "policy" or event.get("decision") != "policy_blocked":
                    errors.append(f"invalid policy event class/decision at {policy_event_path}:{line_no}")
                elif event_task in task_ids:
                    policy_event_tasks.add(event_task)
                    if schema_version >= 3 and task_records.get(event_task, {}).get("status") != "policy_blocked":
                        errors.append(f"policy event task is not policy_blocked at {policy_event_path}:{line_no}")
                if schema_version >= 3:
                    for field in ("timestamp", "visible_message", "coverage_gap"):
                        value = event.get(field)
                        if not isinstance(value, str) or not value.strip():
                            errors.append(f"policy event {field} must be non-empty at {policy_event_path}:{line_no}")
                if not isinstance(event.get("artifact_status"), list) or any(
                    not isinstance(item, str) for item in event.get("artifact_status", [])
                ):
                    errors.append(f"artifact_status must be a list of strings at {policy_event_path}:{line_no}")
                fallback_task = event.get("fallback_task_id")
                if fallback_task is not None:
                    if not isinstance(fallback_task, str):
                        errors.append(f"malformed fallback task at {policy_event_path}:{line_no}")
                    elif fallback_task not in task_records:
                        errors.append(f"unknown fallback task at {policy_event_path}:{line_no}: {fallback_task}")
                    elif task_records[fallback_task].get("fallback_of") != event_task:
                        errors.append(f"fallback linkage mismatch at {policy_event_path}:{line_no}")
                    else:
                        policy_fallback_links.append((event_task, fallback_task))
        missing_events = sorted(policy_blocked_tasks - policy_event_tasks)
        if missing_events:
            errors.append(f"policy_blocked tasks lack policy events: {', '.join(missing_events)}")
        if schema_version >= 3:
            for fallback_id, fallback_task in task_records.items():
                original_id = fallback_task.get("fallback_of")
                if original_id is None:
                    continue
                count = policy_fallback_links.count((original_id, fallback_id))
                if count != 1:
                    errors.append(f"fallback task {fallback_id} must be linked by exactly one policy event")

    if schema_version >= 3:
        conflict_path = resolve_run_path(run_dir, state.get("conflicts_file"), "conflicts_file", errors)
        if conflict_path is not None:
            conflicts = load_json(conflict_path, errors)
            if conflicts is not None and not isinstance(conflicts, list):
                errors.append(f"expected array: {conflict_path}")
            elif isinstance(conflicts, list):
                seen_conflict_ids: set[str] = set()
                for index, conflict in enumerate(conflicts):
                    require_keys(conflict, CONFLICT_REQUIRED, conflict_path, errors)
                    if not isinstance(conflict, dict):
                        continue
                    conflict_id = conflict.get("conflict_id")
                    if not isinstance(conflict_id, str) or not conflict_id.strip() or conflict_id in seen_conflict_ids:
                        errors.append(f"invalid or duplicate conflict_id at {conflict_path}:{index + 1}")
                    else:
                        seen_conflict_ids.add(conflict_id)
                    conflict_tasks = conflict.get("task_ids")
                    if not isinstance(conflict_tasks, list) or len(conflict_tasks) < 2 or any(
                        task_id not in task_ids for task_id in conflict_tasks
                    ):
                        errors.append(f"conflict task_ids must reference at least two tasks at {conflict_path}:{index + 1}")
                        conflict_tasks = []
                    normalized_claim = conflict.get("normalized_claim")
                    if not isinstance(normalized_claim, str) or not normalized_claim.strip():
                        errors.append(f"conflict normalized_claim must be non-empty at {conflict_path}:{index + 1}")
                    conflict_evidence = conflict.get("evidence_ids")
                    if not isinstance(conflict_evidence, list) or any(
                        not isinstance(item, str) or not item.strip() for item in conflict_evidence
                    ):
                        errors.append(f"conflict evidence_ids must be a list of strings at {conflict_path}:{index + 1}")
                        conflict_evidence = []
                    unknown_conflict_evidence = sorted(set(conflict_evidence) - seen_evidence)
                    if unknown_conflict_evidence:
                        errors.append(
                            f"unknown conflict evidence IDs at {conflict_path}:{index + 1}: "
                            + ", ".join(unknown_conflict_evidence)
                        )
                    status = conflict.get("status")
                    if status not in CONFLICT_STATUSES:
                        errors.append(f"invalid conflict status at {conflict_path}:{index + 1}: {status}")
                    verifier = conflict.get("verifier_task_id")
                    if verifier is not None and not isinstance(verifier, str):
                        errors.append(f"malformed conflict verifier at {conflict_path}:{index + 1}")
                    elif verifier is not None and verifier not in task_ids:
                        errors.append(f"unknown conflict verifier at {conflict_path}:{index + 1}")
                    if status == "resolved":
                        if not str(conflict.get("resolution", "")).strip():
                            errors.append(f"resolved conflict lacks resolution at {conflict_path}:{index + 1}")
                        if not conflict_evidence:
                            errors.append(f"resolved conflict evidence_ids must be non-empty at {conflict_path}:{index + 1}")
                        verifier_task = task_records.get(verifier) if isinstance(verifier, str) else None
                        verifier_dependencies = set(verifier_task.get("dependencies", [])) if verifier_task else set()
                        if (
                            verifier_task is None
                            or verifier in conflict_tasks
                            or verifier_task.get("safety", {}).get("task_class") != "verification"
                            or verifier_task.get("status") != "completed"
                            or not set(conflict_tasks).issubset(verifier_dependencies)
                        ):
                            errors.append(
                                f"resolved conflict requires an independent verifier that depends on every conflicting task at "
                                f"{conflict_path}:{index + 1}"
                            )
                        if not any(evidence_owners.get(evidence_id) == verifier for evidence_id in conflict_evidence):
                            errors.append(
                                f"resolved conflict requires verifier-owned evidence at {conflict_path}:{index + 1}"
                            )
                    if status == "unresolved" and not conflict.get("limitations"):
                        errors.append(f"unresolved conflict lacks limitations at {conflict_path}:{index + 1}")
                    if state.get("status") == "completed" and status == "open":
                        errors.append(f"completed run has open conflict: {conflict_id}")

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
        if not seen_evidence:
            errors.append("completed run has no evidence records")
        final_report = resolve_run_path(run_dir, "final/final-report.md", "final report", errors)
        if final_report is not None and (
            not final_report.is_file() or not final_report.read_text(encoding="utf-8").strip()
        ):
            errors.append("completed run requires non-empty final/final-report.md")
        for task_id in task_ids:
            task = task_records.get(task_id)
            if not isinstance(task, dict):
                continue
            if task.get("status") not in TERMINAL_TASK_STATUSES:
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
