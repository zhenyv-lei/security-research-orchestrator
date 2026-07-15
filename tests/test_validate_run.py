from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_run", ROOT / "scripts" / "validate_run.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def task(task_id: str, role: str, dependencies: list[str], mode: str) -> dict[str, object]:
    return {
        "schema_version": "1.1",
        "task_id": task_id,
        "role": role,
        "phase": "experiment" if role == "discovery" else "verification",
        "execution_mode": mode,
        "objective": "test objective",
        "research_question": "Does the controlled observation support the hypothesis?",
        "dependencies": dependencies,
        "assigned_paths": [],
        "inputs": [],
        "target_snapshot": {
            "commit": "0123456789abcdef",
            "rtl_config": "TestConfig",
            "target_class": "cycle-simulator",
            "toolchain": ["verilator:test"],
            "workloads": ["WL-001"],
        },
        "resource_requirements": {
            "cpu": 2,
            "memory_gb": 4,
            "wall_time_minutes": 5,
            "exclusive_resources": [],
        },
        "allowed_actions": ["local simulation"],
        "prohibited_actions": ["external targets"],
        "expected_outputs": ["report.md", "evidence.jsonl"],
        "acceptance_criteria": ["artifacts recorded"],
        "evidence_requirements": ["raw log"],
        "stop_conditions": ["scope change"],
        "escalation_conditions": ["authorization missing"],
        "fallback_of": None,
        "status": "completed",
        "attempts": 1,
        "max_attempts": 2,
    }


class ValidatorTests(unittest.TestCase):
    def make_valid_run(self, root: Path) -> None:
        state = {
            "schema_version": "1.1",
            "run_id": "SR-RUN-TEST",
            "objective": "validate a controlled local microarchitecture study",
            "research_profile": "microarchitecture-security",
            "scope": {
                "assets": ["local RTL"],
                "versions": ["0123456789abcdef"],
                "environments": ["isolated simulator"],
                "target_snapshot": {
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
                },
            },
            "authorization_tier": "A1",
            "authorization": {
                "owner": "test owner",
                "evidence": ["local fixture"],
                "time_window": None,
                "method_classes": ["local simulation"],
                "rate_limits": [],
                "rollback_plan": "discard fixture",
                "data_handling": "local only",
                "output_audience": "test",
            },
            "active_testing_approved": False,
            "allowed_actions": ["local simulation"],
            "prohibited_actions": ["external interaction"],
            "completion_criteria": ["independent verification"],
            "task_ids": ["SR-001", "SR-002"],
            "task_graph": {
                "edges": [["SR-001", "SR-002"]],
                "waves": [["SR-001"], ["SR-002"]],
                "exclusive_resources": [],
            },
            "artifact_roots": {"tasks": "tasks", "experiments": "experiments", "artifacts": "artifacts"},
            "resume": {
                "checkpoint_id": "CP-2",
                "completed_tasks": ["SR-001", "SR-002"],
                "retryable_tasks": [],
                "blocked_tasks": [],
                "next_actions": [],
            },
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
        write_json(root / "tasks/SR-001/task.json", task("SR-001", "discovery", [], "local-simulation"))
        write_json(root / "tasks/SR-002/task.json", task("SR-002", "verification", ["SR-001"], "read-only"))
        for task_id in ("SR-001", "SR-002"):
            task_dir = root / "tasks" / task_id
            (task_dir / "report.md").write_text("complete\n", encoding="utf-8")
        evidence = {
            "evidence_id": "EV-SR-001-01",
            "task_id": "SR-001",
            "kind": "simulation_log",
            "locator": "ART-EXP-001-001",
            "artifact_id": "ART-EXP-001-001",
            "observation": "controlled local observation",
            "supports": ["F-SR-001-01"],
            "sensitivity": "internal",
        }
        (root / "tasks/SR-001/evidence.jsonl").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
        verifier_evidence = {
            "evidence_id": "EV-SR-002-01",
            "task_id": "SR-002",
            "kind": "analysis",
            "locator": "tasks/SR-002/report.md",
            "observation": "independent control reproduces the observation",
            "supports": ["F-SR-001-01"],
            "sensitivity": "internal",
        }
        (root / "tasks/SR-002/evidence.jsonl").write_text(json.dumps(verifier_evidence) + "\n", encoding="utf-8")
        finding = json.loads((ROOT / "assets/templates/finding.json").read_text(encoding="utf-8"))
        finding.update(
            {
                "title": "Controlled test finding",
                "observation": "controlled local observation",
                "interpretation": "supports the local hypothesis",
                "impact": "test only",
                "evidence_ids": ["EV-SR-001-01"],
                "verification_status": "verified",
                "verifier_task_id": "SR-002",
            }
        )
        write_json(root / "tasks/SR-001/finding-001.json", finding)
        experiment = json.loads((ROOT / "assets/templates/experiment.json").read_text(encoding="utf-8"))
        experiment.update(
            {
                "task_id": "SR-001",
                "hypothesis": "A controlled local observation is reproducible.",
                "variables": {
                    "independent": ["stimulus class"],
                    "dependent": ["cycle count"],
                    "controlled": ["commit and config"],
                    "nuisance": [],
                },
                "target_snapshot": {
                    "commit": "0123456789abcdef",
                    "rtl_config": "TestConfig",
                    "target_class": "cycle-simulator",
                    "toolchain": ["verilator:test"],
                    "reference_model": "ref:test",
                },
                "workloads": ["WL-001"],
                "controls": ["negative control"],
                "observables": ["cycle count"],
                "seed_policy": {"mode": "fixed-list", "seeds": [1], "repetitions": 1},
                "command_plan": ["run local simulator"],
                "expected_artifacts": ["ART-EXP-001-001"],
                "acceptance_criteria": ["control reproduced"],
                "inconclusive_criteria": ["run truncated"],
                "resource_exhaustion_criteria": ["resource budget exceeded"],
                "stop_conditions": ["snapshot drift"],
                "status": "completed",
            }
        )
        write_json(root / "experiments/EXP-001/experiment.json", experiment)
        artifact_path = root / "experiments/EXP-001/results/run-001.log"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("controlled result\n", encoding="utf-8")
        artifact_hash = "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        artifact = json.loads((ROOT / "assets/templates/artifact-record.json").read_text(encoding="utf-8"))
        artifact.update(
            {
                "producer_task_id": "SR-001",
                "hash": artifact_hash,
                "target_snapshot": {
                    "commit": "0123456789abcdef",
                    "rtl_config": "TestConfig",
                    "target_class": "cycle-simulator",
                },
                "generated_at": "2026-07-15T00:00:00Z",
            }
        )
        manifest = root / "artifacts/manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(artifact) + "\n", encoding="utf-8")
        (root / "final").mkdir(parents=True, exist_ok=True)
        (root / "final/final-report.md").write_text(
            (ROOT / "assets/templates/final-report.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        write_json(
            root / "evidence-index.json",
            {
                "schema_version": "1.1",
                "records": [
                    {"evidence_id": "EV-SR-001-01"},
                    {"evidence_id": "EV-SR-002-01"},
                ],
            },
        )
        write_json(root / "conflicts.json", {"schema_version": "1.1", "conflicts": []})

    def test_valid_microarchitecture_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            self.assertEqual([], VALIDATOR.validate_run(root))

    def test_dependency_cycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            first = json.loads((root / "tasks/SR-001/task.json").read_text(encoding="utf-8"))
            first["dependencies"] = ["SR-002"]
            write_json(root / "tasks/SR-001/task.json", first)
            state = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
            state["task_graph"]["edges"] = [["SR-002", "SR-001"], ["SR-001", "SR-002"]]
            write_json(root / "run-state.json", state)
            self.assertTrue(any("cycle" in error for error in VALIDATOR.validate_run(root)))

    def test_self_verification_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-001/finding-001.json"
            finding = json.loads(path.read_text(encoding="utf-8"))
            finding["verifier_task_id"] = "SR-001"
            write_json(path, finding)
            self.assertTrue(any("distinct verifier" in error for error in VALIDATOR.validate_run(root)))

    def test_unpinned_experiment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["target_snapshot"]["commit"] = ""
            write_json(path, experiment)
            self.assertTrue(any("target_snapshot.commit" in error for error in VALIDATOR.validate_run(root)))

    def test_cross_layer_snapshot_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["target_snapshot"]["rtl_config"] = "DifferentConfig"
            write_json(path, experiment)
            self.assertTrue(any("differs from run snapshot" in error for error in VALIDATOR.validate_run(root)))

    def test_missing_manifest_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            (root / "experiments/EXP-001/results/run-001.log").unlink()
            self.assertTrue(any("does not exist" in error for error in VALIDATOR.validate_run(root)))

    def test_empty_experiment_contract_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(path.read_text(encoding="utf-8"))
            experiment["controls"] = []
            write_json(path, experiment)
            self.assertTrue(any("controls must be a non-empty list" in error for error in VALIDATOR.validate_run(root)))

    def test_non_verification_role_cannot_verify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            path = root / "tasks/SR-002/task.json"
            verifier = json.loads(path.read_text(encoding="utf-8"))
            verifier["role"] = "analysis"
            write_json(path, verifier)
            self.assertTrue(any("completed verification-role" in error for error in VALIDATOR.validate_run(root)))

    def test_planned_experiment_does_not_require_realized_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_run(root)
            state_path = root / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "planning"
            state["resume"]["completed_tasks"] = []
            write_json(state_path, state)
            for task_id in ("SR-001", "SR-002"):
                task_path = root / "tasks" / task_id / "task.json"
                task_data = json.loads(task_path.read_text(encoding="utf-8"))
                task_data["status"] = "pending"
                task_data["attempts"] = 0
                write_json(task_path, task_data)
            experiment_path = root / "experiments/EXP-001/experiment.json"
            experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
            experiment["status"] = "planned"
            write_json(experiment_path, experiment)
            evidence_path = root / "tasks/SR-001/evidence.jsonl"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence.pop("artifact_id", None)
            evidence_path.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            (root / "tasks/SR-001/finding-001.json").unlink()
            (root / "artifacts/manifest.jsonl").unlink()
            (root / "experiments/EXP-001/results/run-001.log").unlink()
            self.assertEqual([], VALIDATOR.validate_run(root))


if __name__ == "__main__":
    unittest.main()
