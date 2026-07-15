#!/usr/bin/env python3
"""Regression fixtures for the staged security-research-orchestrator skill."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from preflight_tasks import preflight  # noqa: E402
from validate_run import validate_run  # noqa: E402


def approval_packet(approved: bool = False, task_ids: list[str] | None = None) -> dict:
    values = {
        "approval_id": "APR-001" if approved else "",
        "approved": approved,
        "approved_task_ids": task_ids or [],
        "target": "local fixture" if approved else "",
        "owner": "fixture owner" if approved else "",
        "authorization_source": "written fixture approval" if approved else "",
        "method_class": "bounded local validation" if approved else "",
        "time_window": "2026-07-15T00:00:00Z/2026-07-15T01:00:00Z" if approved else "",
        "rate_limits": "one action" if approved else "",
        "mutation": "temporary fixture only" if approved else "",
        "expected_traffic_or_side_effects": "local fixture write" if approved else "",
        "containment": "temporary directory" if approved else "",
        "rollback": "delete temporary directory" if approved else "",
        "sensitive_data_exposure": "none" if approved else "",
        "stop_conditions": ["unexpected side effect"] if approved else [],
    }
    return values


def task(task_id: str, task_class: str = "context_map", dependencies: list[str] | None = None) -> dict:
    synthesis = task_class == "synthesis"
    return {
        "schema_version": 3,
        "task_id": task_id,
        "role": "synthesis" if synthesis else "context",
        "objective": "Establish one bounded evidence claim.",
        "research_question": "Which source artifact establishes the configured ownership boundary?",
        "dependencies": dependencies or [],
        "assigned_paths": ["final"] if synthesis else [f"tasks/{task_id}"],
        "inputs": ["repo@commit"],
        "allowed_actions": ["read local artifacts"],
        "prohibited_actions": ["active testing"],
        "expected_outputs": ["final/final-report.md"] if synthesis else ["report.md"],
        "acceptance_criteria": ["one cited claim"],
        "evidence_requirements": ["stable locator"],
        "stop_conditions": ["scope ambiguity"],
        "escalation_conditions": ["missing source"],
        "safety": {
            "purpose": "defensive",
            "task_class": task_class,
            "capability_boundary": "non_operational",
            "resource_scope": ["configured ownership boundary"],
            "evidence_goal": "Cite the configured ownership boundary.",
            "active_actions": [],
            "approval_ref": None,
            "composition_dependencies": dependencies or [],
            "safe_fallback": None,
        },
        "fallback_of": None,
        "status": "pending",
        "attempts": 0,
        "max_attempts": 2,
    }


def run_state(task_ids: list[str], schema_version: int = 3) -> dict:
    state = {
        "schema_version": schema_version,
        "run_id": "SR-FIXTURE",
        "objective": "Validate orchestration contracts.",
        "scope": {
            "assets": ["local fixture"],
            "versions": ["fixture-v1"],
            "environments": ["local temporary directory"],
        },
        "authorization_tier": "A0",
        "authorization": {
            "owner": "fixture owner",
            "evidence": ["local fixture request"],
            "time_window": None,
            "method_classes": ["passive local source review"],
            "rate_limits": ["repository reads only"],
            "rollback_plan": "remove only generated fixture outputs",
            "data_handling": "keep fixture evidence local",
            "output_audience": "fixture maintainers",
        },
        "active_testing_approved": False,
        "allowed_actions": ["read local fixture"],
        "prohibited_actions": ["external interaction"],
        "completion_criteria": ["validator result"],
        "task_ids": task_ids,
        "policy_event_log": "policy-events.jsonl",
        "composition_review": {
            "individual_tasks_within_scope": True,
            "combined_output_within_scope": True,
            "unnecessary_operational_detail_removed": True,
            "sensitive_data_redacted": True,
        },
        "status": "running",
        "updated_at": "2026-07-15T00:00:00Z",
    }
    if schema_version >= 3:
        state.update(
            {
                "research_profile": "source-code-security-audit",
                "active_testing_approval": approval_packet(),
                "conflicts_file": "conflicts.json",
                "preflight_exceptions": [],
                "task_graph": {"edges": [], "waves": [], "exclusive_resources": []},
                "artifact_roots": {
                    "tasks": "tasks",
                    "experiments": "experiments",
                    "artifacts": "artifacts",
                },
                "resume": {
                    "checkpoint_id": None,
                    "completed_tasks": [],
                    "retryable_tasks": [],
                    "blocked_tasks": [],
                    "next_actions": [],
                },
            }
        )
    return state


def write_run(root: Path, state: dict, tasks: list[dict], events: list[dict] | None = None,
              conflicts: list[dict] | None = None) -> None:
    if state.get("schema_version", 1) == 3:
        if state.get("task_graph") == {"edges": [], "waves": [], "exclusive_resources": []}:
            state["task_graph"] = {
                "edges": [
                    [dependency, record["task_id"]]
                    for record in tasks
                    for dependency in record.get("dependencies", [])
                ],
                "waves": [[record["task_id"]] for record in tasks],
                "exclusive_resources": [],
            }
        resume = state.get("resume")
        if isinstance(resume, dict) and all(
            not resume.get(field) for field in ("completed_tasks", "retryable_tasks", "blocked_tasks", "next_actions")
        ):
            state["resume"] = {
                "checkpoint_id": "CP-FINAL" if state.get("status") == "completed" else None,
                "completed_tasks": [record["task_id"] for record in tasks if record.get("status") == "completed"],
                "retryable_tasks": [
                    record["task_id"] for record in tasks if record.get("status") == "retryable_error"
                ],
                "blocked_tasks": [
                    record["task_id"]
                    for record in tasks
                    if record.get("status")
                    in {"incomplete", "needs_input", "needs_authorization", "blocked_technical", "policy_blocked"}
                ],
                "next_actions": [],
            }
    root.mkdir(parents=True, exist_ok=True)
    (root / "run-state.json").write_text(json.dumps(state), encoding="utf-8")
    for record in tasks:
        task_dir = root / "tasks" / record["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(json.dumps(record), encoding="utf-8")
    if events is not None:
        payload = "".join(json.dumps(event) + "\n" for event in events)
        (root / "policy-events.jsonl").write_text(payload, encoding="utf-8")
    if state.get("schema_version", 1) == 3:
        (root / "conflicts.json").write_text(json.dumps(conflicts or []), encoding="utf-8")


def policy_event(task_id: str, fallback_task_id: str | None) -> dict:
    return {
        "event_id": f"PE-{task_id}",
        "task_id": task_id,
        "timestamp": "2026-07-15T00:00:00Z",
        "failure_class": "policy",
        "visible_message": "Visible policy refusal.",
        "artifact_status": ["task contract preserved"],
        "decision": "policy_blocked",
        "fallback_task_id": fallback_task_id,
        "coverage_gap": "Operational validation remains unavailable.",
    }


def evidence(task_id: str, evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "task_id": task_id,
        "kind": "source_code",
        "locator": "fixture.scala:1",
        "observation": "The fixture contains one bounded source observation.",
        "supports": ["C-FIXTURE-01"],
        "sensitivity": "internal",
    }


def finding(task_id: str, evidence_ids: list[str], verdict: str, verifier_task_id: str | None) -> dict:
    return {
        "finding_id": f"F-{task_id}-01",
        "task_id": task_id,
        "title": "Bounded fixture finding",
        "affected_scope": ["local fixture"],
        "preconditions": ["fixture exists"],
        "observation": "One source observation is present.",
        "interpretation": "The observation supports only the bounded claim.",
        "impact": "No external impact.",
        "evidence_ids": evidence_ids,
        "counter_evidence": ["No contradicting fixture evidence was identified."],
        "false_positive_hypotheses": ["The observation could be fixture-specific."],
        "severity": "informational",
        "severity_rationale": "The fixture has no production impact.",
        "confidence": "high",
        "confidence_rationale": "The source locator and independent fixture evidence agree.",
        "verification_status": verdict,
        "verifier_task_id": verifier_task_id,
        "remediation": ["Retain the validation contract."],
        "regression_checks": ["Re-run the bounded fixture validator."],
        "limitations": ["Synthetic fixture only."],
        "redactions": [],
    }


def completed_report() -> str:
    return """# Security Research Report

## Executive Summary
The bounded fixture completed with one evidence-backed claim.

## Scope and Authorization
Only the local fixture and read-only source review were in scope.

## Method and Coverage
The run checked the declared source locator and task contract.

## Conflicts, Blocks, and Limitations
No conflicts were observed; conclusions apply only to the fixture.

## Claim-to-Evidence Matrix
| Claim ID | Verdict | Evidence IDs | Scope | Limitations |
|---|---|---|---|---|
| C-FIXTURE-01 | candidate | EV-SR-001-01 | local fixture | synthetic only |
"""


def write_completed_generic_run(root: Path) -> None:
    context = task("SR-001")
    context["status"] = "completed"
    synthesis = task("SR-002", "synthesis", ["SR-001"])
    synthesis["status"] = "completed"
    state = run_state(["SR-001", "SR-002"])
    state["status"] = "completed"
    write_run(root, state, [context, synthesis])
    task_dir = root / "tasks" / "SR-001"
    (task_dir / "report.md").write_text("# Completed report\n", encoding="utf-8")
    (task_dir / "evidence.jsonl").write_text(
        json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
    )
    (root / "evidence-index.json").write_text(
        json.dumps({"schema_version": 3, "records": [{"evidence_id": "EV-SR-001-01"}]}),
        encoding="utf-8",
    )
    (root / "final").mkdir()
    (root / "final" / "final-report.md").write_text(completed_report(), encoding="utf-8")


class OrchestratorRegressionTests(unittest.TestCase):
    def test_valid_v3_passes_validation_and_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            write_run(root, run_state(["SR-001"]), [context])
            self.assertEqual(validate_run(root), [])
            self.assertEqual(preflight(root, strict_v2=True), ([], []))

    def test_declared_generic_task_graph_must_match_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            state = run_state(["SR-001"])
            state["task_graph"] = {
                "edges": [["SR-001", "SR-001"]],
                "waves": [["SR-001"]],
                "exclusive_resources": [],
            }
            write_run(root, state, [context])
            self.assertTrue(any("exactly match task dependencies" in error for error in validate_run(root)))

    def test_valid_completed_run_has_outputs_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            write_completed_generic_run(root)
            self.assertEqual(validate_run(root), [])

    def test_boolean_only_v2_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["safety"].pop("approval_ref")
            state = run_state(["SR-001"], schema_version=2)
            write_run(root, state, [context])
            self.assertEqual(validate_run(root), [])
            for kwargs in ({}, {"strict_v2": True}, {"strict_v3": True}):
                errors, _ = preflight(root, **kwargs)
                self.assertTrue(any("schema v3" in error for error in errors), errors)

    def test_safe_non_sr_legacy_task_ids_remain_readable(self) -> None:
        for schema_version in (1, 2):
            with self.subTest(schema_version=schema_version), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                legacy = task("TASK-001")
                if schema_version == 2:
                    legacy["safety"].pop("approval_ref")
                state = run_state(["TASK-001"], schema_version=schema_version)
                write_run(root, state, [legacy])
                self.assertEqual(validate_run(root), [])
                errors, _ = preflight(root)
                self.assertTrue(any("schema v3" in error for error in errors), errors)

    def test_strict_v3_dispatch_rejects_v2_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["safety"].pop("approval_ref")
            write_run(root, run_state(["SR-001"], schema_version=2), [context])
            errors, _ = preflight(root, strict_v2=False, strict_v3=True)
            self.assertTrue(any("schema v3" in error for error in errors), errors)

    def test_incomplete_v3_active_approval_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            state = run_state(["SR-001"])
            state["authorization_tier"] = "A1"
            state["active_testing_approved"] = True
            state["active_testing_approval"] = approval_packet(True, ["SR-001"])
            state["active_testing_approval"]["owner"] = ""
            write_run(root, state, [context])
            self.assertTrue(any("non-empty owner" in error for error in validate_run(root)))

    def test_active_task_must_be_named_by_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            active = task("SR-002", "active_validation", ["SR-001"])
            active["safety"].update(
                {
                    "capability_boundary": "active_authorized",
                    "active_actions": ["one bounded local fixture mutation"],
                    "approval_ref": "APR-001",
                }
            )
            state = run_state(["SR-001", "SR-002"])
            state["authorization_tier"] = "A1"
            state["active_testing_approved"] = True
            state["active_testing_approval"] = approval_packet(True, ["SR-001"])
            write_run(root, state, [context, active])
            errors = validate_run(root)
            self.assertTrue(any("active task absent from approved_task_ids" in error for error in errors))

    def test_approval_must_not_name_unknown_or_passive_tasks(self) -> None:
        for approved_id in ("SR-001", "SR-999"):
            with self.subTest(approved_id=approved_id), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                state = run_state(["SR-001"])
                state["authorization_tier"] = "A1"
                state["active_testing_approved"] = True
                state["active_testing_approval"] = approval_packet(True, [approved_id])
                write_run(root, state, [context])
                errors = validate_run(root)
                self.assertTrue(any("approved_task_ids" in error for error in errors), errors)

    def test_policy_fallback_requires_bidirectional_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            blocked = task("SR-002", "state_inventory", ["SR-001"])
            blocked["status"] = "policy_blocked"
            fallback = task("SR-003", "control_review", ["SR-001"])
            fallback["fallback_of"] = "SR-002"
            state = run_state(["SR-001", "SR-002", "SR-003"])
            write_run(root, state, [context, blocked, fallback], [policy_event("SR-002", None)])
            errors = validate_run(root)
            self.assertTrue(any("must be linked by exactly one policy event" in error for error in errors))

    def test_policy_event_must_reference_blocked_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            write_run(root, run_state(["SR-001"]), [context], [policy_event("SR-001", None)])
            errors = validate_run(root)
            self.assertTrue(any("policy event task is not policy_blocked" in error for error in errors))

    def test_invalid_conflict_schema_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            invalid_conflict = {
                "conflict_id": "CF-001",
                "task_ids": ["SR-001"],
                "normalized_claim": "Conflicting claim.",
                "evidence_ids": [],
                "status": "invalid",
                "verifier_task_id": None,
                "resolution": "",
                "limitations": [],
            }
            write_run(root, run_state(["SR-001"]), [context], conflicts=[invalid_conflict])
            errors = validate_run(root)
            self.assertTrue(any("conflict task_ids" in error for error in errors))
            self.assertTrue(any("invalid conflict status" in error for error in errors))

    def test_resolved_conflict_requires_independent_verifier_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            first = task("SR-001")
            second = task("SR-002", "state_inventory", ["SR-001"])
            conflict = {
                "conflict_id": "CF-001",
                "task_ids": ["SR-001", "SR-002"],
                "normalized_claim": "The two tasks disagree on one bounded claim.",
                "evidence_ids": [],
                "status": "resolved",
                "verifier_task_id": "SR-001",
                "resolution": "The first task selected its own position.",
                "limitations": [],
            }
            state = run_state(["SR-001", "SR-002"])
            write_run(root, state, [first, second], conflicts=[conflict])
            errors = validate_run(root)
            self.assertTrue(any("independent verifier" in error for error in errors), errors)
            self.assertTrue(any("conflict evidence_ids" in error for error in errors), errors)

    def test_completed_run_requires_outputs_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["status"] = "completed"
            state = run_state(["SR-001"])
            state["status"] = "completed"
            write_run(root, state, [context])
            errors = validate_run(root)
            self.assertTrue(any("final/final-report.md" in error for error in errors), errors)
            self.assertTrue(any("completed run has no evidence records" in error for error in errors), errors)

    def test_completed_task_cannot_borrow_other_ownership_domains(self) -> None:
        for borrowed in ("final/final-report.md", "tasks/SR-OTHER/report.md"):
            with self.subTest(borrowed=borrowed), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                context["status"] = "completed"
                context["expected_outputs"] = [borrowed]
                state = run_state(["SR-001"])
                state["status"] = "completed"
                write_run(root, state, [context])
                task_dir = root / "tasks" / "SR-001"
                (task_dir / "evidence.jsonl").write_text(
                    json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
                )
                (root / "final").mkdir()
                (root / "final" / "final-report.md").write_text("# Final report\n", encoding="utf-8")
                other = root / "tasks" / "SR-OTHER"
                other.mkdir()
                (other / "report.md").write_text("# Other task report\n", encoding="utf-8")
                errors = validate_run(root)
                self.assertTrue(any("outside output ownership" in error for error in errors), errors)

    def test_whitespace_only_completed_text_output_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["status"] = "completed"
            write_run(root, run_state(["SR-001"]), [context])
            (root / "tasks" / "SR-001" / "report.md").write_text("  \n", encoding="utf-8")
            errors = validate_run(root)
            self.assertTrue(any("missing or empty" in error for error in errors), errors)

    def test_verified_finding_requires_independent_verifier(self) -> None:
        for verifier_id in (None, [], "SR-001"):
            with self.subTest(verifier_id=verifier_id), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                write_run(root, run_state(["SR-001"]), [context])
                task_dir = root / "tasks" / "SR-001"
                (task_dir / "evidence.jsonl").write_text(
                    json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
                )
                (task_dir / "finding-001.json").write_text(
                    json.dumps(finding("SR-001", ["EV-SR-001-01"], "verified", verifier_id)), encoding="utf-8"
                )
                errors = validate_run(root)
                self.assertTrue(
                    any("verified finding requires an independent verifier" in error for error in errors), errors
                )

    def test_malformed_finding_verdict_fails_closed_without_exception(self) -> None:
        for verdict in ([], {}):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                write_run(root, run_state(["SR-001"]), [context])
                task_dir = root / "tasks" / "SR-001"
                (task_dir / "evidence.jsonl").write_text(
                    json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
                )
                (task_dir / "finding-001.json").write_text(
                    json.dumps(finding("SR-001", ["EV-SR-001-01"], verdict, None)), encoding="utf-8"
                )
                errors = validate_run(root)
                self.assertTrue(any("invalid finding verdict" in error for error in errors), errors)

    def test_valid_verified_finding_has_verifier_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["status"] = "completed"
            verifier = task("SR-002", "verification", ["SR-001"])
            verifier["role"] = "verification"
            verifier["status"] = "completed"
            verifier["expected_outputs"] = ["report.md", "evidence.jsonl"]
            state = run_state(["SR-001", "SR-002"])
            write_run(root, state, [context, verifier])
            origin_dir = root / "tasks" / "SR-001"
            verifier_dir = root / "tasks" / "SR-002"
            origin_dir.joinpath("report.md").write_text("# Origin report\n", encoding="utf-8")
            origin_dir.joinpath("evidence.jsonl").write_text(
                json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
            )
            verifier_evidence = evidence("SR-002", "EV-SR-002-01")
            verifier_evidence["supports"] = ["F-SR-001-01"]
            verifier_dir.joinpath("evidence.jsonl").write_text(
                json.dumps(verifier_evidence) + "\n", encoding="utf-8"
            )
            verifier_dir.joinpath("report.md").write_text("# Independent verdict\n", encoding="utf-8")
            origin_dir.joinpath("finding-001.json").write_text(
                json.dumps(
                    finding("SR-001", ["EV-SR-001-01", "EV-SR-002-01"], "verified", "SR-002")
                ),
                encoding="utf-8",
            )
            self.assertEqual(validate_run(root), [])

    def test_hollow_conflict_verifier_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            first = task("SR-001")
            second = task("SR-002", "state_inventory", ["SR-001"])
            verifier = task("SR-003", "verification", ["SR-001", "SR-002"])
            verifier["status"] = "completed"
            conflict = {
                "conflict_id": "CF-001",
                "task_ids": ["SR-001", "SR-002"],
                "normalized_claim": "The two tasks disagree on one bounded claim.",
                "evidence_ids": ["EV-SR-001-01"],
                "status": "resolved",
                "verifier_task_id": "SR-003",
                "resolution": "The empty verifier selected one position.",
                "limitations": [],
            }
            write_run(root, run_state(["SR-001", "SR-002", "SR-003"]), [first, second, verifier], conflicts=[conflict])
            (root / "tasks" / "SR-001" / "evidence.jsonl").write_text(
                json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
            )
            errors = validate_run(root)
            self.assertTrue(any("verifier-owned evidence" in error for error in errors), errors)

    def test_unsafe_or_duplicate_task_ids_fail_before_access(self) -> None:
        for task_ids in (["../../outside-task"], ["SR-001", "SR-001"]):
            with self.subTest(task_ids=task_ids), tempfile.TemporaryDirectory() as temp:
                temp_root = Path(temp)
                root = temp_root / "run"
                root.mkdir()
                (root / "tasks").mkdir()
                (root / "run-state.json").write_text(json.dumps(run_state(task_ids)), encoding="utf-8")
                (root / "conflicts.json").write_text("[]", encoding="utf-8")
                if task_ids[0].startswith(".."):
                    outside = temp_root / "outside-task"
                    outside.mkdir()
                    (outside / "task.json").write_text(json.dumps(task(task_ids[0])), encoding="utf-8")
                else:
                    task_dir = root / "tasks" / "SR-001"
                    task_dir.mkdir()
                    (task_dir / "task.json").write_text(json.dumps(task("SR-001")), encoding="utf-8")
                errors = validate_run(root)
                self.assertTrue(any("task ID" in error for error in errors), errors)

    def test_run_metadata_path_escape_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            state = run_state(["SR-001"])
            state["conflicts_file"] = "../outside-conflicts.json"
            write_run(root, state, [context])
            (root.parent / "outside-conflicts.json").write_text("[]", encoding="utf-8")
            errors = validate_run(root)
            self.assertTrue(any("conflicts_file escapes run directory" in error for error in errors), errors)

    def test_symlink_assigned_path_escape_fails_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            root = temp_root / "run"
            outside = temp_root / "outside"
            outside.mkdir()
            context = task("SR-001")
            context["assigned_paths"] = ["tasks/SR-001/output"]
            write_run(root, run_state(["SR-001"]), [context])
            (root / "tasks" / "SR-001" / "output").symlink_to(outside, target_is_directory=True)
            errors, _ = preflight(root, strict_v2=True)
            self.assertTrue(any("ownership" in error for error in errors), errors)

    def test_symlink_task_root_escape_fails_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            root = temp_root / "run"
            outside = temp_root / "outside-task"
            outside.mkdir()
            context = task("SR-001")
            root.mkdir()
            (root / "run-state.json").write_text(json.dumps(run_state(["SR-001"])), encoding="utf-8")
            (root / "conflicts.json").write_text("[]", encoding="utf-8")
            (outside / "task.json").write_text(json.dumps(context), encoding="utf-8")
            (root / "tasks").mkdir()
            (root / "tasks" / "SR-001").symlink_to(outside, target_is_directory=True)
            errors, _ = preflight(root, strict_v2=True)
            self.assertTrue(any("task directory escapes run ownership" in error for error in errors), errors)

    def test_v3_requires_exact_known_schema_at_run_and_task_levels(self) -> None:
        for invalid_version in (4, True, "3"):
            with self.subTest(run_schema=invalid_version), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                state = run_state(["SR-001"])
                state["schema_version"] = invalid_version
                write_run(root, state, [context])
                self.assertTrue(any("supported integer versions" in error for error in validate_run(root)))

        for task_version in (None, 4, True):
            with self.subTest(task_schema=task_version), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                if task_version is None:
                    context.pop("schema_version")
                else:
                    context["schema_version"] = task_version
                write_run(root, run_state(["SR-001"]), [context])
                self.assertTrue(any("task" in error and "schema_version" in error for error in validate_run(root)))

    def test_non_object_contracts_fail_closed_without_exceptions(self) -> None:
        for payload in ("[]", "null"):
            with self.subTest(run_payload=payload), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                root.mkdir(parents=True)
                (root / "run-state.json").write_text(payload, encoding="utf-8")
                self.assertTrue(any("expected object" in error for error in validate_run(root)))

        for contract in ("task", "evidence", "finding", "policy-event"):
            for payload in ("[]", "null"):
                with self.subTest(contract=contract, payload=payload), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp) / "run"
                    context = task("SR-001")
                    write_run(root, run_state(["SR-001"]), [context])
                    task_dir = root / "tasks" / "SR-001"
                    if contract == "task":
                        (task_dir / "task.json").write_text(payload, encoding="utf-8")
                    elif contract == "evidence":
                        (task_dir / "evidence.jsonl").write_text(payload + "\n", encoding="utf-8")
                    elif contract == "finding":
                        (task_dir / "finding-001.json").write_text(payload, encoding="utf-8")
                    else:
                        (root / "policy-events.jsonl").write_text(payload + "\n", encoding="utf-8")
                    errors = validate_run(root)
                    self.assertTrue(any("expected object" in error for error in errors), errors)

    def test_v3_common_envelope_and_profile_are_fail_closed(self) -> None:
        for field in ("research_profile", "authorization", "task_graph", "artifact_roots", "resume"):
            with self.subTest(missing=field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                state = run_state(["SR-001"])
                state.pop(field)
                write_run(root, state, [context])
                self.assertTrue(any(field in error for error in validate_run(root)))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            state = run_state(["SR-001"])
            state["research_profile"] = "microarchitecture-securit"
            write_run(root, state, [context])
            self.assertTrue(any("research_profile" in error for error in validate_run(root)))

    def test_pending_output_contract_cannot_escape_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["expected_outputs"] = ["../../outside.md"]
            write_run(root, run_state(["SR-001"]), [context])
            errors, _ = preflight(root, strict_v3=True)
            self.assertTrue(any("expected output escapes" in error for error in errors), errors)

    def test_task_collection_and_graph_duplicates_are_rejected(self) -> None:
        mutations = {
            "assigned_paths": [{}],
            "inputs": "repo@commit",
            "expected_outputs": {},
            "acceptance_criteria": [],
            "dependencies": ["SR-001", "SR-001"],
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                context[field] = value
                write_run(root, run_state(["SR-001"]), [context])
                self.assertTrue(validate_run(root))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            analysis = task("SR-002", "control_review", ["SR-001"])
            state = run_state(["SR-001", "SR-002"])
            state["task_graph"] = {
                "edges": [["SR-001", "SR-002"], ["SR-001", "SR-002"]],
                "waves": [["SR-001"], [], ["SR-002"]],
                "exclusive_resources": [],
            }
            write_run(root, state, [context, analysis])
            errors = validate_run(root)
            self.assertTrue(any("duplicate task graph edge" in error for error in errors), errors)
            self.assertTrue(any("must not be empty" in error for error in errors), errors)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            analysis = task("SR-002", "control_review", ["SR-001"])
            analysis["safety"]["composition_dependencies"] = []
            write_run(root, run_state(["SR-001", "SR-002"]), [context, analysis])
            self.assertTrue(
                any("must include every execution dependency" in error for error in validate_run(root))
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["safety"] = []
            write_run(root, run_state(["SR-001"]), [context])
            errors = validate_run(root)
            self.assertTrue(any("expected object" in error for error in errors), errors)

    def test_composition_review_type_is_validated_before_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            state = run_state(["SR-001"])
            state["composition_review"] = 1
            write_run(root, state, [context])
            errors, _ = preflight(root, strict_v3=True)
            self.assertTrue(any("composition_review" in error for error in errors), errors)

    def test_preflight_requires_one_context_root_in_first_wave(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            first = task("SR-001")
            second = task("SR-002")
            write_run(root, run_state(["SR-001", "SR-002"]), [first, second])
            errors, _ = preflight(root, strict_v3=True)
            self.assertTrue(any("exactly one context_map" in error for error in errors), errors)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            analysis = task("SR-002", "control_review", [])
            state = run_state(["SR-001", "SR-002"])
            state["task_graph"] = {
                "edges": [],
                "waves": [["SR-002"], ["SR-001"]],
                "exclusive_resources": [],
            }
            write_run(root, state, [context, analysis])
            errors, _ = preflight(root, strict_v3=True)
            self.assertTrue(any("first non-blocked task graph wave" in error for error in errors), errors)

    def test_non_operational_dynamic_intent_variants_are_rejected(self) -> None:
        actions = (
            "launch the local workload and collect counters",
            "invoke a simulator fixture",
            "fuzz one local parser",
            "send a probe to the target",
            "运行本地仿真并测量时延",
            "access the FPGA board",
            "start the local Verilator workload",
        )
        for action in actions:
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                context["allowed_actions"] = [action]
                write_run(root, run_state(["SR-001"]), [context])
                self.assertTrue(any("describes active work" in error for error in validate_run(root)))

    def test_generic_profile_cannot_hide_fpga_active_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            active = task("SR-002", "active_validation", ["SR-001"])
            action = "access the FPGA board and collect hardware counters"
            active["allowed_actions"] = [action]
            active["safety"].update(
                {
                    "capability_boundary": "active_authorized",
                    "active_actions": [action],
                    "approval_ref": "APR-001",
                }
            )
            state = run_state(["SR-001", "SR-002"])
            state["authorization_tier"] = "A1"
            state["active_testing_approved"] = True
            state["active_testing_approval"] = approval_packet(True, ["SR-002"])
            write_run(root, state, [context, active])
            errors = validate_run(root)
            self.assertTrue(any("microarchitecture active action requires" in error for error in errors), errors)
            self.assertTrue(any("requires authorization tier A2" in error for error in errors), errors)

    def test_resume_and_dependency_status_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            running = task("SR-002", "control_review", ["SR-001"])
            running["status"] = "running"
            state = run_state(["SR-001", "SR-002"])
            write_run(root, state, [context, running])
            errors = validate_run(root)
            self.assertTrue(any("has dependency SR-001 in status pending" in error for error in errors), errors)

            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["resume"]["completed_tasks"] = ["SR-001"]
            state["resume"]["next_actions"] = 7
            state_path.write_text(json.dumps(state), encoding="utf-8")
            errors = validate_run(root)
            self.assertTrue(any("resume.completed_tasks" in error for error in errors), errors)
            self.assertTrue(any("resume.next_actions" in error for error in errors), errors)

    def test_completed_run_cannot_declare_future_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            write_completed_generic_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["resume"]["next_actions"] = ["perform remaining work"]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            errors = validate_run(root)
            self.assertTrue(any("empty resume.next_actions" in error for error in errors), errors)

    def test_malformed_dependencies_fail_closed_without_exception(self) -> None:
        for dependencies in (1, True, None):
            with self.subTest(dependencies=dependencies), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                write_run(root, run_state(["SR-001"]), [context])
                task_path = root / "tasks/SR-001/task.json"
                context["dependencies"] = dependencies
                task_path.write_text(json.dumps(context), encoding="utf-8")
                errors = validate_run(root)
                self.assertTrue(any("dependencies" in error or "dependency" in error for error in errors), errors)

    def test_malformed_fallback_reference_fails_closed_without_exception(self) -> None:
        for fallback_of in ([], {}):
            with self.subTest(fallback_of=fallback_of), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                context = task("SR-001")
                context["fallback_of"] = fallback_of
                write_run(root, run_state(["SR-001"]), [context])
                errors = validate_run(root)
                self.assertTrue(any("malformed fallback_of" in error for error in errors), errors)

    def test_cosmetic_policy_fallback_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            blocked = task("SR-002", "state_inventory", ["SR-001"])
            blocked["status"] = "policy_blocked"
            fallback = task("SR-003", "control_review", ["SR-001"])
            fallback["fallback_of"] = "SR-002"
            fallback["objective"] = blocked["objective"].upper() + " !!!"
            fallback["research_question"] = blocked["research_question"] + "?"
            state = run_state(["SR-001", "SR-002", "SR-003"])
            write_run(root, state, [context, blocked, fallback], [policy_event("SR-002", "SR-003")])
            errors = validate_run(root)
            self.assertTrue(any("materially change its objective" in error for error in errors), errors)
            self.assertTrue(any("materially change its research_question" in error for error in errors), errors)

    def test_completed_null_metadata_is_rejected(self) -> None:
        for filename in ("conflicts.json", "evidence-index.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "run"
                write_completed_generic_run(root)
                (root / filename).write_text("null", encoding="utf-8")
                errors = validate_run(root)
                expected = "expected array" if filename == "conflicts.json" else "expected object"
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_final_claim_matrix_must_reference_supporting_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            write_completed_generic_run(root)
            report_path = root / "final/final-report.md"
            report = report_path.read_text(encoding="utf-8")
            report = report.replace(
                "| C-FIXTURE-01 | candidate | EV-SR-001-01 | local fixture | synthetic only |",
                "| FAKE-CLAIM | verified | EV-DOES-NOT-EXIST | local fixture | synthetic only |",
            )
            report_path.write_text(report, encoding="utf-8")
            errors = validate_run(root)
            self.assertTrue(any("unknown claim" in error for error in errors), errors)
            self.assertTrue(any("unknown evidence" in error for error in errors), errors)

    def test_final_claim_matrix_rejects_duplicate_claim_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            write_completed_generic_run(root)
            report_path = root / "final/final-report.md"
            report = report_path.read_text(encoding="utf-8")
            report += "| C-FIXTURE-01 | rejected | EV-SR-001-01 | local fixture | duplicate row |\n"
            report_path.write_text(report, encoding="utf-8")
            errors = validate_run(root)
            self.assertTrue(any("duplicate claim" in error for error in errors), errors)

    def test_unlisted_task_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            write_run(root, run_state(["SR-001"]), [context])
            extra_task_path = root / "tasks/SR-999/task.json"
            extra_task_path.parent.mkdir(parents=True)
            extra_task_path.write_text(json.dumps(task("SR-999")), encoding="utf-8")
            errors, _ = preflight(root, strict_v3=True)
            self.assertTrue(any("undeclared task directory" in error for error in errors), errors)

    def test_boolean_attempt_budget_and_blank_approval_stop_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            context["attempts"] = True
            context["max_attempts"] = True
            write_run(root, run_state(["SR-001"]), [context])
            self.assertTrue(any("attempt budget" in error for error in validate_run(root)))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            active = task("SR-002", "active_validation", ["SR-001"])
            action = "collect one bounded local fixture result"
            active["allowed_actions"] = [action]
            active["safety"].update(
                {"capability_boundary": "active_authorized", "active_actions": [action], "approval_ref": "APR-001"}
            )
            state = run_state(["SR-001", "SR-002"])
            state["authorization_tier"] = "A1"
            state["active_testing_approved"] = True
            state["active_testing_approval"] = approval_packet(True, ["SR-002"])
            state["active_testing_approval"]["stop_conditions"] = [""]
            state["authorization"]["time_window"] = state["active_testing_approval"]["time_window"]
            state["authorization"]["method_classes"] = [state["active_testing_approval"]["method_class"]]
            write_run(root, state, [context, active])
            self.assertTrue(any("stop_conditions" in error for error in validate_run(root)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
