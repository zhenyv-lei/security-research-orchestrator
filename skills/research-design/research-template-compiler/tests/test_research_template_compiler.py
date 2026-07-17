from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_research import (  # noqa: E402
    TemplateError,
    compile_research,
    resolve_template,
    validate_template,
)
from validate_run import refresh_run_state, validate_run  # noqa: E402
from prepare_task_inputs import prepare_task_inputs  # noqa: E402


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def scope_inputs() -> dict[str, object]:
    return {
        "locked_context": {
            "authorization_tier": "A1",
            "active_testing_approved": False,
            "allowed_actions": ["read-only review", "local controlled simulation"],
            "prohibited_actions": ["external target interaction"],
            "data_handling": "local only",
            "output_audience": "research team",
            "terminology_profile": "microarchitecture-research-zh",
        },
        "provided_slots": {
            "SCOPE": {
                "research_scope": {
                    "research_object": "pinned local RISC-V RTL snapshot",
                    "research_question": "Which controlled microarchitectural states merit study?",
                    "authorized_sources": ["local RTL", "public architecture documents"],
                    "scope": ["local RTL"],
                    "non_goals": ["external testing"],
                    "deliverable": "research plan",
                    "completion_criteria": ["verified experiment matrix"],
                }
            }
        },
    }


def proposal_for(slot: dict[str, object], status: str = "proposed") -> dict[str, object]:
    slot_id = str(slot["slot_id"])
    keywords = {keyword: f"value for {keyword}" for keyword in slot["required_keywords"]}
    outputs = {output: {"value": output} for output in slot["produces"]}
    reviewed = list(slot["depends_on"]) if slot["kind"] == "verification" else []
    return {
        "schema_version": "1.0",
        "slot_id": slot_id,
        "candidate_id": f"{slot_id}-C1",
        "filled_keywords": keywords,
        "outputs": outputs,
        "claims": [],
        "alternatives": ["alternative"],
        "unknowns": ["unknown"],
        "reviewed_slots": reviewed,
        "new_slot_proposals": [],
        "status": status,
    }


class CompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = ROOT / "assets/templates/base-research.json"
        self.micro = ROOT / "assets/templates/microarchitecture-security.json"

    def compile_micro(self, root: Path) -> Path:
        inputs_path = root / "inputs.json"
        run_dir = root / "run"
        write_json(inputs_path, scope_inputs())
        compile_research(self.micro, inputs_path, run_dir)
        return run_dir

    def test_inheritance_resolves_domain_slots_and_overrides(self) -> None:
        template = resolve_template(self.micro)
        validate_template(template)
        slots = {slot["slot_id"]: slot for slot in template["slots"]}
        self.assertIn("TARGET_SNAPSHOT", slots)
        self.assertIn("OBSERVATION_MODEL", slots)
        self.assertIn("experiment_matrix", slots["METHODS"]["produces"])
        self.assertIn("TARGET_SNAPSHOT", slots["VERIFICATION"]["depends_on"])
        self.assertEqual("A1", template["locked_context"]["authorization_tier"])

    def test_compiler_creates_narrow_artifact_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            task = json.loads((run_dir / "tasks/HYPOTHESES/task.json").read_text(encoding="utf-8"))
            references = {item["reference"] for item in task["inputs"]}
            self.assertEqual(
                {
                    "QUESTIONS.research_questions",
                    "ARCH_MAP.components",
                    "ARCH_MAP.security_boundaries",
                    "OBSERVATION_MODEL.observation_model",
                },
                references,
            )
            self.assertNotIn("CONTEXT.source_index", references)
            self.assertTrue(
                all(item["artifact"].startswith("inbox/HYPOTHESES/") for item in task["inputs"])
            )
            self.assertEqual(["slots/HYPOTHESES/"], task["assigned_paths"])
            self.assertEqual([], validate_run(run_dir))

    def test_materialized_inbox_contains_only_declared_output_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            slots = {slot["slot_id"]: slot for slot in template["slots"]}
            hypotheses = slots["HYPOTHESES"]
            for dependency in hypotheses["depends_on"]:
                path = run_dir / f"slots/{dependency}/proposal.json"
                if not path.exists():
                    proposal = proposal_for(slots[dependency], "evidenced")
                    proposal["claims"] = [
                        {
                            "claim_id": "hidden",
                            "statement": "must not enter inbox",
                            "evidence_ids": [],
                            "confidence": 0.99,
                        }
                    ]
                    write_json(path, proposal)
            written = prepare_task_inputs(run_dir, "HYPOTHESES")
            self.assertEqual(len(hypotheses["consumes"]), len(written))
            for path in written:
                projection = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    {"schema_version", "reference", "source_proposal_hash", "value"},
                    set(projection),
                )
                self.assertNotIn("claims", projection)
                self.assertNotIn("confidence", json.dumps(projection))

    def test_missing_human_slot_is_not_assigned_to_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs_path = root / "inputs.json"
            write_json(inputs_path, {"locked_context": {}, "provided_slots": {}})
            run_dir = root / "run"
            state = compile_research(self.base, inputs_path, run_dir)
            self.assertEqual("needs_input", state["status"])
            self.assertEqual(["SCOPE"], state["needs_input"])
            self.assertNotIn("SCOPE", state["task_ids"])
            self.assertFalse((run_dir / "tasks/SCOPE/task.json").exists())

    def test_empty_provided_human_keyword_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = scope_inputs()
            inputs["provided_slots"]["SCOPE"]["research_scope"]["research_question"] = ""
            inputs_path = root / "inputs.json"
            write_json(inputs_path, inputs)
            with self.assertRaisesRegex(TemplateError, "research_question"):
                compile_research(self.base, inputs_path, root / "run")

    def test_dependency_cycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = resolve_template(self.base)
            for slot in template["slots"]:
                if slot["slot_id"] == "CONTEXT":
                    slot["depends_on"] = ["SYNTHESIS"]
                    slot["consumes"] = ["SYNTHESIS.research_report"]
            path = root / "cycle.json"
            write_json(path, template)
            with self.assertRaisesRegex(TemplateError, "cycle"):
                validate_template(resolve_template(path))

    def test_inheritance_cannot_escape_template_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "outside.json", resolve_template(self.base))
            write_json(
                root / "templates/child.json",
                {
                    "schema_version": "1.0",
                    "template_id": "escape",
                    "description": "invalid",
                    "extends": "../outside.json",
                    "locked_context": {},
                    "slots": [],
                    "synthesis_slot": "SYNTHESIS",
                },
            )
            with self.assertRaisesRegex(TemplateError, "escapes"):
                resolve_template(root / "templates/child.json")

    def test_tampered_task_input_breaks_isolation_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            task_path = run_dir / "tasks/HYPOTHESES/task.json"
            task = json.loads(task_path.read_text(encoding="utf-8"))
            task["inputs"].append(
                {
                    "reference": "CONTEXT.source_index",
                    "artifact": "slots/CONTEXT/proposal.json#outputs/source_index",
                }
            )
            write_json(task_path, task)
            self.assertTrue(any("isolation" in error for error in validate_run(run_dir)))

    def test_missing_required_keyword_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            context = next(slot for slot in template["slots"] if slot["slot_id"] == "CONTEXT")
            proposal = proposal_for(context, "evidenced")
            proposal["filled_keywords"].pop("missing_context")
            write_json(run_dir / "slots/CONTEXT/proposal.json", proposal)
            self.assertTrue(any("missing keywords" in error for error in validate_run(run_dir)))

    def test_verifier_cannot_review_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            verifier = next(slot for slot in template["slots"] if slot["slot_id"] == "VERIFICATION")
            proposal = proposal_for(verifier, "verified")
            proposal["reviewed_slots"] = ["VERIFICATION"]
            write_json(run_dir / "slots/VERIFICATION/proposal.json", proposal)
            self.assertTrue(any("review itself" in error for error in validate_run(run_dir)))

    def test_valid_verifier_proposal_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            slots = {slot["slot_id"]: slot for slot in template["slots"]}
            verifier = next(slot for slot in template["slots"] if slot["slot_id"] == "VERIFICATION")
            for dependency in verifier["depends_on"]:
                path = run_dir / f"slots/{dependency}/proposal.json"
                if not path.exists():
                    write_json(path, proposal_for(slots[dependency], "evidenced"))
            proposal = proposal_for(verifier, "verified")
            write_json(run_dir / "slots/VERIFICATION/proposal.json", proposal)
            refresh_run_state(run_dir)
            self.assertEqual([], validate_run(run_dir))

    def test_verifier_requires_complete_review_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            verifier = next(slot for slot in template["slots"] if slot["slot_id"] == "VERIFICATION")
            proposal = proposal_for(verifier, "verified")
            proposal["reviewed_slots"] = ["CONTEXT"]
            write_json(run_dir / "slots/VERIFICATION/proposal.json", proposal)
            errors = validate_run(run_dir)
            self.assertTrue(any("every declared dependency" in error for error in errors), errors)
            self.assertTrue(any("missing reviewed proposal" in error for error in errors), errors)

    def test_locked_context_types_and_wildcards_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = scope_inputs()
            inputs["locked_context"]["allowed_actions"] = ["anything"]
            inputs_path = root / "inputs.json"
            write_json(inputs_path, inputs)
            with self.assertRaisesRegex(TemplateError, "wildcard"):
                compile_research(self.base, inputs_path, root / "run")

    def test_unknown_terminology_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = scope_inputs()
            inputs["locked_context"]["terminology_profile"] = "concealment-profile"
            inputs_path = root / "inputs.json"
            write_json(inputs_path, inputs)
            with self.assertRaisesRegex(TemplateError, "semantic-fidelity"):
                compile_research(self.base, inputs_path, root / "run")

    def test_non_list_prohibited_actions_is_rejected_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = scope_inputs()
            inputs["locked_context"]["prohibited_actions"] = 7
            inputs_path = root / "inputs.json"
            write_json(inputs_path, inputs)
            with self.assertRaisesRegex(TemplateError, "must be a list"):
                compile_research(self.base, inputs_path, root / "run")

    def test_deleted_task_set_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            state_path = run_dir / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["task_ids"] = []
            state["waves"] = []
            for slot_id in state["slot_states"]:
                state["slot_states"][slot_id] = "completed"
            write_json(state_path, state)
            for path in sorted((run_dir / "tasks").glob("*/*"), reverse=True):
                path.unlink()
            for path in sorted((run_dir / "tasks").glob("*"), reverse=True):
                path.rmdir()
            (run_dir / "tasks").rmdir()
            errors = validate_run(run_dir)
            self.assertTrue(any("derived from the template" in error for error in errors), errors)
            self.assertTrue(any("terminal state without a proposal" in error for error in errors), errors)

    def test_synthesis_cannot_complete_without_verification_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            synthesis = next(slot for slot in template["slots"] if slot["slot_id"] == "SYNTHESIS")
            proposal = proposal_for(synthesis, "completed")
            write_json(run_dir / "slots/SYNTHESIS/proposal.json", proposal)
            errors = validate_run(run_dir)
            self.assertTrue(any("missing synthesis dependency" in error for error in errors))

    def test_refresh_completes_full_proposal_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            for slot in template["slots"]:
                path = run_dir / f"slots/{slot['slot_id']}/proposal.json"
                if path.exists() or slot["kind"] == "locked":
                    continue
                if slot["kind"] == "verification":
                    status = "verified"
                elif slot["kind"] == "synthesis":
                    status = "completed"
                else:
                    status = "evidenced"
                write_json(path, proposal_for(slot, status))
            state = refresh_run_state(run_dir)
            self.assertEqual("completed", state["status"])
            self.assertEqual("completed", state["slot_states"]["SYNTHESIS"])
            for task_id in state["task_ids"]:
                task = json.loads(
                    (run_dir / f"tasks/{task_id}/task.json").read_text(encoding="utf-8")
                )
                self.assertEqual("completed", task["status"])
                self.assertEqual([], task["unresolved_dependencies"])
            self.assertEqual([], validate_run(run_dir))

    def test_shared_exclusive_resource_serializes_same_dependency_wave(self) -> None:
        template = resolve_template(self.base)
        slots = {slot["slot_id"]: slot for slot in template["slots"]}
        slots["HYPOTHESES"]["exclusive_resources"] = ["shared-model"]
        slots["COUNTERMODELS"]["exclusive_resources"] = ["shared-model"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template_path = root / "resource-template.json"
            inputs_path = root / "inputs.json"
            write_json(template_path, template)
            write_json(inputs_path, scope_inputs())
            run_dir = root / "run"
            state = compile_research(template_path, inputs_path, run_dir)
            hypothesis_wave = next(
                index for index, wave in enumerate(state["waves"]) if "HYPOTHESES" in wave
            )
            countermodel_wave = next(
                index for index, wave in enumerate(state["waves"]) if "COUNTERMODELS" in wave
            )
            self.assertNotEqual(hypothesis_wave, countermodel_wave)
            self.assertEqual(validate_run(run_dir), [])

    def test_tampered_wave_order_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            state_path = run_dir / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["waves"] = list(reversed(state["waves"]))
            write_json(state_path, state)
            errors = validate_run(run_dir)
            self.assertTrue(any("resource-safe schedule" in error for error in errors), errors)

    def test_tampered_task_contract_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            task_path = run_dir / "tasks/HYPOTHESES/task.json"
            task = json.loads(task_path.read_text(encoding="utf-8"))
            task["expected_output"] = "slots/OTHER/proposal.json"
            task["max_candidates"] = 999
            task["max_attempts"] = 999
            task["unresolved_dependencies"] = ["SCOPE"]
            write_json(task_path, task)
            errors = validate_run(run_dir)
            self.assertTrue(any("expected_output" in error for error in errors), errors)
            self.assertTrue(any("max_candidates" in error for error in errors), errors)
            self.assertTrue(any("retry contract" in error for error in errors), errors)
            self.assertTrue(any("unresolved_dependencies" in error for error in errors), errors)

    def test_blank_keyword_and_output_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            template = resolve_template(self.micro)
            context = next(slot for slot in template["slots"] if slot["slot_id"] == "CONTEXT")
            proposal = proposal_for(context, "evidenced")
            proposal["filled_keywords"]["known_facts"] = ""
            proposal["outputs"]["system_model"] = {}
            write_json(run_dir / "slots/CONTEXT/proposal.json", proposal)
            errors = validate_run(run_dir)
            self.assertTrue(any("blank keywords" in error for error in errors), errors)
            self.assertTrue(any("blank outputs" in error for error in errors), errors)

    def test_malformed_graph_expansion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            write_json(
                run_dir / "graph-expansion-proposals.json",
                {"schema_version": "1.0", "proposals": [{"suggested_slot_id": "NEW_SLOT"}]},
            )
            errors = validate_run(run_dir)
            self.assertTrue(any("new_slot_proposals" in error for error in errors), errors)

    def test_graph_expansion_semantics_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = self.compile_micro(Path(directory))
            write_json(
                run_dir / "graph-expansion-proposals.json",
                {
                    "schema_version": "1.0",
                    "proposals": [
                        {
                            "suggested_slot_id": "NEW_SLOT",
                            "reason": "",
                            "depends_on": ["MISSING"],
                            "consumes": ["CONTEXT.not_an_output"],
                            "produces": [7],
                            "scope_change": "no",
                        }
                    ],
                },
            )
            errors = validate_run(run_dir)
            self.assertTrue(any("reason must be non-empty" in error for error in errors), errors)
            self.assertTrue(any("scope_change must be boolean" in error for error in errors), errors)
            self.assertTrue(any("unknown dependencies" in error for error in errors), errors)
            self.assertTrue(any("invalid output names" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
