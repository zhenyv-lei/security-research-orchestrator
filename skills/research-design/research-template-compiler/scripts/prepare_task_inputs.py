#!/usr/bin/env python3
"""Materialize only declared upstream output projections for one isolated task."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compile_research import SCHEMA_VERSION, canonical_hash, read_json, write_json


def prepare_task_inputs(run_dir: Path, task_id: str) -> list[Path]:
    run_dir = run_dir.resolve()
    task_path = run_dir / "tasks" / task_id / "task.json"
    task = read_json(task_path)
    if task.get("task_id") != task_id:
        raise ValueError(f"task ID mismatch: {task_id}")

    written: list[Path] = []
    for item in task.get("inputs", []):
        reference = item.get("reference")
        artifact = item.get("artifact")
        source = item.get("source_artifact")
        if not all(isinstance(value, str) and value for value in (reference, artifact, source)):
            raise ValueError(f"malformed input contract for task {task_id}")
        producer_id, output_name = reference.split(".", 1)
        expected_source = f"slots/{producer_id}/proposal.json#outputs/{output_name}"
        expected_artifact = f"inbox/{task_id}/{producer_id}.{output_name}.json"
        if source != expected_source or artifact != expected_artifact:
            raise ValueError(f"input contract path mismatch for {reference}")

        proposal_path = run_dir / "slots" / producer_id / "proposal.json"
        proposal = read_json(proposal_path)
        outputs = proposal.get("outputs")
        if not isinstance(outputs, dict) or output_name not in outputs:
            raise ValueError(f"missing declared upstream output: {reference}")
        destination = (run_dir / artifact).resolve()
        try:
            destination.relative_to(run_dir)
        except ValueError as exc:
            raise ValueError(f"input projection escapes run directory: {artifact}") from exc
        write_json(
            destination,
            {
                "schema_version": SCHEMA_VERSION,
                "reference": reference,
                "source_proposal_hash": canonical_hash(proposal),
                "value": outputs[output_name],
            },
        )
        written.append(destination)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("task_id")
    args = parser.parse_args()
    try:
        written = prepare_task_inputs(args.run_dir, args.task_id)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"OK: materialized {len(written)} input projections for {args.task_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
