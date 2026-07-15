#!/usr/bin/env python3
"""Validate security-research-orchestrator run artifacts with stdlib only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from datetime import datetime
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
RUN_V3_REQUIRED = {
    "schema_version",
    "research_profile",
    "authorization",
    "policy_event_log",
    "active_testing_approval",
    "conflicts_file",
    "preflight_exceptions",
    "task_graph",
    "artifact_roots",
    "resume",
}
MICROARCH_RUN_REQUIRED = {"authorization"}
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
TASK_V3_REQUIRED = {"schema_version"}
MICROARCH_TASK_REQUIRED = {"schema_version", "phase", "execution_mode", "target_snapshot", "resource_requirements"}
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
EXPERIMENT_REQUIRED = {
    "schema_version",
    "experiment_id",
    "task_id",
    "approval_ref",
    "revision",
    "hypothesis",
    "variables",
    "target_snapshot",
    "workloads",
    "controls",
    "observables",
    "seed_policy",
    "cells",
    "command_plan",
    "expected_artifacts",
    "acceptance_criteria",
    "inconclusive_criteria",
    "resource_exhaustion_criteria",
    "stop_conditions",
    "resource_budget",
    "status",
}
ARTIFACT_REQUIRED = {
    "schema_version",
    "artifact_id",
    "producer_task_id",
    "experiment_id",
    "experiment_revision",
    "experiment_contract_hash",
    "cell_id",
    "kind",
    "path",
    "hash",
    "target_snapshot",
    "tool_versions",
    "workload_ids",
    "seed",
    "repetition_index",
    "generated_at",
    "sensitivity",
    "retention",
}
FINDING_V3_REQUIRED = {
    "counter_evidence",
    "false_positive_hypotheses",
    "severity",
    "severity_rationale",
    "confidence",
    "confidence_rationale",
    "regression_checks",
    "redactions",
}
CELL_REQUIRED = {"cell_id", "label", "variable_assignments"}
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
RUN_STATUSES = {"planning", "running", "paused", "completed", "cancelled"}
EXPERIMENT_STATUSES = {
    "planned",
    "calibrating",
    "running",
    "completed",
    "inconclusive",
    "blocked_technical",
    "policy_blocked",
    "cancelled",
}
TERMINAL_EXPERIMENT_STATUSES = {
    "completed",
    "inconclusive",
    "blocked_technical",
    "policy_blocked",
    "cancelled",
}
TASK_EXPERIMENT_STATUSES = {
    "pending": {"planned"},
    "running": EXPERIMENT_STATUSES,
    "retryable_error": {"planned", "blocked_technical"},
    "completed": TERMINAL_EXPERIMENT_STATUSES,
    "incomplete": {"inconclusive", "blocked_technical", "policy_blocked", "cancelled"},
    "needs_input": {"planned", "cancelled"},
    "needs_authorization": {"planned", "cancelled"},
    "blocked_technical": {"blocked_technical", "inconclusive", "cancelled"},
    "policy_blocked": {"policy_blocked", "cancelled"},
    "cancelled": {"cancelled"},
}
VERDICTS = {"verified", "corroborated", "candidate", "rejected", "blocked"}
FINDING_SEVERITIES = {"critical", "high", "medium", "low", "informational", "undetermined"}
FINDING_CONFIDENCES = {"high", "medium", "low"}
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
SCHEMA_VERSIONS = {1, 2, 3}
RESEARCH_PROFILES = {
    "source-code-security-audit",
    "cve-supply-chain-investigation",
    "threat-modeling-architecture-review",
    "microarchitecture-security",
}
CONFLICT_STATUSES = {"open", "resolved", "unresolved"}
TARGET_CLASSES = {"static-rtl", "formal-model", "cycle-simulator", "fpga", "silicon", "software"}
MICROARCH_EXECUTION_MODES = {
    "read-only",
    "passive-research",
    "local-simulation",
    "formal-execution",
    "fpga",
    "silicon",
}
EXECUTION_TARGET_CLASSES = {
    "local-simulation": {"cycle-simulator", "software"},
    "formal-execution": {"formal-model"},
    "fpga": {"fpga"},
    "silicon": {"silicon"},
}
TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
EXPERIMENT_ID_PATTERN = re.compile(r"EXP-[A-Za-z0-9][A-Za-z0-9._-]{0,123}\Z")
CELL_ID_PATTERN = re.compile(r"CELL-[A-Za-z0-9][A-Za-z0-9._-]{0,122}\Z")
VARIABLE_ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}\Z")
TEXT_OUTPUT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
GENERATED_EVIDENCE_KINDS = {
    "build_log",
    "simulation_log",
    "difftest",
    "counter",
    "trace",
    "waveform",
    "checkpoint",
}
ARTIFACT_KINDS = GENERATED_EVIDENCE_KINDS | {
    "analysis",
    "binary",
    "config_snapshot",
    "coverage",
    "formal_log",
    "metrics",
    "report",
}
SENSITIVITY_LEVELS = {"public", "internal", "confidential", "restricted"}
RETENTION_POLICIES = {"keep", "review", "delete-after-run", "delete-after-review"}
EVIDENCE_KINDS = {
    "analysis",
    "authoritative_record",
    "build_log",
    "checkpoint",
    "configuration",
    "counter",
    "difftest",
    "formal_log",
    "report",
    "secondary_commentary",
    "simulation_log",
    "source_code",
    "standard",
    "test_output",
    "trace",
    "vendor_advisory",
    "waveform",
}
TASK_ROLES = {"context", "discovery", "analysis", "verification", "mitigation", "synthesis"}
TASK_CLASS_ROLES = {
    "context_map": "context",
    "verification": "verification",
    "mitigation": "mitigation",
    "synthesis": "synthesis",
}
COMPOSITION_REQUIRED = {
    "individual_tasks_within_scope",
    "combined_output_within_scope",
    "unnecessary_operational_detail_removed",
    "sensitive_data_redacted",
}
MICROARCH_PROFILE = "microarchitecture-security"
SNAPSHOT_IDENTITY_FIELDS = (
    "repository",
    "commit",
    "dirty",
    "submodules",
    "rtl_config",
    "isa_privilege_assumptions",
    "target_class",
    "toolchain",
    "reference_model",
    "workloads",
)
FINAL_REQUIRED_HEADINGS = {
    "## Executive Summary",
    "## Scope and Authorization",
    "## Method and Coverage",
    "## Conflicts, Blocks, and Limitations",
    "## Claim-to-Evidence Matrix",
}
MICROARCH_FINAL_REQUIRED_HEADINGS = {
    "## Design Snapshot and Reproducibility",
    "## Experiment Matrix and Artifact Coverage",
}
FINAL_REPORT_TITLE = "# Security Research Report"
CLAIM_MATRIX_HEADER = "| Claim ID | Verdict | Evidence IDs | Scope | Limitations |"
LOAD_FAILED = object()

ACTIVE_ACTION_PATTERN = re.compile(
    r"(?:\b(?:run|execute|invoke|simulate|scan|measure|instrument|mutate|flash|program|launch|collect|capture|"
    r"benchmark|fuzz|send|interact)\b|运行|执行|仿真|模拟|探测|扫描|测量|插桩|修改|变更|烧录|编程|"
    r"启动|采集|收集|下发|交互|压测|(?<![/_-])\bprobe\b)",
    re.IGNORECASE,
)
MICROARCH_ACTION_PATTERN = re.compile(
    r"(?:\b(?:verilator|vcs|gem5|fpga|silicon|rtl|waveform|cycle\s+counter|hardware\s+counter|board)\b|"
    r"仿真器|芯片|板卡|开发板|硬件计数器|周期计数器|波形)",
    re.IGNORECASE,
)
HARDWARE_ACTION_PATTERN = re.compile(
    r"(?:\b(?:fpga|silicon|hardware\s+(?:board|device|counter)|board)\b|芯片|板卡|开发板|硬件计数器)",
    re.IGNORECASE,
)
HARDWARE_INTERACTION_PATTERN = re.compile(
    r"(?:(?:\b(?:access|connect|query|read|use)\b|访问|连接|读取|使用).{0,40}"
    r"(?:\b(?:fpga|silicon|hardware\s+(?:board|device|counter)|board)\b|芯片|板卡|开发板|硬件计数器))",
    re.IGNORECASE,
)
EXECUTION_START_PATTERN = re.compile(
    r"\bstart\b.{0,40}\b(?:verilator|simulator|simulation|workload|benchmark|fuzzer|target|device|board|test)\b",
    re.IGNORECASE,
)


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path}: {exc}")
    return LOAD_FAILED


def require_keys(data: Any, required: set[str], path: Path, errors: list[str]) -> None:
    if not isinstance(data, dict):
        errors.append(f"expected object: {path}")
        return
    missing = sorted(required - data.keys())
    if missing:
        errors.append(f"missing keys in {path}: {', '.join(missing)}")


def is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_enum_value(value: Any, choices: set[str]) -> bool:
    return isinstance(value, str) and value in choices


def is_string_list(value: Any, *, non_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not non_empty or bool(value))
        and all(is_non_empty_text(item) for item in value)
    )


def is_iso8601_timestamp(value: Any) -> bool:
    if not is_non_empty_text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def is_cell_assignment_value(value: Any) -> bool:
    if value is None or isinstance(value, (dict, list)):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, float):
        return math.isfinite(value)
    return isinstance(value, (bool, int))


def canonical_contract_hash(experiment: dict[str, Any]) -> str:
    contract = {key: value for key, value in experiment.items() if key != "status"}
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def describes_active_action(value: Any) -> bool:
    return isinstance(value, str) and (
        ACTIVE_ACTION_PATTERN.search(value) is not None
        or EXECUTION_START_PATTERN.search(value) is not None
    )


def normalize_contract_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def task_safety(task: Any) -> dict[str, Any]:
    if not isinstance(task, dict):
        return {}
    safety = task.get("safety")
    return safety if isinstance(safety, dict) else {}


def task_dependencies(task: Any) -> list[Any]:
    if not isinstance(task, dict):
        return []
    dependencies = task.get("dependencies")
    return dependencies if isinstance(dependencies, list) else []


def snapshot_identity(snapshot: Any) -> Optional[tuple[str, ...]]:
    if not isinstance(snapshot, dict):
        return None
    return tuple(
        json.dumps(snapshot.get(field), sort_keys=True, separators=(",", ":"))
        for field in SNAPSHOT_IDENTITY_FIELDS
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def validate_common_v3_state(
    state: dict[str, Any],
    state_path: Path,
    task_ids: list[str],
    errors: list[str],
) -> None:
    if not is_non_empty_text(state.get("run_id")):
        errors.append(f"run_id must be a non-empty string in {state_path}")
    if not is_iso8601_timestamp(state.get("updated_at")):
        errors.append(f"updated_at must be an ISO-8601 timestamp with timezone in {state_path}")
    if not is_non_empty_text(state.get("objective")):
        errors.append(f"run objective must be non-empty in {state_path}")
    scope = state.get("scope")
    if not isinstance(scope, dict):
        errors.append(f"run scope must be an object in {state_path}")
    else:
        for field in ("assets", "versions", "environments"):
            values = scope.get(field)
            if not is_string_list(values, non_empty=True) or len(values) != len(set(values)):
                errors.append(f"scope.{field} must be a non-empty unique string list in {state_path}")
    for field in ("allowed_actions", "prohibited_actions", "completion_criteria"):
        if not is_string_list(state.get(field), non_empty=True):
            errors.append(f"run {field} must be a non-empty string list in {state_path}")

    composition = state.get("composition_review")
    if not isinstance(composition, dict) or not COMPOSITION_REQUIRED.issubset(composition):
        errors.append(f"composition_review must contain all v3 checks in {state_path}")
    elif any(not isinstance(composition.get(field), bool) for field in COMPOSITION_REQUIRED):
        errors.append(f"composition_review checks must be booleans in {state_path}")

    authorization = state.get("authorization")
    authorization_fields = {
        "owner",
        "evidence",
        "time_window",
        "method_classes",
        "rate_limits",
        "rollback_plan",
        "data_handling",
        "output_audience",
    }
    if not isinstance(authorization, dict) or not authorization_fields.issubset(authorization):
        errors.append(f"authorization packet is incomplete in {state_path}")
    else:
        for field in ("owner", "rollback_plan", "data_handling", "output_audience"):
            if not is_non_empty_text(authorization.get(field)):
                errors.append(f"authorization.{field} must be non-empty in {state_path}")
        for field in ("evidence", "method_classes", "rate_limits"):
            if not is_string_list(authorization.get(field), non_empty=True):
                errors.append(f"authorization.{field} must be a non-empty string list in {state_path}")
        if authorization.get("time_window") is not None and not is_non_empty_text(authorization.get("time_window")):
            errors.append(f"authorization.time_window must be null or a non-empty string in {state_path}")
        if state.get("active_testing_approved") is True:
            active_approval = state.get("active_testing_approval", {})
            if not isinstance(active_approval, dict):
                active_approval = {}
            if authorization.get("owner") != active_approval.get("owner"):
                errors.append(f"authorization owner differs from active approval in {state_path}")
            if authorization.get("time_window") != active_approval.get("time_window"):
                errors.append(f"authorization time window differs from active approval in {state_path}")
            method_classes = authorization.get("method_classes")
            if not isinstance(method_classes, list) or active_approval.get("method_class") not in method_classes:
                errors.append(f"authorization method class differs from active approval in {state_path}")

    artifact_roots = state.get("artifact_roots")
    expected_roots = {"tasks": "tasks", "experiments": "experiments", "artifacts": "artifacts"}
    if not isinstance(artifact_roots, dict) or any(
        artifact_roots.get(key) != value for key, value in expected_roots.items()
    ):
        errors.append(f"v3 artifact_roots must use tasks, experiments, and artifacts in {state_path}")

    resume = state.get("resume")
    resume_fields = {"checkpoint_id", "completed_tasks", "retryable_tasks", "blocked_tasks", "next_actions"}
    if not isinstance(resume, dict) or not resume_fields.issubset(resume):
        errors.append(f"resume must define checkpoint and task/action lists in {state_path}")
        return
    checkpoint_id = resume.get("checkpoint_id")
    if checkpoint_id is not None and not is_non_empty_text(checkpoint_id):
        errors.append(f"resume.checkpoint_id must be null or a non-empty string in {state_path}")
    for field in ("completed_tasks", "retryable_tasks", "blocked_tasks"):
        values = resume.get(field)
        if (
            not isinstance(values, list)
            or any(not isinstance(item, str) or item not in task_ids for item in values)
            or len(values) != len(set(values))
        ):
            errors.append(f"resume.{field} contains an unknown, duplicate, or malformed task ID in {state_path}")
    next_actions = resume.get("next_actions")
    if not isinstance(next_actions, list) or any(not is_non_empty_text(item) for item in next_actions):
        errors.append(f"resume.next_actions must be a list of non-empty strings in {state_path}")
    elif state.get("status") == "completed" and next_actions:
        errors.append(f"completed run must have an empty resume.next_actions list in {state_path}")


def validate_target_snapshot(
    snapshot: Any,
    path: Path,
    errors: list[str],
    *,
    require_pinned: bool,
) -> None:
    if not isinstance(snapshot, dict):
        errors.append(f"target_snapshot must be an object in {path}")
        return
    if not is_enum_value(snapshot.get("target_class"), TARGET_CLASSES):
        errors.append(f"invalid target_class in {path}: {snapshot.get('target_class')}")
    if require_pinned:
        for field in ("repository", "commit", "rtl_config"):
            value = snapshot.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"microarchitecture profile requires target_snapshot.{field} in {path}")
        if not isinstance(snapshot.get("dirty"), bool):
            errors.append(f"microarchitecture profile requires boolean target_snapshot.dirty in {path}")
        for field in ("submodules", "isa_privilege_assumptions", "toolchain", "workloads"):
            value = snapshot.get(field)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                errors.append(f"microarchitecture profile requires target_snapshot.{field} as a string list in {path}")
        if not snapshot.get("toolchain"):
            errors.append(f"microarchitecture profile requires a pinned target_snapshot.toolchain in {path}")
        if snapshot.get("target_class") != "static-rtl" and not snapshot.get("workloads"):
            errors.append(f"executable target requires target_snapshot.workloads in {path}")


def validate_microarchitecture_state(
    state: dict[str, Any],
    state_path: Path,
    errors: list[str],
) -> Any:
    require_keys(state, MICROARCH_RUN_REQUIRED, state_path, errors)
    scope = state.get("scope")
    run_snapshot = scope.get("target_snapshot") if isinstance(scope, dict) else None
    validate_target_snapshot(run_snapshot, state_path, errors, require_pinned=True)

    return run_snapshot


def validate_task_graph(
    state: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    state_path: Path,
    errors: list[str],
) -> None:
    graph = state.get("task_graph")
    if not isinstance(graph, dict):
        errors.append(f"task_graph must be an object in {state_path}")
        return
    for field in ("edges", "waves", "exclusive_resources"):
        if not isinstance(graph.get(field), list):
            errors.append(f"task_graph.{field} must be a list in {state_path}")

    task_ids = set(tasks)
    parsed_edges: set[tuple[str, str]] = set()
    for edge in graph.get("edges", []) if isinstance(graph.get("edges"), list) else []:
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or any(not isinstance(item, str) or item not in task_ids for item in edge)
        ):
            errors.append(f"invalid task graph edge in {state_path}: {edge}")
            continue
        parsed_edge = (edge[0], edge[1])
        if parsed_edge in parsed_edges:
            errors.append(f"duplicate task graph edge in {state_path}: {edge}")
        parsed_edges.add(parsed_edge)
    expected_edges = {
        (dependency, task_id)
        for task_id, task in tasks.items()
        for dependency in task_dependencies(task)
        if isinstance(dependency, str) and dependency in task_ids
    }
    if parsed_edges != expected_edges:
        errors.append("task_graph.edges must exactly match task dependencies")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"task dependency cycle includes: {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in task_dependencies(tasks[task_id]):
            if isinstance(dependency, str) and dependency in tasks:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)

    wave_index: dict[str, int] = {}
    declared_by_tasks: set[str] = set()
    for index, wave in enumerate(graph.get("waves", []) if isinstance(graph.get("waves"), list) else []):
        if not isinstance(wave, list):
            errors.append(f"task graph wave {index} must be a list")
            continue
        if not wave:
            errors.append(f"task graph wave {index} must not be empty")
            continue
        wave_resources: set[str] = set()
        for task_id in wave:
            if not isinstance(task_id, str) or task_id not in task_ids:
                errors.append(f"unknown task in wave {index}: {task_id}")
                continue
            if task_id in wave_index:
                errors.append(f"task appears in multiple waves: {task_id}")
            wave_index[task_id] = index
            requirements = tasks[task_id].get("resource_requirements", {})
            resources = requirements.get("exclusive_resources", []) if isinstance(requirements, dict) else []
            for resource in resources if isinstance(resources, list) else []:
                if not isinstance(resource, str) or not resource.strip():
                    errors.append(f"invalid exclusive resource for {task_id} in wave {index}")
                    continue
                if resource in wave_resources:
                    errors.append(f"exclusive resource {resource} is shared in wave {index}")
                wave_resources.add(resource)
                declared_by_tasks.add(resource)
    if task_ids and set(wave_index) != task_ids:
        errors.append("task_graph.waves must schedule every task exactly once")
    for dependency, dependent in expected_edges:
        if dependency in wave_index and dependent in wave_index and wave_index[dependency] >= wave_index[dependent]:
            errors.append(f"dependency {dependency} must precede {dependent} in task_graph.waves")
    graph_resources = graph.get("exclusive_resources", [])
    if (
        not isinstance(graph_resources, list)
        or any(not is_non_empty_text(item) for item in graph_resources)
        or len(graph_resources) != len(set(graph_resources))
    ):
        errors.append("task_graph.exclusive_resources must be a unique list of non-empty strings")
    elif set(graph_resources) != declared_by_tasks:
        errors.append("task_graph.exclusive_resources must equal the resources declared by tasks")


def validate_microarchitecture_artifacts(
    run_dir: Path,
    state: dict[str, Any],
    run_snapshot: Any,
    tasks: dict[str, dict[str, Any]],
    evidence_artifact_refs: list[tuple[Path, str]],
    seen_evidence: set[str],
    errors: list[str],
) -> None:
    run_root = run_dir.resolve()
    experiments: dict[str, dict[str, Any]] = {}
    experiments_by_task: dict[str, set[str]] = {}
    experiment_cells: dict[str, dict[str, dict[str, Any]]] = {}
    experiment_matrices: dict[str, tuple[set[str], set[str], set[int], int]] = {}
    experiment_hashes: dict[str, str] = {}
    completed_experiments: set[str] = set()
    expected_artifacts_by_experiment: list[tuple[Path, str, list[str]]] = []
    experiments_root = run_root / "experiments"

    if experiments_root.exists():
        if experiments_root.resolve() != experiments_root:
            errors.append("experiments root must not be a symlink")
        for entry in experiments_root.iterdir():
            if not entry.is_dir() or entry.is_symlink() or not (entry / "experiment.json").is_file():
                errors.append(f"unexpected or incomplete experiment entry: {entry}")
        for experiment_path in sorted(experiments_root.glob("*/experiment.json")):
            if experiment_path.resolve() != experiment_path:
                errors.append(f"experiment contract escapes its owned directory: {experiment_path}")
                continue
            experiment = load_json(experiment_path, errors)
            if experiment is LOAD_FAILED:
                continue
            require_keys(experiment, EXPERIMENT_REQUIRED, experiment_path, errors)
            if not isinstance(experiment, dict):
                continue
            if experiment.get("schema_version") != 3:
                errors.append(f"experiment must use schema_version 3 in {experiment_path}")
            experiment_id = experiment.get("experiment_id")
            if (
                not isinstance(experiment_id, str)
                or not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id)
                or experiment_path.parent.name != experiment_id
            ):
                errors.append(f"invalid or misplaced experiment_id in {experiment_path}: {experiment_id}")
                continue
            if experiment_id in experiments:
                errors.append(f"duplicate experiment_id: {experiment_id}")
                continue
            experiments[experiment_id] = experiment
            experiment_hashes[experiment_id] = canonical_contract_hash(experiment)

            task_id = experiment.get("task_id")
            task = tasks.get(task_id) if isinstance(task_id, str) else None
            if task is None:
                errors.append(f"unknown experiment task in {experiment_path}")
            else:
                experiments_by_task.setdefault(task_id, set()).add(experiment_id)
                safety = task.get("safety", {})
                approval = state.get("active_testing_approval", {})
                if not isinstance(approval, dict):
                    approval = {}
                approved_task_ids = approval.get("approved_task_ids", [])
                if not isinstance(approved_task_ids, list):
                    approved_task_ids = []
                if (
                    safety.get("task_class") != "active_validation"
                    or safety.get("capability_boundary") != "active_authorized"
                    or experiment.get("approval_ref") != safety.get("approval_ref")
                    or experiment.get("approval_ref") != approval.get("approval_id")
                    or task_id not in approved_task_ids
                ):
                    errors.append(f"experiment is not bound to an approved active_validation task in {experiment_path}")

            if not is_enum_value(experiment.get("status"), EXPERIMENT_STATUSES):
                errors.append(f"invalid experiment status in {experiment_path}: {experiment.get('status')}")
            elif task is not None:
                task_status = task.get("status")
                experiment_status = experiment.get("status")
                allowed_statuses = TASK_EXPERIMENT_STATUSES.get(task_status) if isinstance(task_status, str) else None
                if allowed_statuses is None or experiment_status not in allowed_statuses:
                    errors.append(
                        f"task status {task_status} may not own experiment status {experiment_status} in {experiment_path}"
                    )
            if (
                not isinstance(experiment.get("revision"), int)
                or isinstance(experiment.get("revision"), bool)
                or experiment.get("revision", 0) < 1
            ):
                errors.append(f"invalid experiment revision in {experiment_path}")
            if not isinstance(experiment.get("hypothesis"), str) or not experiment.get("hypothesis").strip():
                errors.append(f"experiment hypothesis must be non-empty in {experiment_path}")

            variables = experiment.get("variables")
            variable_fields = {"independent", "dependent", "controlled", "nuisance"}
            independent_variable_ids: set[str] = set()
            if not isinstance(variables, dict) or not variable_fields.issubset(variables):
                errors.append(f"invalid experiment variables in {experiment_path}")
            elif any(
                not isinstance(variables[field], list)
                or any(not is_non_empty_text(item) for item in variables[field])
                or len(variables[field]) != len(set(variables[field]))
                for field in variable_fields
            ):
                errors.append(f"experiment variable groups must be unique string lists in {experiment_path}")
            elif any(not variables[field] for field in ("dependent", "controlled")):
                errors.append(
                    f"experiment dependent and controlled variables must be non-empty in {experiment_path}"
                )
            else:
                independent_variables = variables["independent"]
                if any(not VARIABLE_ID_PATTERN.fullmatch(item) for item in independent_variables):
                    errors.append(
                        f"experiment independent variables must be stable identifier strings in {experiment_path}"
                    )
                else:
                    independent_variable_ids = set(independent_variables)

            list_fields = (
                "workloads",
                "controls",
                "observables",
                "command_plan",
                "expected_artifacts",
                "acceptance_criteria",
                "inconclusive_criteria",
                "resource_exhaustion_criteria",
                "stop_conditions",
            )
            for field in list_fields:
                value = experiment.get(field)
                if not isinstance(value, list) or not value or any(
                    not isinstance(item, str) or not item.strip() for item in value
                ) or len(value) != len(set(value)):
                    errors.append(f"experiment {field} must be a non-empty unique string list in {experiment_path}")

            seed_policy = experiment.get("seed_policy")
            if (
                not isinstance(seed_policy, dict)
                or not isinstance(seed_policy.get("repetitions"), int)
                or isinstance(seed_policy.get("repetitions"), bool)
                or seed_policy.get("repetitions", 0) < 1
            ):
                errors.append(f"invalid seed policy in {experiment_path}")
            elif not is_enum_value(seed_policy.get("mode"), {"fixed-list", "deterministic"}):
                errors.append(f"unsupported seed policy mode in {experiment_path}: {seed_policy.get('mode')}")
            elif (
                not isinstance(seed_policy.get("seeds"), list)
                or not seed_policy.get("seeds")
                or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seed_policy.get("seeds", []))
                or len(seed_policy.get("seeds", [])) != len(set(seed_policy.get("seeds", [])))
            ):
                errors.append(f"seed policy requires at least one unique integer seed in {experiment_path}")

            cells = experiment.get("cells")
            parsed_cells: dict[str, dict[str, Any]] = {}
            assignment_fingerprints: set[str] = set()
            if not isinstance(cells, list) or not cells:
                errors.append(f"experiment cells must be a non-empty list in {experiment_path}")
            else:
                for cell_index, cell in enumerate(cells, 1):
                    require_keys(cell, CELL_REQUIRED, experiment_path, errors)
                    if not isinstance(cell, dict):
                        continue
                    cell_id = cell.get("cell_id")
                    if (
                        not isinstance(cell_id, str)
                        or not CELL_ID_PATTERN.fullmatch(cell_id)
                        or cell_id in parsed_cells
                    ):
                        errors.append(f"invalid or duplicate experiment cell_id at {experiment_path}:{cell_index}")
                        continue
                    if not is_non_empty_text(cell.get("label")):
                        errors.append(f"experiment cell label must be non-empty at {experiment_path}:{cell_index}")
                    assignments = cell.get("variable_assignments")
                    if (
                        not isinstance(assignments, dict)
                        or any(not is_non_empty_text(key) for key in assignments)
                    ):
                        errors.append(
                            f"experiment cell variable_assignments must be an object with string keys at "
                            f"{experiment_path}:{cell_index}"
                        )
                    else:
                        if set(assignments) != independent_variable_ids:
                            errors.append(
                                f"experiment cell variable_assignments must exactly match declared independent variables at "
                                f"{experiment_path}:{cell_index}"
                            )
                        if any(not is_cell_assignment_value(value) for value in assignments.values()):
                            errors.append(
                                f"experiment cell variable assignments must use non-null scalar values at "
                                f"{experiment_path}:{cell_index}"
                            )
                        fingerprint = json.dumps(assignments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                        if fingerprint in assignment_fingerprints:
                            errors.append(f"duplicate experiment cell variable assignments at {experiment_path}:{cell_index}")
                        assignment_fingerprints.add(fingerprint)
                    parsed_cells[cell_id] = cell
            if independent_variable_ids and len(parsed_cells) < 2:
                errors.append(
                    f"experiment with independent variables requires at least two distinct cells in {experiment_path}"
                )
            if isinstance(experiment_id, str):
                experiment_cells[experiment_id] = parsed_cells
                workloads = experiment.get("workloads")
                seeds = seed_policy.get("seeds") if isinstance(seed_policy, dict) else None
                repetitions = seed_policy.get("repetitions") if isinstance(seed_policy, dict) else None
                if (
                    is_string_list(workloads, non_empty=True)
                    and isinstance(seeds, list)
                    and all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
                    and isinstance(repetitions, int)
                    and not isinstance(repetitions, bool)
                    and repetitions > 0
                ):
                    experiment_matrices[experiment_id] = (
                        set(parsed_cells),
                        set(workloads),
                        set(seeds),
                        repetitions,
                    )

            budget = experiment.get("resource_budget")
            budget_fields = {"cpu", "memory_gb", "wall_time_minutes", "storage_gb", "exclusive_resources"}
            if not isinstance(budget, dict) or not budget_fields.issubset(budget):
                errors.append(f"invalid experiment resource_budget in {experiment_path}")
            elif (
                not isinstance(budget.get("exclusive_resources"), list)
                or any(not isinstance(item, str) or not item.strip() for item in budget.get("exclusive_resources", []))
                or len(budget.get("exclusive_resources", []))
                != len(set(budget.get("exclusive_resources", [])))
                or any(
                    isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0
                    for value in (budget.get("cpu"), budget.get("memory_gb"), budget.get("wall_time_minutes"), budget.get("storage_gb"))
                )
            ):
                errors.append(f"malformed experiment resource_budget in {experiment_path}")
            elif task is not None:
                task_resources = task.get("resource_requirements", {})
                task_exclusive = task_resources.get("exclusive_resources", []) if isinstance(task_resources, dict) else []
                safe_task_exclusive = {
                    item for item in task_exclusive if isinstance(item, str)
                } if isinstance(task_exclusive, list) else set()
                if not set(budget.get("exclusive_resources", [])).issubset(
                    safe_task_exclusive
                ):
                    errors.append(f"experiment exclusive resources are not declared by its task in {experiment_path}")
                for field in ("cpu", "memory_gb", "wall_time_minutes", "storage_gb"):
                    experiment_limit = budget.get(field)
                    task_limit = task_resources.get(field) if isinstance(task_resources, dict) else None
                    if (
                        experiment_limit is not None
                        and task_limit is not None
                        and isinstance(experiment_limit, (int, float))
                        and isinstance(task_limit, (int, float))
                        and experiment_limit > task_limit
                    ):
                        errors.append(f"experiment {field} exceeds its task resource budget in {experiment_path}")
            experiment_snapshot = experiment.get("target_snapshot")
            validate_target_snapshot(experiment_snapshot, experiment_path, errors, require_pinned=True)
            if snapshot_identity(experiment_snapshot) != snapshot_identity(run_snapshot):
                errors.append(f"experiment target snapshot differs from run snapshot in {experiment_path}")
            if isinstance(experiment_snapshot, dict) and experiment_snapshot.get("dirty") is True:
                errors.append(f"executable experiment requires a clean target snapshot in {experiment_path}")
            if isinstance(experiment_snapshot, dict) and experiment.get("workloads") != experiment_snapshot.get("workloads"):
                errors.append(f"experiment workloads differ from target snapshot in {experiment_path}")

            expected = experiment.get("expected_artifacts")
            if experiment.get("status") == "completed":
                completed_experiments.add(experiment_id)
                if isinstance(expected, list):
                    expected_artifacts_by_experiment.append(
                        (experiment_path, experiment_id, [item for item in expected if isinstance(item, str)])
                    )

    for task_id, task in tasks.items():
        safety = task.get("safety", {})
        if isinstance(safety, dict) and safety.get("task_class") == "active_validation":
            if not experiments_by_task.get(task_id):
                errors.append(f"active_validation task requires at least one experiment contract: {task_id}")

    artifact_ids: set[str] = set()
    artifact_experiments: dict[str, Any] = {}
    artifact_ids_by_experiment: dict[str, set[str]] = {}
    artifact_coordinates_by_experiment: dict[str, set[tuple[str, str, int, int]]] = {}
    registered_artifact_paths: set[Path] = set()
    artifact_path_owners: dict[Path, str] = {}
    manifest_path = run_root / "artifacts" / "manifest.jsonl"
    if manifest_path.exists():
        if manifest_path.resolve() != manifest_path:
            errors.append("artifact manifest must not be a symlink")
        for line_no, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                artifact = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSONL {manifest_path}:{line_no}: {exc}")
                continue
            require_keys(artifact, ARTIFACT_REQUIRED, manifest_path, errors)
            if not isinstance(artifact, dict):
                continue
            if artifact.get("schema_version") != 3:
                errors.append(f"artifact must use schema_version 3 at {manifest_path}:{line_no}")
            artifact_id = artifact.get("artifact_id")
            if not isinstance(artifact_id, str) or not artifact_id.strip() or artifact_id in artifact_ids:
                errors.append(f"invalid or duplicate artifact_id at {manifest_path}:{line_no}")
            else:
                artifact_ids.add(artifact_id)
                artifact_experiments[artifact_id] = artifact.get("experiment_id")
                if isinstance(artifact.get("experiment_id"), str):
                    artifact_ids_by_experiment.setdefault(artifact["experiment_id"], set()).add(artifact_id)

            producer = artifact.get("producer_task_id")
            if not isinstance(producer, str) or producer not in tasks:
                errors.append(f"unknown artifact producer at {manifest_path}:{line_no}")
            experiment_id = artifact.get("experiment_id")
            experiment = experiments.get(experiment_id) if isinstance(experiment_id, str) else None
            if experiment is None:
                errors.append(f"unknown artifact experiment at {manifest_path}:{line_no}")
            elif producer != experiment.get("task_id"):
                errors.append(f"artifact producer differs from experiment owner at {manifest_path}:{line_no}")
            if experiment is not None:
                if experiment.get("status") == "planned":
                    errors.append(f"planned experiment must not have realized artifacts at {manifest_path}:{line_no}")
                artifact_revision = artifact.get("experiment_revision")
                if (
                    not isinstance(artifact_revision, int)
                    or isinstance(artifact_revision, bool)
                    or artifact_revision < 1
                ):
                    errors.append(f"artifact experiment_revision must be a positive integer at {manifest_path}:{line_no}")
                elif artifact_revision != experiment.get("revision"):
                    errors.append(f"artifact experiment_revision differs from its experiment at {manifest_path}:{line_no}")
                expected_contract_hash = experiment_hashes.get(str(experiment_id))
                if artifact.get("experiment_contract_hash") != expected_contract_hash:
                    errors.append(f"artifact experiment_contract_hash differs from its experiment at {manifest_path}:{line_no}")

            cell_id = artifact.get("cell_id")
            cells_for_experiment = experiment_cells.get(str(experiment_id), {})
            cell = cells_for_experiment.get(cell_id) if isinstance(cell_id, str) else None
            if cell is None:
                errors.append(f"artifact references an unknown experiment cell at {manifest_path}:{line_no}")

            artifact_path_value = artifact.get("path")
            artifact_path = resolve_run_path(run_root, artifact_path_value, f"artifact path at {manifest_path}:{line_no}", errors)
            if artifact_path is not None:
                owned_root = run_root / "experiments" / str(experiment_id) / "results"
                if artifact_path != owned_root and owned_root not in artifact_path.parents:
                    errors.append(f"artifact path is outside experiment ownership at {manifest_path}:{line_no}")
                if not artifact_path.is_file():
                    errors.append(f"manifest artifact does not exist at {manifest_path}:{line_no}: {artifact_path_value}")
                else:
                    if artifact_path in artifact_path_owners:
                        errors.append(
                            f"artifact path is registered by multiple IDs at {manifest_path}:{line_no}: "
                            f"{artifact_path_owners[artifact_path]} and {artifact_id}"
                        )
                    elif isinstance(artifact_id, str):
                        artifact_path_owners[artifact_path] = artifact_id
                    registered_artifact_paths.add(artifact_path)

            hash_value = artifact.get("hash")
            if not isinstance(hash_value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", hash_value):
                errors.append(f"artifact requires a populated sha256 hash at {manifest_path}:{line_no}")
            elif artifact_path is not None and artifact_path.is_file() and file_sha256(artifact_path) != hash_value:
                errors.append(f"artifact hash mismatch at {manifest_path}:{line_no}")
            artifact_snapshot = artifact.get("target_snapshot")
            validate_target_snapshot(artifact_snapshot, manifest_path, errors, require_pinned=True)
            if snapshot_identity(artifact_snapshot) != snapshot_identity(run_snapshot):
                errors.append(f"artifact target snapshot differs from run snapshot at {manifest_path}:{line_no}")
            if isinstance(artifact_snapshot, dict) and artifact_snapshot.get("dirty") is True:
                errors.append(f"generated artifact requires a clean target snapshot at {manifest_path}:{line_no}")
            tool_versions = artifact.get("tool_versions")
            workload_ids = artifact.get("workload_ids")
            experiment_workloads = experiment.get("workloads", []) if isinstance(experiment, dict) else []
            if not isinstance(experiment_workloads, list):
                experiment_workloads = []
            if not isinstance(tool_versions, list) or not tool_versions or any(
                not isinstance(item, str) for item in tool_versions
            ):
                errors.append(f"artifact tool_versions must be a non-empty string list at {manifest_path}:{line_no}")
            elif isinstance(artifact_snapshot, dict) and tool_versions != artifact_snapshot.get("toolchain"):
                errors.append(f"artifact tool_versions differ from target snapshot at {manifest_path}:{line_no}")
            if not isinstance(workload_ids, list) or not workload_ids or any(
                not isinstance(item, str) for item in workload_ids
            ):
                errors.append(f"artifact workload_ids must be a non-empty string list at {manifest_path}:{line_no}")
            elif len(workload_ids) != 1 or workload_ids[0] not in experiment_workloads:
                errors.append(f"artifact must bind exactly one declared experiment workload at {manifest_path}:{line_no}")
            if not is_enum_value(artifact.get("kind"), ARTIFACT_KINDS):
                errors.append(f"invalid artifact kind at {manifest_path}:{line_no}: {artifact.get('kind')}")
            if not is_enum_value(artifact.get("sensitivity"), SENSITIVITY_LEVELS):
                errors.append(
                    f"invalid artifact sensitivity at {manifest_path}:{line_no}: {artifact.get('sensitivity')}"
                )
            if not is_enum_value(artifact.get("retention"), RETENTION_POLICIES):
                errors.append(f"invalid artifact retention at {manifest_path}:{line_no}: {artifact.get('retention')}")
            if not is_iso8601_timestamp(artifact.get("generated_at")):
                errors.append(f"artifact generated_at must be an ISO-8601 timestamp with timezone at {manifest_path}:{line_no}")
            seed = artifact.get("seed")
            artifact_seed_policy = experiment.get("seed_policy", {}) if isinstance(experiment, dict) else {}
            if not isinstance(artifact_seed_policy, dict):
                artifact_seed_policy = {}
            artifact_seeds = artifact_seed_policy.get("seeds", [])
            if not isinstance(artifact_seeds, list):
                artifact_seeds = []
            artifact_repetitions = artifact_seed_policy.get("repetitions", 0)
            if not isinstance(artifact_repetitions, int) or isinstance(artifact_repetitions, bool):
                artifact_repetitions = 0
            if not isinstance(seed, int) or isinstance(seed, bool):
                errors.append(f"artifact seed must be an integer at {manifest_path}:{line_no}")
            elif seed not in artifact_seeds:
                errors.append(f"artifact seed is not declared by its experiment at {manifest_path}:{line_no}")
            repetition_index = artifact.get("repetition_index")
            if (
                not isinstance(repetition_index, int)
                or isinstance(repetition_index, bool)
                or repetition_index < 0
            ):
                errors.append(f"artifact repetition_index must be a non-negative integer at {manifest_path}:{line_no}")
            elif (
                repetition_index >= artifact_repetitions
            ):
                errors.append(f"artifact repetition_index is outside its experiment at {manifest_path}:{line_no}")

            if (
                cell is not None
                and isinstance(cell_id, str)
                and isinstance(workload_ids, list)
                and len(workload_ids) == 1
                and isinstance(workload_ids[0], str)
                and isinstance(seed, int)
                and not isinstance(seed, bool)
                and isinstance(repetition_index, int)
                and not isinstance(repetition_index, bool)
                and repetition_index >= 0
            ):
                coordinate = (cell_id, workload_ids[0], seed, repetition_index)
                matrix = experiment_matrices.get(str(experiment_id))
                if matrix is None or not (
                    coordinate[0] in matrix[0]
                    and coordinate[1] in matrix[1]
                    and coordinate[2] in matrix[2]
                    and coordinate[3] < matrix[3]
                ):
                    errors.append(f"artifact coordinate is outside its experiment matrix at {manifest_path}:{line_no}")
                else:
                    artifact_coordinates_by_experiment.setdefault(str(experiment_id), set()).add(coordinate)

    for experiment_path, experiment_id, expected in expected_artifacts_by_experiment:
        missing = sorted(set(expected) - artifact_ids)
        if missing:
            errors.append(f"unknown expected artifact IDs in {experiment_path}: {', '.join(missing)}")
        unexpected = sorted(artifact_ids_by_experiment.get(experiment_id, set()) - set(expected))
        if unexpected:
            errors.append(f"completed experiment has unplanned artifact IDs in {experiment_path}: {', '.join(unexpected)}")
        for artifact_id in set(expected) & artifact_ids:
            if artifact_experiments.get(artifact_id) != experiment_id:
                errors.append(f"artifact {artifact_id} is owned by a different experiment than {experiment_id}")
        matrix = experiment_matrices.get(experiment_id)
        expected_coordinate_count = (
            len(matrix[0]) * len(matrix[1]) * len(matrix[2]) * matrix[3]
            if matrix is not None
            else 0
        )
        covered_coordinate_count = len(artifact_coordinates_by_experiment.get(experiment_id, set()))
        if covered_coordinate_count != expected_coordinate_count:
            errors.append(
                f"completed experiment has uncovered cell/workload/seed/repetition coordinates in {experiment_path}: "
                f"expected {expected_coordinate_count}, found {covered_coordinate_count}"
            )

    if experiments_root.exists():
        for results_root in experiments_root.glob("*/results"):
            if results_root.is_symlink():
                errors.append(f"experiment results root must not be a symlink: {results_root}")
                continue
            for result_path in results_root.rglob("*"):
                if result_path.is_file() and result_path.resolve() not in registered_artifact_paths:
                    errors.append(f"unregistered experiment artifact: {result_path}")

    for evidence_path, artifact_id in evidence_artifact_refs:
        if artifact_id not in artifact_ids:
            errors.append(f"unknown artifact ID referenced in {evidence_path}: {artifact_id}")
    if (completed_experiments or evidence_artifact_refs) and not manifest_path.is_file():
        errors.append("completed experiments or artifact-backed evidence require artifacts/manifest.jsonl")

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
    task_class = task_safety(task).get("task_class")
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


def markdown_section_content(report: str, heading: str) -> str:
    lines = report.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return ""
    content: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            content.append(line.strip())
    return "\n".join(content)


def validate_completed_run_package(
    run_dir: Path,
    state: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    seen_evidence: set[str],
    evidence_supports: dict[str, set[str]],
    finding_verdicts: dict[str, str],
    errors: list[str],
) -> None:
    resume = state.get("resume", {})
    if not isinstance(resume, dict) or not is_non_empty_text(resume.get("checkpoint_id")):
        errors.append("completed v3 run requires a non-empty resume.checkpoint_id")

    synthesis_tasks = [
        task_id
        for task_id, task in tasks.items()
        if task_safety(task).get("task_class") == "synthesis" and task.get("status") == "completed"
    ]
    if len(synthesis_tasks) != 1:
        errors.append("completed v3 run requires exactly one completed synthesis task")
    else:
        synthesis = tasks[synthesis_tasks[0]]
        outputs = synthesis.get("expected_outputs", [])
        if not isinstance(outputs, list) or "final/final-report.md" not in outputs:
            errors.append("completed synthesis task must declare final/final-report.md")

    evidence_index_path = run_dir / "evidence-index.json"
    evidence_index = load_json(evidence_index_path, errors)
    if evidence_index is LOAD_FAILED:
        pass
    elif isinstance(evidence_index, dict):
        if evidence_index.get("schema_version") != 3:
            errors.append(f"evidence-index must use schema_version 3 in {evidence_index_path}")
        records = evidence_index.get("records")
        if not isinstance(records, list):
            errors.append(f"evidence-index records must be a list in {evidence_index_path}")
        else:
            indexed_ids = [
                record.get("evidence_id")
                for record in records
                if isinstance(record, dict) and is_non_empty_text(record.get("evidence_id"))
            ]
            if set(indexed_ids) != seen_evidence:
                errors.append("evidence-index.json must index every evidence ID exactly once")
            if len(indexed_ids) != len(set(indexed_ids)) or len(indexed_ids) != len(records):
                errors.append("evidence-index.json contains duplicate or malformed records")
    else:
        errors.append(f"expected object: {evidence_index_path}")

    final_report_path = run_dir / "final" / "final-report.md"
    if not final_report_path.is_file():
        return
    final_report = final_report_path.read_text(encoding="utf-8")
    required_headings = set(FINAL_REQUIRED_HEADINGS)
    if state.get("research_profile") == MICROARCH_PROFILE:
        required_headings |= MICROARCH_FINAL_REQUIRED_HEADINGS
    if FINAL_REPORT_TITLE not in final_report.splitlines():
        errors.append(f"final report is missing required title: {FINAL_REPORT_TITLE}")
    missing_headings = sorted(heading for heading in required_headings if heading not in final_report.splitlines())
    if missing_headings:
        errors.append(f"final report is missing required headings: {', '.join(missing_headings)}")
    for heading in sorted(required_headings - {"## Claim-to-Evidence Matrix"}):
        if heading in final_report.splitlines() and not markdown_section_content(final_report, heading):
            errors.append(f"final report section is empty: {heading}")
    matrix = markdown_section_content(final_report, "## Claim-to-Evidence Matrix")
    matrix_lines = [line.strip() for line in matrix.splitlines() if line.strip()]
    if CLAIM_MATRIX_HEADER not in matrix_lines:
        errors.append("final report claim-to-evidence matrix is missing its canonical header")
    data_rows = [
        line
        for line in matrix_lines
        if line.startswith("|")
        and line != CLAIM_MATRIX_HEADER
        and not re.fullmatch(r"\|[\s|:-]+\|", line)
    ]
    if not data_rows:
        errors.append("final report claim-to-evidence matrix has no claim rows")
    known_claims = {claim_id for claims in evidence_supports.values() for claim_id in claims}
    for row_index, row in enumerate(data_rows, 1):
        columns = [column.strip().strip("`") for column in row.strip("|").split("|")]
        if len(columns) != 5 or any(not column for column in columns):
            errors.append(f"final report claim-to-evidence row {row_index} must have five non-empty columns")
            continue
        claim_id, verdict, evidence_cell, _, _ = columns
        if claim_id not in known_claims:
            errors.append(f"final report claim-to-evidence row references unknown claim: {claim_id}")
        if not is_enum_value(verdict, VERDICTS):
            errors.append(f"final report claim-to-evidence row has invalid verdict: {verdict}")
        elif claim_id in finding_verdicts and verdict != finding_verdicts[claim_id]:
            errors.append(f"final report verdict differs from finding {claim_id}: {verdict}")
        elif verdict in {"verified", "corroborated"} and claim_id not in finding_verdicts:
            errors.append(f"final report accepted claim lacks a matching finding record: {claim_id}")
        evidence_ids = [item.strip().strip("`") for item in evidence_cell.split(",") if item.strip()]
        if not evidence_ids:
            errors.append(f"final report claim-to-evidence row has no evidence IDs: {claim_id}")
            continue
        for evidence_id in evidence_ids:
            if evidence_id not in seen_evidence:
                errors.append(f"final report claim-to-evidence row references unknown evidence: {evidence_id}")
            elif claim_id not in evidence_supports.get(evidence_id, set()):
                errors.append(f"final report evidence {evidence_id} does not support claim {claim_id}")


def validate_task_outputs(
    run_dir: Path,
    task_id: str,
    task: dict[str, Any],
    errors: list[str],
    *,
    require_content: bool,
) -> None:
    outputs = task.get("expected_outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append(f"task has no expected_outputs contract: {task_id}")
        return
    if any(not isinstance(output, str) for output in outputs) or len(outputs) != len(set(outputs)):
        errors.append(f"task expected_outputs must be unique strings: {task_id}")
        return
    for output in outputs:
        output_path = expected_output_path(run_dir, task_id, task, output, errors)
        if require_content and output_path is not None and not output_has_content(output_path):
            errors.append(f"completed task output is missing or empty: {task_id}:{output}")


def validate_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    state_path = run_dir / "run-state.json"
    state = load_json(state_path, errors)
    if state is LOAD_FAILED:
        return errors
    require_keys(state, RUN_REQUIRED, state_path, errors)
    if not isinstance(state, dict):
        return errors

    schema_version = state.get("schema_version", 1)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version not in SCHEMA_VERSIONS:
        errors.append("run-state.json schema_version must be one of the supported integer versions: 1, 2, or 3")
        return errors
    if schema_version >= 2:
        require_keys(state, RUN_V2_REQUIRED, state_path, errors)
        policy_event_log = state.get("policy_event_log")
        if not isinstance(policy_event_log, str) or not policy_event_log.strip():
            errors.append("v2 run-state.json policy_event_log must be a non-empty path string")
    if schema_version >= 3:
        require_keys(state, RUN_V3_REQUIRED, state_path, errors)
        if not is_enum_value(state.get("research_profile"), RESEARCH_PROFILES):
            errors.append(
                "v3 research_profile must be one of: " + ", ".join(sorted(RESEARCH_PROFILES))
            )
        if not is_enum_value(state.get("authorization_tier"), AUTHORIZATION_TIERS):
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
            if not is_string_list(stop_conditions):
                errors.append("active_testing_approval.stop_conditions must be a list of non-empty strings")
            approved_task_ids = active_approval.get("approved_task_ids")
            if not is_string_list(approved_task_ids):
                errors.append("active_testing_approval.approved_task_ids must be a list of non-empty strings")
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

    if not is_enum_value(state.get("status"), RUN_STATUSES):
        errors.append(f"invalid run status in {state_path}: {state.get('status')}")
    microarchitecture_profile = state.get("research_profile") == MICROARCH_PROFILE

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

    run_snapshot: Any = None
    if schema_version == 3:
        validate_common_v3_state(state, state_path, task_ids, errors)
    if microarchitecture_profile:
        run_snapshot = validate_microarchitecture_state(state, state_path, errors)

    seen_evidence: set[str] = set()
    evidence_owners: dict[str, str] = {}
    evidence_supports: dict[str, set[str]] = {}
    evidence_artifact_refs: list[tuple[Path, str]] = []
    finding_refs: list[tuple[Path, str, list[str], str, str, Any]] = []
    seen_finding_ids: set[str] = set()
    finding_verdicts: dict[str, str] = {}
    policy_blocked_tasks: set[str] = set()
    task_records: dict[str, dict[str, Any]] = {}
    run_root = run_dir.resolve()
    tasks_root = run_root / "tasks"
    if not tasks_root.is_dir() or tasks_root.is_symlink():
        errors.append(f"tasks root must be a real directory: {tasks_root}")
    else:
        for entry in tasks_root.iterdir():
            if not entry.is_dir() or entry.is_symlink() or not (entry / "task.json").is_file():
                errors.append(f"unexpected or incomplete task entry: {entry}")
            elif entry.name not in task_ids:
                errors.append(f"undeclared task directory is outside task graph ownership: {entry.name}")

    for task_id in task_ids:
        task_dir = run_root / "tasks" / task_id
        if task_dir.resolve() != task_dir:
            errors.append(f"task directory escapes run ownership for task ID: {task_id}")
            continue
        task_path = task_dir / "task.json"
        task = load_json(task_path, errors)
        if task is LOAD_FAILED:
            continue
        require_keys(task, TASK_REQUIRED, task_path, errors)
        if not isinstance(task, dict):
            continue
        task_records[task_id] = task
        if schema_version == 3:
            require_keys(task, TASK_V3_REQUIRED, task_path, errors)
            if task.get("schema_version") != 3:
                errors.append(f"v3 task must use schema_version 3 in {task_path}")
            if not is_enum_value(task.get("role"), TASK_ROLES):
                errors.append(f"invalid task role in {task_path}: {task.get('role')}")
            for field in ("objective", "research_question"):
                if not is_non_empty_text(task.get(field)):
                    errors.append(f"task {field} must be non-empty in {task_path}")
            if not isinstance(task.get("dependencies"), list) or any(
                not is_non_empty_text(item) for item in task.get("dependencies", [])
            ) or len(task.get("dependencies", [])) != len(set(task.get("dependencies", []))):
                errors.append(f"task dependencies must be a unique string list in {task_path}")
            for field in (
                "assigned_paths",
                "inputs",
                "allowed_actions",
                "prohibited_actions",
                "expected_outputs",
                "acceptance_criteria",
                "evidence_requirements",
                "stop_conditions",
                "escalation_conditions",
            ):
                value = task.get(field)
                if not is_string_list(value, non_empty=True) or len(value) != len(set(value)):
                    errors.append(f"task {field} must be a non-empty unique string list in {task_path}")
        if microarchitecture_profile:
            require_keys(task, MICROARCH_TASK_REQUIRED, task_path, errors)
            if task.get("schema_version") != 3:
                errors.append(f"microarchitecture task must use schema_version 3 in {task_path}")
            resources = task.get("resource_requirements")
            resource_fields = {"cpu", "memory_gb", "wall_time_minutes", "storage_gb", "exclusive_resources"}
            if not isinstance(resources, dict) or not resource_fields.issubset(resources):
                errors.append(f"invalid resource_requirements in {task_path}")
            elif (
                not isinstance(resources.get("exclusive_resources"), list)
                or any(
                    not isinstance(item, str) or not item.strip()
                    for item in resources.get("exclusive_resources", [])
                )
                or len(resources.get("exclusive_resources", []))
                != len(set(resources.get("exclusive_resources", [])))
                or any(
                    value is not None
                    and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0)
                    for value in (
                        resources.get("cpu"),
                        resources.get("memory_gb"),
                        resources.get("wall_time_minutes"),
                        resources.get("storage_gb"),
                    )
                )
            ):
                errors.append(f"malformed resource_requirements in {task_path}")
            elif not is_enum_value(task.get("execution_mode"), {"read-only", "passive-research"}) and any(
                isinstance(resources.get(field), bool)
                or not isinstance(resources.get(field), (int, float))
                or resources.get(field) <= 0
                for field in ("cpu", "memory_gb", "wall_time_minutes", "storage_gb")
            ):
                errors.append(f"executable task requires positive numeric resource reservations in {task_path}")
            if not is_enum_value(task.get("execution_mode"), MICROARCH_EXECUTION_MODES):
                errors.append(f"invalid microarchitecture execution_mode in {task_path}: {task.get('execution_mode')}")
            task_snapshot = task.get("target_snapshot")
            validate_target_snapshot(task_snapshot, task_path, errors, require_pinned=True)
            if snapshot_identity(task_snapshot) != snapshot_identity(run_snapshot):
                errors.append(f"task target snapshot differs from run snapshot in {task_path}")
            execution_mode = task.get("execution_mode")
            expected_target_classes = EXECUTION_TARGET_CLASSES.get(execution_mode) if isinstance(execution_mode, str) else None
            if (
                expected_target_classes
                and isinstance(task_snapshot, dict)
                and not is_enum_value(task_snapshot.get("target_class"), expected_target_classes)
            ):
                errors.append(f"execution_mode and target_class disagree in {task_path}")
        if task.get("task_id") != task_id:
            errors.append(f"task ID mismatch in {task_path}")
        status = task.get("status")
        if not is_enum_value(status, ALL_TASK_STATUSES):
            errors.append(f"invalid task status in {task_path}: {status}")
        if status == "policy_blocked":
            policy_blocked_tasks.add(task_id)
        dependencies = task.get("dependencies", [])
        valid_dependencies = task_dependencies(task)
        if not isinstance(dependencies, list) or any(dep not in task_ids for dep in valid_dependencies):
            errors.append(f"unknown or malformed dependency in {task_path}")
        elif task_id in valid_dependencies:
            errors.append(f"task cannot depend on itself in {task_path}")
        attempts = task.get("attempts")
        max_attempts = task.get("max_attempts")
        if (
            not isinstance(attempts, int)
            or not isinstance(max_attempts, int)
            or isinstance(attempts, bool)
            or isinstance(max_attempts, bool)
            or attempts < 0
            or max_attempts < 0
            or attempts > max_attempts
        ):
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
                if not is_enum_value(task_class, TASK_CLASSES):
                    errors.append(f"invalid task_class in {task_path}: {task_class}")
                expected_role = TASK_CLASS_ROLES.get(task_class) if isinstance(task_class, str) else None
                if expected_role is not None and task.get("role") != expected_role:
                    errors.append(f"task_class {task_class} requires role {expected_role} in {task_path}")
                if not is_enum_value(boundary, CAPABILITY_BOUNDARIES):
                    errors.append(f"invalid capability_boundary in {task_path}: {boundary}")
                if (
                    not is_string_list(resource_scope, non_empty=True)
                    or len(resource_scope) != len(set(resource_scope))
                ):
                    errors.append(f"resource_scope must be a non-empty unique string list in {task_path}")
                if not isinstance(evidence_goal, str) or not evidence_goal.strip():
                    errors.append(f"evidence_goal must be non-empty in {task_path}")
                if (
                    not isinstance(active_actions, list)
                    or any(not is_non_empty_text(item) for item in active_actions)
                    or len(active_actions) != len(set(active_actions))
                ):
                    errors.append(f"active_actions must be a unique list of non-empty strings in {task_path}")
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
                    if not isinstance(approval, dict):
                        approval = {}
                    if approval_ref != approval.get("approval_id"):
                        errors.append(f"active task approval_ref mismatch in {task_path}")
                    approved_task_ids = approval.get("approved_task_ids", [])
                    if not isinstance(approved_task_ids, list) or task_id not in approved_task_ids:
                        errors.append(f"active task absent from approved_task_ids in {task_path}")
                if schema_version >= 3 and boundary == "non_operational" and approval_ref is not None:
                    errors.append(f"non_operational task must have null approval_ref in {task_path}")
                if (
                    not isinstance(composition_dependencies, list)
                    or any(dep not in task_ids for dep in composition_dependencies)
                    or len(composition_dependencies) != len(set(composition_dependencies))
                ):
                    errors.append(f"unknown or malformed composition dependency in {task_path}")
                elif not set(valid_dependencies).issubset(set(composition_dependencies)):
                    errors.append(f"composition_dependencies must include every execution dependency in {task_path}")
                safe_fallback = safety.get("safe_fallback")
                if safe_fallback is not None and not is_non_empty_text(safe_fallback):
                    errors.append(f"safe_fallback must be null or a non-empty string in {task_path}")
                executable = not is_enum_value(task.get("execution_mode"), {"read-only", "passive-research"})
                if microarchitecture_profile and executable and task_class != "active_validation":
                    errors.append(f"executable microarchitecture task must use active_validation in {task_path}")
                if microarchitecture_profile and task_class == "active_validation" and not executable:
                    errors.append(f"active_validation microarchitecture task requires an executable mode in {task_path}")
                if (
                    microarchitecture_profile
                    and is_enum_value(task.get("execution_mode"), {"fpga", "silicon"})
                    and state.get("authorization_tier") != "A2"
                ):
                    errors.append(f"fpga or silicon execution requires authorization tier A2 in {task_path}")
                allowed_actions = task.get("allowed_actions")
                if not isinstance(allowed_actions, list) or any(
                    not isinstance(action, str) for action in allowed_actions
                ):
                    errors.append(f"allowed_actions must be a list of strings in {task_path}")
                elif is_string_list(active_actions) and not set(active_actions).issubset(allowed_actions):
                    errors.append(f"active_actions must be declared in allowed_actions in {task_path}")
                if isinstance(allowed_actions, list):
                    dynamic_allowed_actions = [
                        action for action in allowed_actions if describes_active_action(action)
                    ]
                    active_intent_surfaces = dynamic_allowed_actions + [
                        value
                        for value in (task.get("objective"), task.get("research_question"))
                        if describes_active_action(value)
                    ]
                    active_intent_surfaces.extend(
                        action
                        for action in allowed_actions
                        if isinstance(action, str) and HARDWARE_INTERACTION_PATTERN.search(action)
                    )
                    active_intent_surfaces = list(dict.fromkeys(active_intent_surfaces))
                    if boundary == "non_operational" and active_intent_surfaces:
                        errors.append(
                            f"non_operational task contract describes active work in {task_path}: "
                            + "; ".join(active_intent_surfaces)
                        )
                active_action_text = " ".join(active_actions) if is_string_list(active_actions, non_empty=True) else ""
                if active_action_text and MICROARCH_ACTION_PATTERN.search(active_action_text):
                    if not microarchitecture_profile:
                        errors.append(f"microarchitecture active action requires research_profile {MICROARCH_PROFILE} in {task_path}")
                    if HARDWARE_ACTION_PATTERN.search(active_action_text) and state.get("authorization_tier") != "A2":
                        errors.append(f"FPGA, silicon, or hardware-board action requires authorization tier A2 in {task_path}")

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
                if not isinstance(record, dict):
                    continue
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
                if not is_enum_value(record.get("kind"), EVIDENCE_KINDS):
                    errors.append(f"invalid evidence kind at {evidence_path}:{line_no}: {record.get('kind')}")
                if not is_enum_value(record.get("sensitivity"), SENSITIVITY_LEVELS):
                    errors.append(
                        f"invalid evidence sensitivity at {evidence_path}:{line_no}: {record.get('sensitivity')}"
                    )
                for field in ("locator", "observation"):
                    value = record.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"evidence {field} must be non-empty at {evidence_path}:{line_no}")
                supports = record.get("supports")
                if not isinstance(supports, list) or not supports or any(
                    not isinstance(item, str) or not item.strip() for item in supports
                ) or len(supports) != len(set(supports)):
                    errors.append(f"evidence supports must be a non-empty unique string list at {evidence_path}:{line_no}")
                elif isinstance(evidence_id, str) and evidence_id.strip():
                    evidence_supports[evidence_id] = set(supports)
                artifact_id = record.get("artifact_id")
                if (
                    microarchitecture_profile
                    and (
                        is_enum_value(record.get("kind"), GENERATED_EVIDENCE_KINDS)
                        or task_safety(task).get("task_class") == "active_validation"
                    )
                    and (not isinstance(artifact_id, str) or not artifact_id.strip())
                ):
                    errors.append(f"generated microarchitecture evidence requires artifact_id at {evidence_path}:{line_no}")
                if artifact_id is not None:
                    if not isinstance(artifact_id, str) or not artifact_id.strip():
                        errors.append(f"evidence artifact_id must be a non-empty string at {evidence_path}:{line_no}")
                    else:
                        evidence_artifact_refs.append((evidence_path, artifact_id))

        for finding_path in sorted(task_dir.glob("finding-*.json")):
            finding = load_json(finding_path, errors)
            if finding is LOAD_FAILED:
                continue
            require_keys(finding, FINDING_REQUIRED, finding_path, errors)
            if not isinstance(finding, dict):
                continue
            if schema_version == 3:
                require_keys(finding, FINDING_V3_REQUIRED, finding_path, errors)
            if finding.get("task_id") != task_id:
                errors.append(f"finding task mismatch in {finding_path}")
            verdict = finding.get("verification_status")
            if not is_enum_value(verdict, VERDICTS):
                errors.append(f"invalid finding verdict in {finding_path}: {verdict}")
            for field in (
                "finding_id",
                "title",
                "observation",
                "interpretation",
                "impact",
            ):
                if not is_non_empty_text(finding.get(field)):
                    errors.append(f"finding {field} must be non-empty in {finding_path}")
            finding_id = finding.get("finding_id")
            if is_non_empty_text(finding_id):
                if finding_id in seen_finding_ids:
                    errors.append(f"duplicate finding_id in {finding_path}: {finding_id}")
                seen_finding_ids.add(finding_id)
                if is_enum_value(verdict, VERDICTS):
                    finding_verdicts[finding_id] = verdict
            for field in ("affected_scope", "preconditions", "remediation", "limitations"):
                if not is_string_list(finding.get(field), non_empty=True):
                    errors.append(f"finding {field} must be a non-empty list of strings in {finding_path}")
            if schema_version == 3:
                if not is_enum_value(finding.get("severity"), FINDING_SEVERITIES):
                    errors.append(f"invalid finding severity in {finding_path}: {finding.get('severity')}")
                if not is_enum_value(finding.get("confidence"), FINDING_CONFIDENCES):
                    errors.append(f"invalid finding confidence in {finding_path}: {finding.get('confidence')}")
                for field in ("severity_rationale", "confidence_rationale"):
                    if not is_non_empty_text(finding.get(field)):
                        errors.append(f"finding {field} must be non-empty in {finding_path}")
                for field in ("counter_evidence", "false_positive_hypotheses", "regression_checks", "redactions"):
                    value = finding.get(field)
                    if not isinstance(value, list) or any(not is_non_empty_text(item) for item in value):
                        errors.append(f"finding {field} must be a list of non-empty strings in {finding_path}")
                if is_enum_value(verdict, {"verified", "corroborated"}):
                    for field in ("counter_evidence", "false_positive_hypotheses", "regression_checks"):
                        if not finding.get(field):
                            errors.append(f"{verdict} finding requires non-empty {field} in {finding_path}")
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
                        finding_id if isinstance(finding_id, str) else "",
                        evidence_ids,
                        task_id,
                        verdict,
                        finding.get("verifier_task_id"),
                    )
                )

    for task_id, task in task_records.items():
        if not is_enum_value(task.get("status"), {"running", "completed"}):
            continue
        task_class = task_safety(task).get("task_class")
        required_statuses = TERMINAL_TASK_STATUSES if task_class == "synthesis" else {"completed"}
        for dependency in task_dependencies(task):
            if not isinstance(dependency, str):
                continue
            dependency_task = task_records.get(dependency)
            if dependency_task is not None and not is_enum_value(dependency_task.get("status"), required_statuses):
                errors.append(
                    f"{task.get('status')} task {task_id} has dependency {dependency} in status "
                    f"{dependency_task.get('status')}"
                )

    if schema_version == 3 or "task_graph" in state:
        validate_task_graph(state, task_records, state_path, errors)
    if schema_version == 3:
        resume = state.get("resume", {})
        expected_resume_statuses = {
            "completed_tasks": {"completed"},
            "retryable_tasks": {"retryable_error"},
            "blocked_tasks": TERMINAL_TASK_STATUSES - {"completed", "cancelled"},
        }
        if isinstance(resume, dict):
            for field, statuses in expected_resume_statuses.items():
                declared = (
                    {item for item in resume.get(field, []) if isinstance(item, str)}
                    if isinstance(resume.get(field), list)
                    else set()
                )
                expected = {
                    task_id
                    for task_id, task in task_records.items()
                    if is_enum_value(task.get("status"), statuses)
                }
                if declared != expected:
                    errors.append(f"resume.{field} must exactly match task statuses")

    for task_id, task in task_records.items():
        validate_task_outputs(
            run_root,
            task_id,
            task,
            errors,
            require_content=task.get("status") == "completed",
        )

    if schema_version >= 3:
        active_approval = state.get("active_testing_approval", {})
        if isinstance(active_approval, dict) and active_approval.get("approved") is True:
            approval_id = active_approval.get("approval_id")
            approved_task_ids = active_approval.get("approved_task_ids", [])
            for approved_task_id in approved_task_ids if isinstance(approved_task_ids, list) else []:
                if not isinstance(approved_task_id, str):
                    continue
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

    for finding_path, finding_id, evidence_ids, origin_task_id, verdict, verifier_task_id in finding_refs:
        missing = sorted(set(evidence_ids) - seen_evidence)
        if missing:
            errors.append(f"unknown evidence IDs in {finding_path}: {', '.join(missing)}")
        if is_enum_value(verdict, {"verified", "corroborated"}):
            verifier_task = task_records.get(verifier_task_id) if isinstance(verifier_task_id, str) else None
            verifier_evidence = [
                evidence_id
                for evidence_id in evidence_ids
                if evidence_owners.get(evidence_id) == verifier_task_id
                and finding_id in evidence_supports.get(evidence_id, set())
            ]
            if (
                verifier_task is None
                or verifier_task_id == origin_task_id
                or task_safety(verifier_task).get("task_class") != "verification"
                or verifier_task.get("status") != "completed"
                or origin_task_id not in task_dependencies(verifier_task)
                or not verifier_evidence
            ):
                errors.append(
                    f"{verdict} finding requires an independent verifier with completed artifacts and cited verifier evidence: "
                    f"{finding_path}"
                )

    if microarchitecture_profile:
        validate_microarchitecture_artifacts(
            run_root,
            state,
            run_snapshot,
            task_records,
            evidence_artifact_refs,
            seen_evidence,
            errors,
        )
    elif (
        (run_root / "experiments").exists()
        or (run_root / "artifacts" / "manifest.jsonl").exists()
        or evidence_artifact_refs
    ):
        errors.append("experiment contracts and generated artifacts require research_profile microarchitecture-security")

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
                if not isinstance(event, dict):
                    continue
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
                if not isinstance(original_id, str):
                    continue
                count = policy_fallback_links.count((original_id, fallback_id))
                if count != 1:
                    errors.append(f"fallback task {fallback_id} must be linked by exactly one policy event")
                original_task = task_records.get(original_id)
                if not isinstance(original_task, dict):
                    continue
                for field in ("objective", "research_question"):
                    original_text = normalize_contract_text(original_task.get(field))
                    fallback_text = normalize_contract_text(fallback_task.get(field))
                    if original_text and fallback_text == original_text:
                        errors.append(f"fallback task {fallback_id} must materially change its {field}")
                original_safety = original_task.get("safety", {})
                fallback_safety = fallback_task.get("safety", {})
                if (
                    isinstance(original_safety, dict)
                    and original_safety.get("capability_boundary") == "active_authorized"
                    and (
                        not isinstance(fallback_safety, dict)
                        or fallback_safety.get("capability_boundary") != "non_operational"
                    )
                ):
                    errors.append(f"fallback task {fallback_id} for blocked active work must be non_operational")

    if schema_version >= 3:
        conflict_path = resolve_run_path(run_dir, state.get("conflicts_file"), "conflicts_file", errors)
        if conflict_path is not None:
            conflicts = load_json(conflict_path, errors)
            if conflicts is LOAD_FAILED:
                pass
            elif not isinstance(conflicts, list):
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
                    if not is_enum_value(status, CONFLICT_STATUSES):
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
                        verifier_dependencies = {
                            dependency
                            for dependency in task_dependencies(verifier_task)
                            if isinstance(dependency, str)
                        }
                        if (
                            verifier_task is None
                            or verifier in conflict_tasks
                            or task_safety(verifier_task).get("task_class") != "verification"
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
        if not isinstance(composition, dict) or any(composition.get(key) is not True for key in COMPOSITION_REQUIRED):
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
            if not is_enum_value(task.get("status"), TERMINAL_TASK_STATUSES):
                errors.append(f"completed run has non-terminal task: {task_id}")
        if schema_version == 3:
            validate_completed_run_package(
                run_root,
                state,
                task_records,
                seen_evidence,
                evidence_supports,
                finding_verdicts,
                errors,
            )

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
