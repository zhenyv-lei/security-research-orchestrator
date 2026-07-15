#!/usr/bin/env python3
"""Validate security-research-orchestrator run artifacts with stdlib only."""

from __future__ import annotations

import argparse
import hashlib
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
MICROARCH_RUN_REQUIRED = {"research_profile", "authorization", "task_graph", "artifact_roots", "resume"}
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
    "kind",
    "path",
    "hash",
    "target_snapshot",
    "tool_versions",
    "workload_ids",
    "seed",
    "generated_at",
    "sensitivity",
    "retention",
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
    "## Scope and Authorization",
    "## Design Snapshot and Reproducibility",
    "## Experiment Matrix and Artifact Coverage",
    "## Conflicts, Blocks, and Limitations",
    "## Claim-to-Evidence Matrix",
}


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
    if snapshot.get("target_class") not in TARGET_CLASSES:
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
    task_ids: list[str],
    errors: list[str],
) -> Any:
    require_keys(state, MICROARCH_RUN_REQUIRED, state_path, errors)
    scope = state.get("scope")
    run_snapshot = scope.get("target_snapshot") if isinstance(scope, dict) else None
    validate_target_snapshot(run_snapshot, state_path, errors, require_pinned=True)

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
    elif state.get("active_testing_approved") is True:
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
    if not isinstance(artifact_roots, dict) or any(artifact_roots.get(key) != value for key, value in expected_roots.items()):
        errors.append(f"microarchitecture artifact_roots must use tasks, experiments, and artifacts in {state_path}")

    resume = state.get("resume")
    resume_lists = {"completed_tasks", "retryable_tasks", "blocked_tasks", "next_actions"}
    if not isinstance(resume, dict) or not resume_lists.issubset(resume):
        errors.append(f"resume must define checkpoint and task/action lists in {state_path}")
    elif any(
        not isinstance(resume.get(key), list) or any(item not in task_ids for item in resume.get(key, []))
        for key in ("completed_tasks", "retryable_tasks", "blocked_tasks")
    ):
        errors.append(f"resume contains an unknown or malformed task ID in {state_path}")
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
        parsed_edges.add((edge[0], edge[1]))
    expected_edges = {
        (dependency, task_id)
        for task_id, task in tasks.items()
        for dependency in task.get("dependencies", [])
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
        for dependency in tasks[task_id].get("dependencies", []):
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
    if not isinstance(graph_resources, list) or any(not isinstance(item, str) for item in graph_resources):
        errors.append("task_graph.exclusive_resources must be a list of strings")
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
            if experiment is None:
                continue
            require_keys(experiment, EXPERIMENT_REQUIRED, experiment_path, errors)
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

            task_id = experiment.get("task_id")
            task = tasks.get(task_id) if isinstance(task_id, str) else None
            if task is None:
                errors.append(f"unknown experiment task in {experiment_path}")
            else:
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

            if experiment.get("status") not in EXPERIMENT_STATUSES:
                errors.append(f"invalid experiment status in {experiment_path}: {experiment.get('status')}")
            if not isinstance(experiment.get("revision"), int) or experiment.get("revision", 0) < 1:
                errors.append(f"invalid experiment revision in {experiment_path}")
            if not isinstance(experiment.get("hypothesis"), str) or not experiment.get("hypothesis").strip():
                errors.append(f"experiment hypothesis must be non-empty in {experiment_path}")

            variables = experiment.get("variables")
            variable_fields = {"independent", "dependent", "controlled", "nuisance"}
            if not isinstance(variables, dict) or not variable_fields.issubset(variables):
                errors.append(f"invalid experiment variables in {experiment_path}")
            elif any(not isinstance(variables[field], list) for field in variable_fields):
                errors.append(f"experiment variable groups must be lists in {experiment_path}")
            elif any(not variables[field] for field in ("independent", "dependent", "controlled")):
                errors.append(
                    f"experiment independent, dependent, and controlled variables must be non-empty in {experiment_path}"
                )

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
                ):
                    errors.append(f"experiment {field} must be a non-empty list in {experiment_path}")

            seed_policy = experiment.get("seed_policy")
            if (
                not isinstance(seed_policy, dict)
                or not isinstance(seed_policy.get("repetitions"), int)
                or seed_policy.get("repetitions", 0) < 1
            ):
                errors.append(f"invalid seed policy in {experiment_path}")
            elif seed_policy.get("mode") == "fixed-list" and not seed_policy.get("seeds"):
                errors.append(f"fixed-list seed policy requires at least one seed in {experiment_path}")
            elif seed_policy.get("mode") == "fixed-list" and (
                not isinstance(seed_policy.get("seeds"), list)
                or any(not isinstance(seed, int) for seed in seed_policy.get("seeds", []))
                or len(seed_policy.get("seeds", [])) != len(set(seed_policy.get("seeds", [])))
            ):
                errors.append(f"fixed-list seed policy requires unique integer seeds in {experiment_path}")
            elif seed_policy.get("mode") not in {"fixed-list", "deterministic"}:
                errors.append(f"unsupported seed policy mode in {experiment_path}: {seed_policy.get('mode')}")

            budget = experiment.get("resource_budget")
            budget_fields = {"cpu", "memory_gb", "wall_time_minutes", "storage_gb", "exclusive_resources"}
            if not isinstance(budget, dict) or not budget_fields.issubset(budget):
                errors.append(f"invalid experiment resource_budget in {experiment_path}")
            elif (
                not isinstance(budget.get("exclusive_resources"), list)
                or any(not isinstance(item, str) or not item.strip() for item in budget.get("exclusive_resources", []))
                or any(
                    value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0)
                    for value in (budget.get("cpu"), budget.get("memory_gb"), budget.get("wall_time_minutes"), budget.get("storage_gb"))
                )
            ):
                errors.append(f"malformed experiment resource_budget in {experiment_path}")
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

    artifact_ids: set[str] = set()
    artifact_experiments: dict[str, Any] = {}
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
            if artifact.get("schema_version") != 3:
                errors.append(f"artifact must use schema_version 3 at {manifest_path}:{line_no}")
            artifact_id = artifact.get("artifact_id")
            if not isinstance(artifact_id, str) or not artifact_id.strip() or artifact_id in artifact_ids:
                errors.append(f"invalid or duplicate artifact_id at {manifest_path}:{line_no}")
            else:
                artifact_ids.add(artifact_id)
                artifact_experiments[artifact_id] = artifact.get("experiment_id")

            producer = artifact.get("producer_task_id")
            if producer not in tasks:
                errors.append(f"unknown artifact producer at {manifest_path}:{line_no}")
            experiment_id = artifact.get("experiment_id")
            experiment = experiments.get(experiment_id) if isinstance(experiment_id, str) else None
            if experiment is None:
                errors.append(f"unknown artifact experiment at {manifest_path}:{line_no}")
            elif producer != experiment.get("task_id"):
                errors.append(f"artifact producer differs from experiment owner at {manifest_path}:{line_no}")

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
            elif isinstance(artifact_snapshot, dict) and workload_ids != artifact_snapshot.get("workloads"):
                errors.append(f"artifact workload_ids differ from target snapshot at {manifest_path}:{line_no}")
            if not isinstance(artifact.get("generated_at"), str) or not artifact.get("generated_at").strip():
                errors.append(f"artifact generated_at must be non-empty at {manifest_path}:{line_no}")

    for experiment_path, experiment_id, expected in expected_artifacts_by_experiment:
        missing = sorted(set(expected) - artifact_ids)
        if missing:
            errors.append(f"unknown expected artifact IDs in {experiment_path}: {', '.join(missing)}")
        for artifact_id in set(expected) & artifact_ids:
            if artifact_experiments.get(artifact_id) != experiment_id:
                errors.append(f"artifact {artifact_id} is owned by a different experiment than {experiment_id}")

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

    if state.get("status") == "completed":
        evidence_index_path = run_root / "evidence-index.json"
        evidence_index = load_json(evidence_index_path, errors)
        if isinstance(evidence_index, dict):
            if evidence_index.get("schema_version") != 3:
                errors.append(f"evidence-index must use schema_version 3 in {evidence_index_path}")
            records = evidence_index.get("records")
            if not isinstance(records, list):
                errors.append(f"evidence-index records must be a list in {evidence_index_path}")
            else:
                indexed_ids = [
                    record.get("evidence_id")
                    for record in records
                    if isinstance(record, dict) and isinstance(record.get("evidence_id"), str)
                ]
                if set(indexed_ids) != seen_evidence:
                    errors.append("evidence-index.json must index every evidence ID exactly once")
                if len(indexed_ids) != len(set(indexed_ids)) or len(indexed_ids) != len(records):
                    errors.append("evidence-index.json contains duplicate or malformed records")

        final_report_path = run_root / "final" / "final-report.md"
        if final_report_path.is_file():
            final_report = final_report_path.read_text(encoding="utf-8")
            missing_headings = sorted(heading for heading in FINAL_REQUIRED_HEADINGS if heading not in final_report)
            if missing_headings:
                errors.append(f"final report is missing required headings: {', '.join(missing_headings)}")


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

    if state.get("status") not in RUN_STATUSES:
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
    if microarchitecture_profile:
        run_snapshot = validate_microarchitecture_state(state, state_path, task_ids, errors)

    seen_evidence: set[str] = set()
    evidence_owners: dict[str, str] = {}
    evidence_artifact_refs: list[tuple[Path, str]] = []
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
        if microarchitecture_profile:
            require_keys(task, MICROARCH_TASK_REQUIRED, task_path, errors)
            if task.get("schema_version") != 3:
                errors.append(f"microarchitecture task must use schema_version 3 in {task_path}")
            resources = task.get("resource_requirements")
            resource_fields = {"cpu", "memory_gb", "wall_time_minutes", "exclusive_resources"}
            if not isinstance(resources, dict) or not resource_fields.issubset(resources):
                errors.append(f"invalid resource_requirements in {task_path}")
            elif (
                not isinstance(resources.get("exclusive_resources"), list)
                or any(
                    not isinstance(item, str) or not item.strip()
                    for item in resources.get("exclusive_resources", [])
                )
                or any(
                    value is not None
                    and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0)
                    for value in (
                        resources.get("cpu"),
                        resources.get("memory_gb"),
                        resources.get("wall_time_minutes"),
                    )
                )
            ):
                errors.append(f"malformed resource_requirements in {task_path}")
            if task.get("execution_mode") not in MICROARCH_EXECUTION_MODES:
                errors.append(f"invalid microarchitecture execution_mode in {task_path}: {task.get('execution_mode')}")
            task_snapshot = task.get("target_snapshot")
            validate_target_snapshot(task_snapshot, task_path, errors, require_pinned=True)
            if snapshot_identity(task_snapshot) != snapshot_identity(run_snapshot):
                errors.append(f"task target snapshot differs from run snapshot in {task_path}")
            expected_target_classes = EXECUTION_TARGET_CLASSES.get(task.get("execution_mode"))
            if (
                expected_target_classes
                and isinstance(task_snapshot, dict)
                and task_snapshot.get("target_class") not in expected_target_classes
            ):
                errors.append(f"execution_mode and target_class disagree in {task_path}")
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
        elif task_id in dependencies:
            errors.append(f"task cannot depend on itself in {task_path}")
        attempts = task.get("attempts")
        max_attempts = task.get("max_attempts")
        if (
            not isinstance(attempts, int)
            or not isinstance(max_attempts, int)
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
                    if not isinstance(approval, dict):
                        approval = {}
                    if approval_ref != approval.get("approval_id"):
                        errors.append(f"active task approval_ref mismatch in {task_path}")
                    approved_task_ids = approval.get("approved_task_ids", [])
                    if not isinstance(approved_task_ids, list) or task_id not in approved_task_ids:
                        errors.append(f"active task absent from approved_task_ids in {task_path}")
                if schema_version >= 3 and boundary == "non_operational" and approval_ref is not None:
                    errors.append(f"non_operational task must have null approval_ref in {task_path}")
                if not isinstance(composition_dependencies, list) or any(
                    dep not in task_ids for dep in composition_dependencies
                ):
                    errors.append(f"unknown or malformed composition dependency in {task_path}")
                executable = task.get("execution_mode") not in {"read-only", "passive-research"}
                if microarchitecture_profile and executable and task_class != "active_validation":
                    errors.append(f"executable microarchitecture task must use active_validation in {task_path}")
                if microarchitecture_profile and task_class == "active_validation" and not executable:
                    errors.append(f"active_validation microarchitecture task requires an executable mode in {task_path}")
                if (
                    microarchitecture_profile
                    and task.get("execution_mode") in {"fpga", "silicon"}
                    and state.get("authorization_tier") != "A2"
                ):
                    errors.append(f"fpga or silicon execution requires authorization tier A2 in {task_path}")
                allowed_actions = task.get("allowed_actions")
                if not isinstance(allowed_actions, list) or any(
                    not isinstance(action, str) for action in allowed_actions
                ):
                    errors.append(f"allowed_actions must be a list of strings in {task_path}")
                elif isinstance(active_actions, list) and not set(active_actions).issubset(allowed_actions):
                    errors.append(f"active_actions must be declared in allowed_actions in {task_path}")

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
                artifact_id = record.get("artifact_id")
                if (
                    microarchitecture_profile
                    and record.get("kind") in GENERATED_EVIDENCE_KINDS
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

    if microarchitecture_profile:
        validate_task_graph(state, task_records, state_path, errors)
        resume = state.get("resume", {})
        expected_resume_statuses = {
            "completed_tasks": {"completed"},
            "retryable_tasks": {"retryable_error"},
            "blocked_tasks": TERMINAL_TASK_STATUSES - {"completed", "cancelled"},
        }
        if isinstance(resume, dict):
            for field, statuses in expected_resume_statuses.items():
                for task_id in resume.get(field, []) if isinstance(resume.get(field), list) else []:
                    if task_id in task_records and task_records[task_id].get("status") not in statuses:
                        errors.append(f"resume.{field} disagrees with task status for {task_id}")

    for task_id, task in task_records.items():
        if task.get("status") == "completed":
            validate_completed_task_outputs(run_root, task_id, task, errors)

    if schema_version >= 3:
        active_approval = state.get("active_testing_approval", {})
        if isinstance(active_approval, dict) and active_approval.get("approved") is True:
            approval_id = active_approval.get("approval_id")
            approved_task_ids = active_approval.get("approved_task_ids", [])
            for approved_task_id in approved_task_ids if isinstance(approved_task_ids, list) else []:
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
