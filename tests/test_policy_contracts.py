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
    return {
        "task_id": task_id,
        "role": "context",
        "objective": "Establish one bounded evidence claim.",
        "research_question": "Which source artifact establishes the configured ownership boundary?",
        "dependencies": dependencies or [],
        "assigned_paths": [f"tasks/{task_id}"],
        "inputs": ["repo@commit"],
        "allowed_actions": ["read local artifacts"],
        "prohibited_actions": ["active testing"],
        "expected_outputs": ["report.md"],
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
        "scope": {"assets": ["local fixture"]},
        "authorization_tier": "A0",
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
                "active_testing_approval": approval_packet(),
                "conflicts_file": "conflicts.json",
                "preflight_exceptions": [],
            }
        )
    return state


def write_run(root: Path, state: dict, tasks: list[dict], events: list[dict] | None = None,
              conflicts: list[dict] | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "run-state.json").write_text(json.dumps(state), encoding="utf-8")
    for record in tasks:
        task_dir = root / "tasks" / record["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(json.dumps(record), encoding="utf-8")
    if events is not None:
        payload = "".join(json.dumps(event) + "\n" for event in events)
        (root / "policy-events.jsonl").write_text(payload, encoding="utf-8")
    if state.get("schema_version", 1) >= 3:
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
        "verification_status": verdict,
        "verifier_task_id": verifier_task_id,
        "remediation": ["Retain the validation contract."],
        "limitations": ["Synthetic fixture only."],
    }


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
            context = task("SR-001")
            context["status"] = "completed"
            state = run_state(["SR-001"])
            state["status"] = "completed"
            write_run(root, state, [context])
            task_dir = root / "tasks" / "SR-001"
            (task_dir / "report.md").write_text("# Completed report\n", encoding="utf-8")
            (task_dir / "evidence.jsonl").write_text(
                json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
            )
            (root / "final").mkdir()
            (root / "final" / "final-report.md").write_text("# Final report\n", encoding="utf-8")
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

    def test_valid_verified_finding_has_verifier_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            context = task("SR-001")
            verifier = task("SR-002", "verification", ["SR-001"])
            verifier["role"] = "verification"
            verifier["status"] = "completed"
            verifier["expected_outputs"] = ["report.md", "evidence.jsonl"]
            state = run_state(["SR-001", "SR-002"])
            write_run(root, state, [context, verifier])
            origin_dir = root / "tasks" / "SR-001"
            verifier_dir = root / "tasks" / "SR-002"
            origin_dir.joinpath("evidence.jsonl").write_text(
                json.dumps(evidence("SR-001", "EV-SR-001-01")) + "\n", encoding="utf-8"
            )
            verifier_dir.joinpath("evidence.jsonl").write_text(
                json.dumps(evidence("SR-002", "EV-SR-002-01")) + "\n", encoding="utf-8"
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
            self.assertTrue(any("assigned path escapes task ownership" in error for error in errors))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
