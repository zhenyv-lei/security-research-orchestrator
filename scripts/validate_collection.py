#!/usr/bin/env python3
"""Validate the repository-level skill catalog and JSON assets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog.json"
NAME_RE = re.compile(r"^name:\s*([a-z0-9-]+)\s*$", re.MULTILINE)


def main() -> int:
    errors: list[str] = []
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read catalog.json: {exc}")
        return 1

    declared: dict[str, Path] = {}
    seen_paths: set[Path] = set()
    categories = catalog.get("categories")
    if not isinstance(categories, list):
        errors.append("catalog.categories must be a list")
        categories = []

    for category in categories:
        if not isinstance(category, dict) or not isinstance(category.get("skills"), list):
            errors.append("every catalog category must contain a skills list")
            continue
        for skill in category["skills"]:
            if not isinstance(skill, dict):
                errors.append("every catalog skill must be an object")
                continue
            name = skill.get("name")
            path_value = skill.get("path")
            entrypoint_value = skill.get("entrypoint")
            if not all(isinstance(value, str) and value for value in (name, path_value, entrypoint_value)):
                errors.append("catalog skill name, path, and entrypoint must be non-empty strings")
                continue
            path = (ROOT / path_value).resolve()
            entrypoint = (ROOT / entrypoint_value).resolve()
            try:
                path.relative_to(ROOT)
                entrypoint.relative_to(ROOT)
            except ValueError:
                errors.append(f"catalog path escapes repository: {name}")
                continue
            if name in declared:
                errors.append(f"duplicate skill name: {name}")
            if path in seen_paths:
                errors.append(f"duplicate skill path: {path_value}")
            declared[name] = path
            seen_paths.add(path)
            if entrypoint != path / "SKILL.md":
                errors.append(f"entrypoint does not match skill path: {name}")
            if not entrypoint.is_file():
                errors.append(f"missing entrypoint: {entrypoint_value}")
                continue
            match = NAME_RE.search(entrypoint.read_text(encoding="utf-8"))
            if not match or match.group(1) != name:
                errors.append(f"SKILL.md name does not match catalog: {name}")
            if not (path / "agents" / "openai.yaml").is_file():
                errors.append(f"missing agents/openai.yaml: {name}")
            origin = skill.get("origin")
            if origin is not None:
                if not isinstance(origin, dict):
                    errors.append(f"origin must be an object: {name}")
                else:
                    license_value = origin.get("license")
                    license_file_value = origin.get("license_file")
                    if not isinstance(license_value, str) or not license_value:
                        errors.append(f"origin license must be non-empty: {name}")
                    if not isinstance(license_file_value, str) or not license_file_value:
                        errors.append(f"origin license_file must be non-empty: {name}")
                    else:
                        license_path = (ROOT / license_file_value).resolve()
                        try:
                            license_path.relative_to(ROOT)
                        except ValueError:
                            errors.append(f"origin license_file escapes repository: {name}")
                        else:
                            if not license_path.is_file():
                                errors.append(f"missing origin license_file: {name}")

    discovered = {
        path.parent.resolve()
        for path in (ROOT / "skills").glob("*/*/SKILL.md")
        if path.is_file()
    }
    undeclared = sorted(path.relative_to(ROOT).as_posix() for path in discovered - seen_paths)
    missing = sorted(path.relative_to(ROOT).as_posix() for path in seen_paths - discovered)
    if undeclared:
        errors.append("uncataloged skills: " + ", ".join(undeclared))
    if missing:
        errors.append("catalog paths without SKILL.md: " + ", ".join(missing))

    relationships = catalog.get("relationships")
    if not isinstance(relationships, list):
        errors.append("catalog.relationships must be a list")
    else:
        for relationship in relationships:
            if not isinstance(relationship, dict):
                errors.append("every catalog relationship must be an object")
                continue
            source = relationship.get("from")
            target = relationship.get("to")
            relation_type = relationship.get("type")
            if source not in declared:
                errors.append(f"relationship has unknown source: {source}")
            if target not in declared:
                errors.append(f"relationship has unknown target: {target}")
            if not isinstance(relation_type, str) or not relation_type:
                errors.append("relationship type must be a non-empty string")

    for path in ROOT.rglob("*.json"):
        if ".git" in path.parts:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: cataloged {len(declared)} skills; all entrypoints and JSON assets are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
