#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

"""Raise an adapter dependency lower bound without discarding other constraints."""

import argparse
from pathlib import Path

import tomlkit
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

DEPENDENCIES = (
    "pte-adapter-model-explorer",
    "etrecord-adapter-model-explorer",
    "etdump-data-provider-model-explorer",
)


def normalize_version(version: str) -> str:
    version = version.strip().removeprefix("refs/tags/").removeprefix("v")
    try:
        parsed = Version(version)
    except InvalidVersion as exc:
        raise ValueError(
            "Expected a package version such as v0.1.2 or v0.1.2rc1"
        ) from exc
    if len(parsed.release) != 3 or parsed.local is not None or parsed.epoch:
        raise ValueError(
            "Expected a package version without a local suffix or epoch"
        )
    return str(parsed)


def update_dependency(pyproject: Path, dependency: str, version: str) -> bool:
    if dependency not in DEPENDENCIES:
        raise ValueError(f"Unsupported dependency: {dependency}")
    version = normalize_version(version)
    incoming = Version(version)
    document = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
    requirements = document["project"]["dependencies"]
    for index, value in enumerate(requirements):
        requirement = Requirement(str(value))
        if canonicalize_name(requirement.name) != dependency:
            continue
        lower_bounds = [s for s in requirement.specifier if s.operator == ">="]
        if len(lower_bounds) != 1:
            raise ValueError(f"Expected one >= lower bound for {dependency}")
        current = lower_bounds[0]
        # A delayed or repeated notification must not downgrade main.
        if incoming <= Version(current.version):
            return False
        remaining = [s for s in requirement.specifier if s != current]
        constraints = SpecifierSet(",".join(str(s) for s in remaining))
        if not constraints.contains(incoming, prereleases=True):
            raise ValueError(
                f"{dependency} {version} violates existing constraints {constraints}"
            )
        requirement.specifier = SpecifierSet(
            ",".join([f">={version}", *(str(s) for s in remaining)])
        )
        requirements[index] = str(requirement)
        pyproject.write_text(tomlkit.dumps(document), encoding="utf-8")
        return True
    raise ValueError(
        f"Dependency not found in [project].dependencies: {dependency}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dependency", choices=DEPENDENCIES)
    parser.add_argument(
        "version", help="Release version or tag, including prereleases"
    )
    parser.add_argument(
        "--pyproject", type=Path, default=Path("pyproject.toml")
    )
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    version = normalize_version(args.version)
    update_dependency(args.pyproject, args.dependency, version)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"dependency={args.dependency}\nversion={version}\n")


if __name__ == "__main__":
    main()
