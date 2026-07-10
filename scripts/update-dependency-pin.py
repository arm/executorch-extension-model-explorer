#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

"""Update one adapter package dependency lower bound in pyproject.toml."""

import argparse
from pathlib import Path

DEPENDENCY_ALIASES = {
    "pte-adapter-model-explorer": "pte-adapter-model-explorer",
    "etrecord-adapter-model-explorer": "etrecord-adapter-model-explorer",
    "etdump-data-provider-model-explorer": "etdump-data-provider-model-explorer",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update a package lower bound in pyproject.toml"
    )
    parser.add_argument(
        "dependency",
        choices=sorted(DEPENDENCY_ALIASES),
        help="Dependency package name to update",
    )
    parser.add_argument(
        "version",
        help="Version or release tag to use as the lower bound, for example 0.1.0 or v0.1.0",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml",
    )
    return parser.parse_args()


def normalize_version(version: str) -> str:
    version = version.strip()
    if version.startswith("refs/tags/"):
        version = version.removeprefix("refs/tags/")
    return version.removeprefix("v")


def update_dependency(pyproject: Path, dependency: str, version: str) -> None:
    package = DEPENDENCY_ALIASES[dependency]
    replacement = f'  "{package}>={normalize_version(version)}",'

    lines = pyproject.read_text(encoding="utf-8").splitlines()
    in_project = False
    in_dependencies = False
    updated = False

    for index, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            in_dependencies = False
            continue

        if in_project and stripped == "dependencies = [":
            in_dependencies = True
            continue

        if in_dependencies and stripped == "]":
            in_dependencies = False
            continue

        if in_dependencies and stripped.startswith(f'"{package}'):
            lines[index] = replacement
            updated = True
            break

    if not updated:
        raise SystemExit(
            f"Dependency not found in [project].dependencies: {package}"
        )

    pyproject.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    update_dependency(args.pyproject, args.dependency, args.version)


if __name__ == "__main__":
    main()
