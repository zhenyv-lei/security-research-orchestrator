from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight_tasks import preflight  # noqa: E402
from validate_run import canonical_contract_hash, validate_run  # noqa: E402


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def snapshot() -> dict[str, object]:
    return {
        "repository": "/local/rtl",
        "commit": "0123456789abcdef",
        "dirty": False,
        "submodules": [],
        "rtl_config": "TestConfig",
        "isa_privilege_assumptions": ["RV64"],
        "target_class": "cycle-simulator",
        "toolchain": ["verilator:test"],
        "reference_model": "ref:test",
        "workloads": ["WL-001"],
    }


def approval() -> dict[str, object]:
    return {
        "approval_id": "APR-001",
        "approved": True,
        "approved_task_ids": ["SR-002"],
        "target": "local cycle-simulator fixture",
        "owner": "fixture owner",
        "authorization_source": "written fixture approval",
        "method_class": "bounded local simulation",
        "time_window": "2026-07-15T00:00:00Z/2026-07-15T01:00:00Z",
        "rate_limits": "one experiment",
        "mutation": "temporary result files",
        "expected_traffic_or_side_effects": "local fixture writes",
        "containment": "temporary directory",
        "rollback": "delete temporary directory",
        "sensitive_data_exposure": "none",
        "stop_conditions": ["unexpected external interaction"],
    }


def task(
    task_id: str,
    task_class: str,
    dependencies: list[str],
    *,
    execution_mode: str = "read-only",
) -> dict[str, object]:
    active = task_class == "active_validation"
    synthesis = task_class == "synthesis"
    return {
        "schema_version": 3,
        "task_id": task_id,
        "role": (
            "synthesis"
            if synthesis
            else ("verification" if task_class == "verification" else ("context" if task_class == "context_map" else "analysis"))
        ),
        "phase": task_class.replace("_", "-"),
        "execution_mode": execution_mode,
        "objective": f"Complete the bounded {task_class} fixture.",
        "research_question": "Does the controlled artifact establish the bounded claim?",
        "dependencies": dependencies,
        "assigned_paths": ["final"] if synthesis else [f"tasks/{task_id}"],
        "inputs": ["repo@0123456789abcdef"],
        "target_snapshot": snapshot(),
        "resource_requirements": {
            "cpu": 2,
            "memory_gb": 4,
            "wall_time_minutes": 5,
            "storage_gb": 2,
            "exclusive_resources": ["sim-slot"] if active else [],
        },
        "allowed_actions": ["run one bounded local simulation"] if active else ["read local artifacts"],
        "prohibited_actions": ["external targets"],
        "expected_outputs": ["final/final-report.md"] if synthesis else ["report.md", "evidence.jsonl"],
        "acceptance_criteria": ["one cited claim"],
        "evidence_requirements": ["stable locator"],
        "stop_conditions": ["scope change"],
        "escalation_conditions": ["authorization ambiguity"],
        "safety": {
            "purpose": "defensive",
            "task_class": task_class,
            "capability_boundary": "active_authorized" if active else "non_operational",
            "resource_scope": ["local simulator"] if active else ["configured RTL snapshot"],
            "evidence_goal": "Cite one bounded source or experiment observation.",
            "active_actions": ["run one bounded local simulation"] if active else [],
            "approval_ref": "APR-001" if active else None,
            "composition_dependencies": dependencies,
            "safe_fallback": None,
        },
        "fallback_of": None,
        "status": "completed",
        "attempts": 1,
        "max_attempts": 2,
    }


def completed_report() -> str:
    return """# Security Research Report

## Executive Summary
The bounded simulator fixture produced one independently checked result.

## Scope and Authorization
Only the pinned local simulator fixture and declared action were authorized.

## Design Snapshot and Reproducibility
The commit, configuration, toolchain, workload, seed, and repetition are recorded.

## Experiment Matrix and Artifact Coverage
CELL-001 has one hash-verified simulation artifact.

## Method and Coverage
The run compared the approved control and recorded cycle count.

## Conflicts, Blocks, and Limitations
No conflict was observed; the result is limited to the synthetic fixture.

## Claim-to-Evidence Matrix
| Claim ID | Verdict | Evidence IDs | Scope | Limitations |
|---|---|---|---|---|
| F-SR-002-01 | verified | EV-SR-002-01, EV-SR-003-01 | local fixture | synthetic only |
"""


class MicroarchitectureValidatorTests(unittest.TestCase):
    def make_valid_run(self, root: Path) -> None:
        state = {
            "schema_version": 3,
            "run_id": "SR-RUN-MICROARCH-TEST",
            "objective": "Validate a controlled local microarchitecture study.",
            "research_profile": "microarchitecture-security",
            "scope": {
                "assets": ["local RTL"],
                "versions": ["0123456789abcdef"],
                "environments": ["isolated simulator"],
                "target_snapshot": snapshot(),
            },
            "authorization_tier": "A1",
            "authorization": {
                "owner": "fixture owner",
                "evidence": ["written fixture approval"],
                "time_window": "2026-07-15T00:00:00Z/2026-07-15T01:00:00Z",
                "method_classes": ["bounded local simulation"],
                "rate_limits": ["one experiment"],
                "rollback_plan": "delete temporary directory",
                "data_handling": "local only",
                "output_audience": "test",
            },
            "active_testing_approved": True,
            "active_testing_approval": approval(),
            "allowed_actions": ["read local RTL", "run one bounded local simulation"],
            "prohibited_actions": ["external interaction"],
            "completion_criteria": ["independent verification"],
            "task_ids": ["SR-001", "SR-002", "SR-003", "SR-004"],
            "task_graph": {
                "edges": [["SR-001", "SR-002"], ["SR-002", "SR-003"], ["SR-003", "SR-004"]],
                "waves": [["SR-001"], ["SR-002"], ["SR-003"], ["SR-004"]],
                "exclusive_resources": ["sim-slot"],
            },
            "artifact_roots": {
                "tasks": "tasks",
                "experiments": "experiments",
                "artifacts": "artifacts",
            },
            "resume": {
                "checkpoint_id": "CP-3",
                "completed_tasks": ["SR-001", "SR-002", "SR-003", "SR-004"],
                "retryable_tasks": [],
                "blocked_tasks": [],
                "next_actions": [],
            },
            "policy_event_log": "policy-events.jsonl",
            "conflicts_file": "conflicts.json",
            "preflight_exceptions": [],
            "composition_review": {
                "individual_tasks_within_scope": True,
                "combined_output_within_scope": True,
                "unnecessary_operational_detail_removed": True,
                "sensitive_data_redacted": True,
            },
            "status": "completed",
            "updated_at": "2026-07-15T00:00:00Z",
        }
        write_json(root / "run-state.json", state)

        context = task("SR-001", "context_map", [])
        active = task("SR-002", "active_validation", ["SR-001"], execution_mode="local-simulation")
        verifier = task("SR-003", "verification", ["SR-002"])
        synthesis = task("SR-004", "synthesis", ["SR-003"])
        write_json(root / "tasks/SR-001/task.json", context)
        write_json(root / "tasks/SR-002/task.json", active)
        write_json(root / "tasks/SR-003/task.json", verifier)
        write_json(root / "tasks/SR-004/task.json", synthesis)

        evidence_records = {
            "SR-001": {
                "evidence_id": "EV-SR-001-01",
                "task_id": "SR-001",
                "kind": "source_code",
                "locator": "fixture.scala:1",
                "observation": "The configured snapshot is pinned.",
                "supports": ["C-SNAPSHOT"],
                "sensitivity": "internal",
            },
            "SR-002": {
                "evidence_id": "EV-SR-002-01",
                "task_id": "SR-002",
                "kind": "simulation_log",
                "locator": "ART-EXP-001-001",
                "artifact_id": "ART-EXP-001-001",
                "observation": "The bounded local control completed.",
                "supports": ["F-SR-002-01"],
                "sensitivity": "internal",
            },
            "SR-003": {
                "evidence_id": "EV-SR-003-01",
                "task_id": "SR-003",
                "kind": "analysis",
                "locator": "tasks/SR-003/report.md",
                "observation": "An independent control supports the bounded finding.",
                "supports": ["F-SR-002-01"],
                "sensitivity": "internal",
            },
        }
        for task_id, evidence in evidence_records.items():
            task_dir = root / "tasks" / task_id
            (task_dir / "report.md").write_text("# Completed report\n", encoding="utf-8")
            (task_dir / "evidence.jsonl").write_text(json.dumps(evidence) + "\n", encoding="utf-8")

        finding = json.loads((ROOT / "assets/templates/finding.json").read_text(encoding="utf-8"))
        finding.update(
            {
                "finding_id": "F-SR-002-01",
                "task_id": "SR-002",
                "title": "Bounded fixture finding",
                "affected_scope": ["local simulator fixture"],
                "preconditions": ["pinned fixture snapshot"],
                "observation": "The bounded local control completed.",
                "interpretation": "The result supports only the fixture claim.",
                "impact": "Test fixture only.",
                "evidence_ids": ["EV-SR-002-01", "EV-SR-003-01"],
                "counter_evidence": ["The negative control did not show the observation."],
                "false_positive_hypotheses": ["A tool-only artifact could mimic the cycle count."],
                "severity": "informational",
                "severity_rationale": "The result applies only to a synthetic fixture.",
                "confidence": "high",
                "confidence_rationale": "The raw artifact and independent verifier agree.",
                "verification_status": "verified",
                "verifier_task_id": "SR-003",
                "remediation": ["Retain the bounded validation contract."],
                "regression_checks": ["Re-run CELL-001 with the pinned snapshot."],
                "limitations": ["No production target was evaluated."],
            }
        )
        write_json(root / "tasks/SR-002/finding-001.json", finding)

        experiment = json.loads((ROOT / "assets/templates/experiment.json").read_text(encoding="utf-8"))
        experiment.update(
            {
                "experiment_id": "EXP-001",
                "task_id": "SR-002",
                "approval_ref": "APR-001",
                "hypothesis": "A bounded local observation is reproducible.",
                "variables": {
                    "independent": [],
                    "dependent": ["cycle count"],
                    "controlled": ["commit and configuration"],
                    "nuisance": [],
                },
                "target_snapshot": snapshot(),
                "workloads": ["WL-001"],
                "controls": ["negative control"],
                "observables": ["cycle count"],
                "seed_policy": {"mode": "fixed-list", "seeds": [1], "repetitions": 1},
                "cells": [
                    {
                        "cell_id": "CELL-001",
                        "label": "bounded control configuration",
                        "variable_assignments": {},
                    }
                ],
                "command_plan": ["run one bounded local simulation"],
                "expected_artifacts": ["ART-EXP-001-001"],
                "acceptance_criteria": ["control reproduced"],
                "inconclusive_criteria": ["run truncated"],
                "resource_exhaustion_criteria": ["budget exceeded"],
                "stop_conditions": ["snapshot drift"],
                "resource_budget": {
                    "cpu": 2,
                    "memory_gb": 4,
                    "wall_time_minutes": 5,
                    "storage_gb": 1,
                    "exclusive_resources": ["sim-slot"],
                },
                "status": "completed",
            }
        )
        write_json(root / "experiments/EXP-001/experiment.json", experiment)

        artifact_path = root / "experiments/EXP-001/results/run-001.log"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("controlled result\n", encoding="utf-8")
        artifact = json.loads((ROOT / "assets/templates/artifact-record.json").read_text(encoding="utf-8"))
        artifact.update(
            {
                "artifact_id": "ART-EXP-001-001",
                "producer_task_id": "SR-002",
                "experiment_id": "EXP-001",
                "experiment_revision": 1,
                "experiment_contract_hash": canonical_contract_hash(experiment),
                "cell_id": "CELL-001",
                "path": "experiments/EXP-001/results/run-001.log",
                "hash": "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                "target_snapshot": snapshot(),
                "tool_versions": ["verilator:test"],
                "workload_ids": ["WL-001"],
                "seed": 1,
                "repetition_index": 0,
                "generated_at": "2026-07-15T00:00:00Z",
            }
        )
        manifest = root / "artifacts/manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(artifact) + "\n", encoding="utf-8")

        write_json(root / "conflicts.json", [])
        write_json(
            root / "evidence-index.json",
            {
                "schema_version": 3,
                "records": [
                    {"evidence_id": "EV-SR-001-01"},
                    {"evidence_id": "EV-SR-002-01"},
                    {"evidence_id": "EV-SR-003-01"},
                ],
            },
        )
        final_dir = root / "final"
        final_dir.mkdir()
        (final_dir / "final-report.md").write_text(
            completed_report(),
            encoding="utf-8",
        )

    def errors_for(self, root: Path) -> list[str]:
        return validate_run(root)

    def test_valid_microarchitecture_run_and_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            self.assertEqual([], self.errors_for(root))
            self.assertEqual(([], []), preflight(root, strict_v3=True))

    def test_static_rtl_a0_microarchitecture_run_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["authorization_tier"] = "A0"
            state["active_testing_approved"] = False
            inactive_approval = approval()
            inactive_approval.update({"approval_id": "", "approved": False, "approved_task_ids": [], "stop_conditions": []})
            for field in (
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
            ):
                inactive_approval[field] = ""
            state["active_testing_approval"] = inactive_approval
            state["task_ids"] = ["SR-001"]
            state["task_graph"] = {"edges": [], "waves": [["SR-001"]], "exclusive_resources": []}
            state["resume"]["completed_tasks"] = ["SR-001"]
            state["status"] = "running"
            static_snapshot = snapshot()
            static_snapshot["target_class"] = "static-rtl"
            static_snapshot["workloads"] = []
            state["scope"]["target_snapshot"] = static_snapshot
            write_json(state_path, state)

            context_path = root / "tasks/SR-001/task.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["target_snapshot"] = static_snapshot
            write_json(context_path, context)
            for task_id in ("SR-002", "SR-003", "SR-004"):
                shutil.rmtree(root / "tasks" / task_id)
            shutil.rmtree(root / "experiments")
            shutil.rmtree(root / "artifacts")
            write_json(
                root / "evidence-index.json",
                {"schema_version": 3, "records": [{"evidence_id": "EV-SR-001-01"}]},
            )
            self.assertEqual([], self.errors_for(root))
            self.assertEqual(([], []), preflight(root, strict_v3=True))

    def test_experiment_cannot_bypass_profile_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["research_profile"] = "source-code-audit"
            write_json(state_path, state)
            self.assertTrue(any("require research_profile" in error for error in self.errors_for(root)))

    def test_unpinned_run_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["scope"]["target_snapshot"]["commit"] = ""
            write_json(state_path, state)
            self.assertTrue(any("target_snapshot.commit" in error for error in self.errors_for(root)))

    def test_snapshot_toolchain_and_task_phase_must_be_substantive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["scope"]["target_snapshot"]["toolchain"] = [""]
            write_json(state_path, state)
            self.assertTrue(any("target_snapshot.toolchain" in error for error in self.errors_for(root)))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            task_path = root / "tasks/SR-002/task.json"
            active = json.loads(task_path.read_text(encoding="utf-8"))
            active["phase"] = []
            write_json(task_path, active)
            self.assertTrue(any("phase must be a non-empty string" in error for error in self.errors_for(root)))

    def test_cross_layer_snapshot_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["target_snapshot"]["rtl_config"] = "DifferentConfig"
            write_json(path, experiment)
            self.assertTrue(any("differs from run snapshot" in error for error in self.errors_for(root)))

    def test_experiment_requires_approved_active_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["approval_ref"] = "APR-OTHER"
            write_json(path, experiment)
            self.assertTrue(any("approved active_validation" in error for error in self.errors_for(root)))

    def test_general_authorization_must_match_active_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["authorization"]["owner"] = "different owner"
            write_json(state_path, state)
            self.assertTrue(any("owner differs" in error for error in self.errors_for(root)))

    def test_executable_task_requires_active_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-001/task.json"
            context = json.loads(path.read_text(encoding="utf-8"))
            context["execution_mode"] = "local-simulation"
            write_json(path, context)
            self.assertTrue(any("must use active_validation" in error for error in self.errors_for(root)))

    def test_non_operational_active_word_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-001/task.json"
            context = json.loads(path.read_text(encoding="utf-8"))
            context["allowed_actions"] = ["run one local simulation"]
            write_json(path, context)
            errors, warnings = preflight(root, strict_v3=True)
            self.assertEqual([], warnings)
            self.assertTrue(any("describes active work" in error for error in errors), errors)

    def test_execution_mode_must_match_target_class(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-002/task.json"
            active = json.loads(path.read_text(encoding="utf-8"))
            active["execution_mode"] = "silicon"
            write_json(path, active)
            self.assertTrue(any("target_class disagree" in error for error in self.errors_for(root)))

    def test_fpga_and_silicon_execution_require_a2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-002/task.json"
            active = json.loads(path.read_text(encoding="utf-8"))
            active["execution_mode"] = "fpga"
            write_json(path, active)
            self.assertTrue(any("requires authorization tier A2" in error for error in self.errors_for(root)))

    def test_task_toolchain_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-001/task.json"
            context = json.loads(path.read_text(encoding="utf-8"))
            context["target_snapshot"]["toolchain"] = ["verilator:different"]
            write_json(path, context)
            self.assertTrue(any("differs from run snapshot" in error for error in self.errors_for(root)))

    def test_missing_manifest_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            (root / "experiments/EXP-001/results/run-001.log").unlink()
            self.assertTrue(any("does not exist" in error for error in self.errors_for(root)))

    def test_unknown_experiment_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            unknown = root / "experiments/EXP-UNKNOWN"
            unknown.mkdir()
            (unknown / "notes.txt").write_text("untracked\n", encoding="utf-8")
            self.assertTrue(any("unexpected or incomplete" in error for error in self.errors_for(root)))

    def test_unregistered_experiment_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            (root / "experiments/EXP-001/results/extra.log").write_text("extra\n", encoding="utf-8")
            self.assertTrue(any("unregistered experiment artifact" in error for error in self.errors_for(root)))

    def test_artifact_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            (root / "experiments/EXP-001/results/run-001.log").write_text("changed\n", encoding="utf-8")
            self.assertTrue(any("hash mismatch" in error for error in self.errors_for(root)))

    def test_generated_evidence_requires_registered_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            evidence_path = root / "tasks/SR-002/evidence.jsonl"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence.pop("artifact_id")
            evidence_path.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            self.assertTrue(any("requires artifact_id" in error for error in self.errors_for(root)))

    def test_artifact_cannot_escape_experiment_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            manifest = root / "artifacts/manifest.jsonl"
            artifact = json.loads(manifest.read_text(encoding="utf-8"))
            artifact["path"] = "tasks/SR-002/report.md"
            artifact["hash"] = "sha256:" + hashlib.sha256(
                (root / "tasks/SR-002/report.md").read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
            self.assertTrue(any("outside experiment ownership" in error for error in self.errors_for(root)))

    def test_artifact_producer_must_match_experiment_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            manifest = root / "artifacts/manifest.jsonl"
            artifact = json.loads(manifest.read_text(encoding="utf-8"))
            artifact["producer_task_id"] = "SR-001"
            manifest.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
            self.assertTrue(any("producer differs" in error for error in self.errors_for(root)))

    def test_fixed_seed_policy_requires_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["seed_policy"]["seeds"] = []
            write_json(path, experiment)
            self.assertTrue(any("requires at least one unique integer seed" in error for error in self.errors_for(root)))

    def test_completed_run_requires_exact_evidence_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            write_json(
                root / "evidence-index.json",
                {"schema_version": 3, "records": [{"evidence_id": "EV-SR-001-01"}]},
            )
            self.assertTrue(any("index every evidence ID" in error for error in self.errors_for(root)))

    def test_task_graph_must_match_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["task_graph"]["edges"] = []
            write_json(state_path, state)
            self.assertTrue(any("exactly match task dependencies" in error for error in self.errors_for(root)))

    def test_malformed_microarchitecture_contract_returns_errors_not_exceptions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["active_testing_approval"]["approved_task_ids"] = 7
            state["task_graph"]["edges"] = [[{}, "SR-002"]]
            write_json(state_path, state)
            task_path = root / "tasks/SR-002/task.json"
            active = json.loads(task_path.read_text(encoding="utf-8"))
            active["resource_requirements"] = []
            active["allowed_actions"] = [{}]
            write_json(task_path, active)
            errors = self.errors_for(root)
            self.assertTrue(errors)
            self.assertTrue(any("approved_task_ids" in error for error in errors))

    def test_planned_experiment_does_not_require_realized_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "running"
            state["resume"]["completed_tasks"] = ["SR-001"]
            write_json(state_path, state)

            for task_id in ("SR-002", "SR-003", "SR-004"):
                task_path = root / "tasks" / task_id / "task.json"
                task_data = json.loads(task_path.read_text(encoding="utf-8"))
                task_data["status"] = "pending"
                task_data["attempts"] = 0
                write_json(task_path, task_data)
            experiment_path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["status"] = "planned"
            write_json(experiment_path, experiment)

            (root / "tasks/SR-002/evidence.jsonl").unlink()
            (root / "tasks/SR-002/finding-001.json").unlink()
            (root / "artifacts/manifest.jsonl").unlink()
            (root / "experiments/EXP-001/results/run-001.log").unlink()
            self.assertEqual([], self.errors_for(root))

    def test_microarchitecture_json_contracts_fail_closed_on_arrays(self) -> None:
        for contract in ("experiment", "artifact", "evidence-index"):
            for payload in ("[]", "null"):
                with self.subTest(contract=contract, payload=payload), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_valid_run(root)
                    if contract == "experiment":
                        (root / "experiments/EXP-001/experiment.json").write_text(payload, encoding="utf-8")
                    elif contract == "artifact":
                        (root / "artifacts/manifest.jsonl").write_text(payload + "\n", encoding="utf-8")
                    else:
                        (root / "evidence-index.json").write_text(payload, encoding="utf-8")
                    errors = self.errors_for(root)
                    self.assertTrue(any("expected object" in error for error in errors), errors)

    def test_active_validation_requires_an_experiment_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            shutil.rmtree(root / "experiments")
            shutil.rmtree(root / "artifacts")
            errors, _ = preflight(root, strict_v3=True)
            self.assertTrue(any("requires at least one experiment contract" in error for error in errors), errors)

    def test_experiment_resources_must_fit_task_and_graph_reservations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["resource_budget"]["cpu"] = 999
            experiment["resource_budget"]["exclusive_resources"] = ["untracked-board"]
            write_json(path, experiment)
            errors = self.errors_for(root)
            self.assertTrue(any("exclusive resources are not declared" in error for error in errors), errors)
            self.assertTrue(any("cpu exceeds" in error for error in errors), errors)

    def test_artifact_must_bind_revision_contract_cell_seed_and_enums(self) -> None:
        mutations = {
            "experiment_revision": 2,
            "experiment_contract_hash": "sha256:" + "0" * 64,
            "cell_id": "CELL-UNKNOWN",
            "seed": None,
            "repetition_index": -1,
            "kind": [],
            "sensitivity": "secret-ish",
            "retention": 7,
            "generated_at": "yesterday",
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_valid_run(root)
                manifest = root / "artifacts/manifest.jsonl"
                artifact = json.loads(manifest.read_text(encoding="utf-8"))
                artifact[field] = value
                manifest.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
                self.assertTrue(self.errors_for(root))

    def test_experiment_contract_drift_invalidates_existing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["command_plan"] = ["run a changed approved command"]
            write_json(path, experiment)
            self.assertTrue(any("experiment_contract_hash differs" in error for error in self.errors_for(root)))

    def test_active_validation_evidence_always_requires_artifact_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            evidence_path = root / "tasks/SR-002/evidence.jsonl"
            evidence_record = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_record["kind"] = "analysis"
            evidence_record.pop("artifact_id")
            evidence_path.write_text(json.dumps(evidence_record) + "\n", encoding="utf-8")
            self.assertTrue(any("requires artifact_id" in error for error in self.errors_for(root)))

    def test_planned_experiment_rejects_stale_realized_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["status"] = "planned"
            write_json(path, experiment)
            errors = self.errors_for(root)
            self.assertTrue(any("completed may not own experiment status planned" in error for error in errors), errors)
            self.assertTrue(any("planned experiment must not have realized artifacts" in error for error in errors), errors)

    def test_cells_exactly_cover_seed_repetition_workload_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["seed_policy"] = {"mode": "fixed-list", "seeds": [1, 2], "repetitions": 2}
            write_json(path, experiment)
            self.assertTrue(any("uncovered cell/workload/seed/repetition" in error for error in self.errors_for(root)))

    def test_large_repetition_count_is_validated_without_materializing_the_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["seed_policy"]["repetitions"] = 100_000_000
            write_json(path, experiment)
            errors = self.errors_for(root)
            self.assertTrue(any("expected 100000000, found 1" in error for error in errors), errors)

    def test_verified_finding_requires_substantive_contract_fields(self) -> None:
        fields = ("title", "observation", "interpretation", "impact", "severity_rationale", "confidence_rationale")
        for field in fields:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_valid_run(root)
                path = root / "tasks/SR-002/finding-001.json"
                finding_record = json.loads(path.read_text(encoding="utf-8"))
                finding_record[field] = ""
                write_json(path, finding_record)
                self.assertTrue(any(field in error for error in self.errors_for(root)))

    def test_evidence_enums_and_verifier_support_link_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            evidence_path = root / "tasks/SR-003/evidence.jsonl"
            evidence_record = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_record["kind"] = []
            evidence_record["sensitivity"] = "unknown"
            evidence_record["supports"] = ["OTHER-FINDING"]
            evidence_path.write_text(json.dumps(evidence_record) + "\n", encoding="utf-8")
            errors = self.errors_for(root)
            self.assertTrue(any("invalid evidence kind" in error for error in errors), errors)
            self.assertTrue(any("invalid evidence sensitivity" in error for error in errors), errors)
            self.assertTrue(any("requires an independent verifier" in error for error in errors), errors)

    def test_cells_must_assign_exact_independent_variables_with_scalar_values(self) -> None:
        assignments = (
            {"unrelated-variable": "control"},
            {"configuration": None},
            {"configuration": ""},
        )
        for value in assignments:
            with self.subTest(assignments=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_valid_run(root)
                experiment_path = root / "experiments/EXP-001/experiment.json"
                experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
                experiment["cells"][0]["variable_assignments"] = value
                write_json(experiment_path, experiment)
                manifest_path = root / "artifacts/manifest.jsonl"
                artifact = json.loads(manifest_path.read_text(encoding="utf-8"))
                artifact["experiment_contract_hash"] = canonical_contract_hash(experiment)
                manifest_path.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
                errors = self.errors_for(root)
                self.assertTrue(
                    any("exactly match declared independent" in error or "non-null scalar" in error for error in errors),
                    errors,
                )

    def test_final_matrix_must_cover_every_finding_and_its_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            report_path = root / "final/final-report.md"
            report = report_path.read_text(encoding="utf-8")
            report = report.replace(
                "| F-SR-002-01 | verified | EV-SR-002-01, EV-SR-003-01 | local fixture | synthetic only |",
                "| C-SNAPSHOT | candidate | EV-SR-001-01 | local fixture | synthetic only |",
            )
            report_path.write_text(report, encoding="utf-8")
            errors = self.errors_for(root)
            self.assertTrue(any("omits finding claims" in error for error in errors), errors)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            report_path = root / "final/final-report.md"
            report = report_path.read_text(encoding="utf-8")
            report = report.replace("EV-SR-002-01, EV-SR-003-01", "EV-SR-002-01")
            report_path.write_text(report, encoding="utf-8")
            errors = self.errors_for(root)
            self.assertTrue(any("omits finding evidence" in error for error in errors), errors)

    def test_task_and_experiment_status_matrix_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            task_path = root / "tasks/SR-002/task.json"
            active = json.loads(task_path.read_text(encoding="utf-8"))
            active["status"] = "cancelled"
            write_json(task_path, active)
            experiment_path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["status"] = "running"
            write_json(experiment_path, experiment)
            errors = self.errors_for(root)
            self.assertTrue(any("cancelled may not own experiment status running" in error for error in errors), errors)

    def test_boolean_experiment_revisions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            experiment_path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["revision"] = True
            write_json(experiment_path, experiment)
            manifest_path = root / "artifacts/manifest.jsonl"
            artifact = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact["experiment_revision"] = True
            artifact["experiment_contract_hash"] = canonical_contract_hash(experiment)
            manifest_path.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
            errors = self.errors_for(root)
            self.assertTrue(any("invalid experiment revision" in error for error in errors), errors)
            self.assertTrue(any("positive integer" in error for error in errors), errors)

    def test_experiment_storage_budget_must_fit_task_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            experiment_path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["resource_budget"]["storage_gb"] = 10**12
            write_json(experiment_path, experiment)
            self.assertTrue(any("storage_gb exceeds" in error for error in self.errors_for(root)))

    def test_non_finite_json_resource_values_are_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_valid_run(root)
                task_path = root / "tasks/SR-002/task.json"
                active = json.loads(task_path.read_text(encoding="utf-8"))
                active["resource_requirements"]["cpu"] = value
                write_json(task_path, active)
                errors = self.errors_for(root)
                self.assertTrue(any("non-standard JSON numeric constant" in error for error in errors), errors)

    def test_experiment_command_plan_is_bound_to_task_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            experiment_path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["command_plan"] = ["connect to an unapproved external device and mutate it"]
            write_json(experiment_path, experiment)
            errors = self.errors_for(root)
            self.assertTrue(any("task allowed_actions" in error for error in errors), errors)
            self.assertTrue(any("unapproved or out-of-scope" in error for error in errors), errors)

    def test_realized_artifact_must_fall_within_approval_time_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            manifest_path = root / "artifacts/manifest.jsonl"
            artifact = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact["generated_at"] = "2099-01-01T00:00:00Z"
            manifest_path.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
            errors = self.errors_for(root)
            self.assertTrue(any("outside its active approval time window" in error for error in errors), errors)

    def test_completed_experiment_rejects_unplanned_artifact_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            original_manifest = root / "artifacts/manifest.jsonl"
            original = json.loads(original_manifest.read_text(encoding="utf-8"))
            extra_path = root / "experiments/EXP-001/results/unplanned.log"
            extra_path.write_text("unplanned but well-formed\n", encoding="utf-8")
            extra = dict(original)
            extra["artifact_id"] = "ART-UNPLANNED"
            extra["path"] = "experiments/EXP-001/results/unplanned.log"
            extra["hash"] = "sha256:" + hashlib.sha256(extra_path.read_bytes()).hexdigest()
            original_manifest.write_text(
                json.dumps(original) + "\n" + json.dumps(extra) + "\n",
                encoding="utf-8",
            )
            errors = self.errors_for(root)
            self.assertTrue(any("unplanned artifact IDs" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
