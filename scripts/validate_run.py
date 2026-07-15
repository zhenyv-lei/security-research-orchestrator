#!/usr/bin/env python3
"""Validate security-research-orchestrator run artifacts with stdlib only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


RUN_REQUIRED = {
    "schema_version",
    "run_id",
    "objective",
    "research_profile",
    "scope",
    "authorization_tier",
    "authorization",
    "active_testing_approved",
    "allowed_actions",
    "prohibited_actions",
    "completion_criteria",
    "task_ids",
    "task_graph",
    "artifact_roots",
    "resume",
    "composition_review",
    "status",
    "updated_at",
}
TASK_REQUIRED = {
    "schema_version",
    "task_id",
    "role",
    "phase",
    "execution_mode",
    "objective",
    "research_question",
    "dependencies",
    "assigned_paths",
    "inputs",
    "target_snapshot",
    "resource_requirements",
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
    "schema_version",
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
TARGET_CLASSES = {"static-rtl", "formal-model", "cycle-simulator", "fpga", "silicon", "software"}
AUTHORIZATION_TIERS = {"A0", "A1", "A2"}
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


def is_safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def snapshot_identity(snapshot: Any) -> tuple[Any, Any, Any] | None:
    if not isinstance(snapshot, dict):
        return None
    return snapshot.get("commit"), snapshot.get("rtl_config"), snapshot.get("target_class")


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
    require_pinned: bool = False,
) -> None:
    if not isinstance(snapshot, dict):
        errors.append(f"target_snapshot must be an object in {path}")
        return
    target_class = snapshot.get("target_class")
    if target_class not in TARGET_CLASSES:
        errors.append(f"invalid target_class in {path}: {target_class}")
    if require_pinned:
        for key in ("commit", "rtl_config"):
            if not isinstance(snapshot.get(key), str) or not snapshot.get(key):
                errors.append(f"executable microarchitecture task requires target_snapshot.{key} in {path}")


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
    for key in ("edges", "waves", "exclusive_resources"):
        if not isinstance(graph.get(key), list):
            errors.append(f"task_graph.{key} must be a list in {state_path}")

    task_ids = set(tasks)
    edges = graph.get("edges", [])
    parsed_edges: set[tuple[str, str]] = set()
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, list) or len(edge) != 2 or any(item not in task_ids for item in edge):
                errors.append(f"invalid task graph edge in {state_path}: {edge}")
                continue
            parsed_edges.add((edge[0], edge[1]))
    expected_edges = {
        (dependency, task_id)
        for task_id, task in tasks.items()
        for dependency in task.get("dependencies", [])
        if dependency in task_ids
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
            if dependency in tasks:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)

    waves = graph.get("waves", [])
    wave_index: dict[str, int] = {}
    all_exclusive_resources: set[str] = set()
    if isinstance(waves, list):
        for index, wave in enumerate(waves):
            if not isinstance(wave, list):
                errors.append(f"task graph wave {index} must be a list")
                continue
            resources: set[str] = set()
            assigned_paths: set[str] = set()
            for task_id in wave:
                if task_id not in task_ids:
                    errors.append(f"unknown task in wave {index}: {task_id}")
                    continue
                if task_id in wave_index:
                    errors.append(f"task appears in multiple waves: {task_id}")
                wave_index[task_id] = index
                requirements = tasks[task_id].get("resource_requirements", {})
                exclusive = requirements.get("exclusive_resources", []) if isinstance(requirements, dict) else []
                for resource in exclusive if isinstance(exclusive, list) else []:
                    if resource in resources:
                        errors.append(f"exclusive resource {resource} is shared in wave {index}")
                    resources.add(resource)
                    all_exclusive_resources.add(resource)
                task_paths = tasks[task_id].get("assigned_paths", [])
                for assigned_path in task_paths if isinstance(task_paths, list) else []:
                    if assigned_path in assigned_paths:
                        errors.append(f"assigned path {assigned_path} is shared in wave {index}")
                    assigned_paths.add(assigned_path)
    if task_ids and set(wave_index) != task_ids:
        errors.append("task_graph.waves must schedule every task exactly once")
    for dependency, dependent in expected_edges:
        if dependency in wave_index and dependent in wave_index and wave_index[dependency] >= wave_index[dependent]:
            errors.append(f"dependency {dependency} must precede {dependent} in task_graph.waves")
    declared_resources = graph.get("exclusive_resources", [])
    if isinstance(declared_resources, list) and set(declared_resources) != all_exclusive_resources:
        errors.append("task_graph.exclusive_resources must equal the resources declared by tasks")


def validate_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    state_path = run_dir / "run-state.json"
    state = load_json(state_path, errors)
    if state is None:
        return errors
    require_keys(state, RUN_REQUIRED, state_path, errors)

    if state.get("status") not in RUN_STATUSES:
        errors.append(f"invalid run status in {state_path}: {state.get('status')}")
    if state.get("authorization_tier") not in AUTHORIZATION_TIERS:
        errors.append(f"invalid authorization tier in {state_path}: {state.get('authorization_tier')}")
    if state.get("authorization_tier") == "A0" and state.get("active_testing_approved") is True:
        errors.append("A0 runs cannot approve active testing")
    task_ids = state.get("task_ids", []) if isinstance(state, dict) else []
    if not isinstance(task_ids, list) or any(not isinstance(item, str) for item in task_ids):
        errors.append("run-state.json task_ids must be a list of strings")
        return errors
    if len(task_ids) != len(set(task_ids)):
        errors.append("run-state.json task_ids must be unique")

    scope = state.get("scope")
    run_snapshot: Any = None
    if not isinstance(scope, dict):
        errors.append(f"scope must be an object in {state_path}")
    elif state.get("research_profile") == "microarchitecture-security":
        run_snapshot = scope.get("target_snapshot")
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
    elif state.get("authorization_tier") == "A2" or state.get("active_testing_approved") is True:
        for key in ("owner", "time_window", "rollback_plan", "data_handling", "output_audience"):
            if not authorization.get(key):
                errors.append(f"active testing requires authorization.{key} in {state_path}")
        if not authorization.get("evidence") or not authorization.get("method_classes"):
            errors.append(f"active testing requires authorization evidence and method classes in {state_path}")

    artifact_roots = state.get("artifact_roots")
    required_roots = {"tasks", "experiments", "artifacts"}
    if not isinstance(artifact_roots, dict) or not required_roots.issubset(artifact_roots):
        errors.append(f"artifact_roots must define tasks, experiments, and artifacts in {state_path}")
    elif any(not is_safe_relative_path(artifact_roots[key]) for key in required_roots):
        errors.append(f"artifact_roots must contain safe relative paths in {state_path}")

    resume = state.get("resume")
    resume_lists = {"completed_tasks", "retryable_tasks", "blocked_tasks", "next_actions"}
    if not isinstance(resume, dict) or not resume_lists.issubset(resume):
        errors.append(f"resume must define checkpoint and task/action lists in {state_path}")
    else:
        for key in ("completed_tasks", "retryable_tasks", "blocked_tasks"):
            value = resume.get(key)
            if not isinstance(value, list) or any(item not in task_ids for item in value):
                errors.append(f"resume.{key} contains an unknown or malformed task ID")

    tasks: dict[str, dict[str, Any]] = {}
    seen_evidence: set[str] = set()
    evidence_supports_by_task: dict[str, set[str]] = {}
    evidence_artifact_refs: list[tuple[Path, str]] = []
    finding_refs: list[tuple[Path, list[str]]] = []
    verified_findings: list[tuple[Path, dict[str, Any]]] = []

    for task_id in task_ids:
        task_dir = run_dir / "tasks" / task_id
        task_path = task_dir / "task.json"
        task = load_json(task_path, errors)
        if task is None:
            continue
        require_keys(task, TASK_REQUIRED, task_path, errors)
        if task.get("task_id") != task_id:
            errors.append(f"task ID mismatch in {task_path}")
        tasks[task_id] = task
        status = task.get("status")
        if status not in ALL_TASK_STATUSES:
            errors.append(f"invalid task status in {task_path}: {status}")
        dependencies = task.get("dependencies", [])
        if not isinstance(dependencies, list) or any(dep not in task_ids for dep in dependencies):
            errors.append(f"unknown or malformed dependency in {task_path}")
        if task_id in dependencies:
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
        resources = task.get("resource_requirements")
        if not isinstance(resources, dict) or not isinstance(resources.get("exclusive_resources"), list):
            errors.append(f"invalid resource_requirements in {task_path}")
        profile = state.get("research_profile")
        executable = task.get("execution_mode") not in {"read-only", "passive-research"}
        task_snapshot = task.get("target_snapshot")
        if task_snapshot is not None or profile == "microarchitecture-security":
            validate_target_snapshot(
                task_snapshot,
                task_path,
                errors,
                require_pinned=profile == "microarchitecture-security" and executable,
            )
        if profile == "microarchitecture-security" and snapshot_identity(task_snapshot) != snapshot_identity(run_snapshot):
            errors.append(f"task target snapshot differs from run snapshot in {task_path}")

        if status == "completed":
            expected_outputs = task.get("expected_outputs", [])
            if isinstance(expected_outputs, list):
                for output in expected_outputs:
                    if not is_safe_relative_path(output) or not (task_dir / output).exists():
                        errors.append(f"completed task is missing expected output {output!r} in {task_dir}")

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
                supports = record.get("supports")
                if isinstance(supports, list):
                    evidence_supports_by_task.setdefault(task_id, set()).update(
                        item for item in supports if isinstance(item, str)
                    )
                artifact_id = record.get("artifact_id")
                if isinstance(artifact_id, str):
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
            if not isinstance(evidence_ids, list):
                errors.append(f"evidence_ids must be a list in {finding_path}")
            else:
                finding_refs.append((finding_path, evidence_ids))
            if verdict == "verified":
                verified_findings.append((finding_path, finding))

    if isinstance(resume, dict):
        expected_resume_statuses = {
            "completed_tasks": {"completed"},
            "retryable_tasks": {"retryable_error"},
            "blocked_tasks": {
                "incomplete",
                "needs_input",
                "needs_authorization",
                "blocked_technical",
                "policy_blocked",
            },
        }
        for key, statuses in expected_resume_statuses.items():
            for task_id in resume.get(key, []) if isinstance(resume.get(key), list) else []:
                if task_id in tasks and tasks[task_id].get("status") not in statuses:
                    errors.append(f"resume.{key} disagrees with task status for {task_id}")

    validate_task_graph(state, tasks, state_path, errors)

    experiment_ids: set[str] = set()
    experiment_artifact_refs: list[tuple[Path, str, list[str]]] = []
    completed_experiment_ids: set[str] = set()
    experiments_root = run_dir / "experiments"
    if experiments_root.exists():
        for experiment_path in sorted(experiments_root.glob("*/experiment.json")):
            experiment = load_json(experiment_path, errors)
            if experiment is None:
                continue
            require_keys(experiment, EXPERIMENT_REQUIRED, experiment_path, errors)
            experiment_id = experiment.get("experiment_id")
            if experiment_id in experiment_ids:
                errors.append(f"duplicate experiment_id: {experiment_id}")
            if isinstance(experiment_id, str):
                experiment_ids.add(experiment_id)
            if experiment.get("task_id") not in tasks:
                errors.append(f"unknown experiment task in {experiment_path}")
            if experiment.get("status") not in EXPERIMENT_STATUSES:
                errors.append(f"invalid experiment status in {experiment_path}: {experiment.get('status')}")
            if not isinstance(experiment.get("revision"), int) or experiment.get("revision", 0) < 1:
                errors.append(f"invalid experiment revision in {experiment_path}")
            if not isinstance(experiment.get("hypothesis"), str) or not experiment.get("hypothesis").strip():
                errors.append(f"experiment hypothesis must be non-empty in {experiment_path}")
            variables = experiment.get("variables")
            required_variables = {"independent", "dependent", "controlled", "nuisance"}
            if not isinstance(variables, dict) or not required_variables.issubset(variables):
                errors.append(f"invalid experiment variables in {experiment_path}")
            elif any(not isinstance(variables[key], list) for key in required_variables):
                errors.append(f"experiment variable groups must be lists in {experiment_path}")
            elif any(not variables[key] for key in ("independent", "dependent", "controlled")):
                errors.append(f"experiment independent, dependent, and controlled variables must be non-empty in {experiment_path}")
            for key in (
                "workloads",
                "controls",
                "observables",
                "command_plan",
                "expected_artifacts",
                "acceptance_criteria",
                "inconclusive_criteria",
                "resource_exhaustion_criteria",
                "stop_conditions",
            ):
                if not isinstance(experiment.get(key), list) or not experiment.get(key):
                    errors.append(f"experiment {key} must be a non-empty list in {experiment_path}")
            seed_policy = experiment.get("seed_policy")
            if (
                not isinstance(seed_policy, dict)
                or not isinstance(seed_policy.get("repetitions"), int)
                or seed_policy.get("repetitions", 0) < 1
            ):
                errors.append(f"invalid seed policy in {experiment_path}")
            elif seed_policy.get("mode") == "fixed-list" and not seed_policy.get("seeds"):
                errors.append(f"fixed-list seed policy requires at least one seed in {experiment_path}")
            elif seed_policy.get("mode") not in {"fixed-list", "deterministic"}:
                errors.append(f"unsupported seed policy mode in {experiment_path}: {seed_policy.get('mode')}")
            experiment_snapshot = experiment.get("target_snapshot")
            validate_target_snapshot(experiment_snapshot, experiment_path, errors, require_pinned=True)
            if snapshot_identity(experiment_snapshot) != snapshot_identity(run_snapshot):
                errors.append(f"experiment target snapshot differs from run snapshot in {experiment_path}")
            expected_artifacts = experiment.get("expected_artifacts")
            if experiment.get("status") == "completed" and isinstance(experiment_id, str):
                completed_experiment_ids.add(experiment_id)
            if experiment.get("status") == "completed" and isinstance(expected_artifacts, list):
                experiment_artifact_refs.append(
                    (experiment_path, experiment_id, [item for item in expected_artifacts if isinstance(item, str)])
                )

    artifact_ids: set[str] = set()
    artifact_experiments: dict[str, Any] = {}
    manifest_path = run_dir / "artifacts" / "manifest.jsonl"
    if manifest_path.exists():
        for line_no, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                artifact = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSONL {manifest_path}:{line_no}: {exc}")
                continue
            require_keys(artifact, ARTIFACT_REQUIRED, manifest_path, errors)
            artifact_id = artifact.get("artifact_id")
            if artifact_id in artifact_ids:
                errors.append(f"duplicate artifact_id: {artifact_id}")
            if isinstance(artifact_id, str):
                artifact_ids.add(artifact_id)
                artifact_experiments[artifact_id] = artifact.get("experiment_id")
            if artifact.get("producer_task_id") not in tasks:
                errors.append(f"unknown artifact producer at {manifest_path}:{line_no}")
            experiment_id = artifact.get("experiment_id")
            if experiment_id is not None and experiment_id not in experiment_ids:
                errors.append(f"unknown artifact experiment at {manifest_path}:{line_no}")
            artifact_path_value = artifact.get("path")
            if not is_safe_relative_path(artifact_path_value):
                errors.append(f"unsafe artifact path at {manifest_path}:{line_no}")
                artifact_path = None
            else:
                artifact_path = (run_dir / artifact_path_value).resolve()
                try:
                    artifact_path.relative_to(run_dir.resolve())
                except ValueError:
                    errors.append(f"artifact path escapes run directory at {manifest_path}:{line_no}")
                    artifact_path = None
                if artifact_path is not None and not artifact_path.is_file():
                    errors.append(f"manifest artifact does not exist at {manifest_path}:{line_no}: {artifact_path_value}")
            hash_value = artifact.get("hash")
            if (
                not isinstance(hash_value, str)
                or not hash_value.startswith("sha256:")
                or len(hash_value) != 71
            ):
                errors.append(f"artifact requires a populated sha256 hash at {manifest_path}:{line_no}")
            elif artifact_path is not None and artifact_path.is_file() and file_sha256(artifact_path) != hash_value:
                errors.append(f"artifact hash mismatch at {manifest_path}:{line_no}")
            artifact_snapshot = artifact.get("target_snapshot")
            validate_target_snapshot(artifact_snapshot, manifest_path, errors, require_pinned=True)
            if snapshot_identity(artifact_snapshot) != snapshot_identity(run_snapshot):
                errors.append(f"artifact target snapshot differs from run snapshot at {manifest_path}:{line_no}")
            if not isinstance(artifact.get("generated_at"), str) or not artifact.get("generated_at"):
                errors.append(f"artifact generated_at must be non-empty at {manifest_path}:{line_no}")

    for experiment_path, experiment_id, expected_artifacts in experiment_artifact_refs:
        missing = sorted(set(expected_artifacts) - artifact_ids)
        if missing:
            errors.append(f"unknown expected artifact IDs in {experiment_path}: {', '.join(missing)}")
        for artifact_id in set(expected_artifacts) & artifact_ids:
            if artifact_experiments.get(artifact_id) != experiment_id:
                errors.append(f"artifact {artifact_id} is owned by a different experiment than {experiment_id}")

    for evidence_path, artifact_id in evidence_artifact_refs:
        if artifact_id not in artifact_ids:
            errors.append(f"unknown artifact ID referenced in {evidence_path}: {artifact_id}")

    for finding_path, evidence_ids in finding_refs:
        missing = sorted(set(evidence_ids) - seen_evidence)
        if missing:
            errors.append(f"unknown evidence IDs in {finding_path}: {', '.join(missing)}")

    for finding_path, finding in verified_findings:
        verifier_task_id = finding.get("verifier_task_id")
        if verifier_task_id not in tasks or verifier_task_id == finding.get("task_id"):
            errors.append(f"verified finding requires a distinct verifier task in {finding_path}")
            continue
        verifier = tasks[verifier_task_id]
        if verifier.get("role") != "verification" or verifier.get("status") != "completed":
            errors.append(f"verified finding requires a completed verification-role task in {finding_path}")
        finding_id = finding.get("finding_id")
        if finding_id not in evidence_supports_by_task.get(verifier_task_id, set()):
            errors.append(f"verifier evidence must independently support {finding_id} in {finding_path}")

    if (completed_experiment_ids or evidence_artifact_refs) and not manifest_path.is_file():
        errors.append("completed experiments or artifact-backed evidence require artifacts/manifest.jsonl")

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
        for task_id, task in tasks.items():
            if task.get("status") not in TERMINAL_TASK_STATUSES:
                errors.append(f"completed run has non-terminal task: {task_id}")
        final_report_path = run_dir / "final" / "final-report.md"
        if not final_report_path.is_file():
            errors.append("completed run requires final/final-report.md")
        else:
            final_report = final_report_path.read_text(encoding="utf-8")
            missing_headings = sorted(heading for heading in FINAL_REQUIRED_HEADINGS if heading not in final_report)
            if missing_headings:
                errors.append(f"final report is missing required headings: {', '.join(missing_headings)}")

        evidence_index_path = run_dir / "evidence-index.json"
        evidence_index = load_json(evidence_index_path, errors)
        if isinstance(evidence_index, dict):
            records = evidence_index.get("records")
            if not isinstance(records, list):
                errors.append(f"evidence-index records must be a list in {evidence_index_path}")
            else:
                indexed_ids = {
                    record.get("evidence_id")
                    for record in records
                    if isinstance(record, dict) and isinstance(record.get("evidence_id"), str)
                }
                if indexed_ids != seen_evidence:
                    errors.append("evidence-index.json must index every evidence ID exactly once")
                if len(indexed_ids) != len(records):
                    errors.append("evidence-index.json contains duplicate or malformed records")

        conflicts_path = run_dir / "conflicts.json"
        conflicts = load_json(conflicts_path, errors)
        if not isinstance(conflicts, dict) or not isinstance(conflicts.get("conflicts"), list):
            errors.append(f"conflicts must be a list in {conflicts_path}")

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
