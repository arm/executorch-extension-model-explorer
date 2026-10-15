# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0
"""Release notifications only raise the intended dependency lower bound."""

import importlib.util
import subprocess  # nosec B404: exercise the repository script without a shell.
import sys
import unittest
from pathlib import Path

import pytest
import tomlkit
from packaging.requirements import Requirement

_ASSERT = unittest.TestCase()

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts/update-dependency-pin.py"
)
SPEC = importlib.util.spec_from_file_location("dependency_updater", SCRIPT)
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


def test_umbrella_only_declares_its_direct_plugins():
    document = tomlkit.parse(
        (SCRIPT.parents[1] / "pyproject.toml").read_text()
    )
    names = {
        Requirement(value).name
        for value in document["project"]["dependencies"]
    }
    _ASSERT.assertEqual(
        names,
        {
            "pte-adapter-model-explorer",
            "etrecord-adapter-model-explorer",
            "etdump-data-provider-model-explorer",
        },
    )
    _ASSERT.assertEqual(set(updater.DEPENDENCIES), names)


@pytest.mark.parametrize(
    "dependency",
    [
        "vgf-adapter-model-explorer",
        "tosa-adapter-model-explorer",
        "executorch",
        "flatbuffers",
        "ai-edge-model-explorer",
    ],
)
def test_rejects_transitive_dependency_updates(tmp_path, dependency):
    project = tmp_path / "pyproject.toml"
    content = f'[project]\ndependencies = ["{dependency}>=0.1.0"]\n'
    project.write_text(content)
    with pytest.raises(ValueError, match="Unsupported dependency"):
        updater.update_dependency(project, dependency, "v0.5.1")
    _ASSERT.assertEqual(project.read_text(), content)


@pytest.mark.parametrize("dependency", updater.DEPENDENCIES)
def test_update_preserves_other_constraints(tmp_path, dependency):
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\nversion = "0.1.0"\n'
        f'dependencies = ["{dependency}>=0.1.0,<0.6.0", "other==1.0"]\n'
        '# retained comment\n[dependency-groups]\ndev = ["pytest"]\n'
    )
    _ASSERT.assertTrue(
        updater.update_dependency(project, dependency, "refs/tags/v0.5.1")
    )
    contents = project.read_text()
    document = tomlkit.parse(contents)
    requirements = document["project"]["dependencies"]
    _ASSERT.assertEqual(
        Requirement(requirements[0]).specifier,
        Requirement(f"{dependency}>=0.5.1,<0.6.0").specifier,
    )
    _ASSERT.assertEqual(requirements[1], "other==1.0")
    _ASSERT.assertEqual(document["project"]["version"], "0.1.0")
    _ASSERT.assertEqual(document["dependency-groups"]["dev"], ["pytest"])
    _ASSERT.assertIn("# retained comment", contents)


@pytest.mark.parametrize(
    "version", ["0.5.1", "v0.5.1", "refs/tags/v0.5.1", "v00.5.1"]
)
def test_normalize_version(version):
    _ASSERT.assertEqual(updater.normalize_version(version), "0.5.1")


@pytest.mark.parametrize(
    "version",
    [
        "",
        "v1",
        "v1.2",
        "1!1.2.3",
        "v1.2.3+local",
        "v0.5.1rc1",
        "v0.5.1-pre-release",
        "refs/tags/v0.5.1.dev2",
        "v0.5.1.post1",
        "v0.5.1.0",
        '1.2.3"; echo bad',
        "1.2.3\nbranch=main",
    ],
)
def test_invalid_versions_do_not_modify_files(tmp_path, version):
    project = tmp_path / "pyproject.toml"
    content = (
        '[project]\ndependencies = ["pte-adapter-model-explorer>=0.4.1"]\n'
    )
    project.write_text(content)
    with pytest.raises(ValueError, match="Expected a clean release version"):
        updater.update_dependency(
            project, "pte-adapter-model-explorer", version
        )
    _ASSERT.assertEqual(project.read_text(), content)


@pytest.mark.parametrize("version", ["0.4.1", "0.5.0"])
def test_repeated_or_older_release_is_noop(tmp_path, version):
    project = tmp_path / "pyproject.toml"
    content = (
        '[project]\ndependencies = ["pte-adapter-model-explorer>=0.5.0"]\n'
    )
    project.write_text(content)
    _ASSERT.assertFalse(
        updater.update_dependency(
            project, "pte-adapter-model-explorer", version
        )
    )
    _ASSERT.assertEqual(project.read_text(), content)


def test_prerelease_cannot_downgrade_stable_release(tmp_path):
    project = tmp_path / "pyproject.toml"
    content = (
        '[project]\ndependencies = ["pte-adapter-model-explorer>=0.5.1"]\n'
    )
    project.write_text(content)
    with pytest.raises(ValueError, match="Expected a clean release version"):
        updater.update_dependency(
            project, "pte-adapter-model-explorer", "v0.5.1rc1"
        )
    _ASSERT.assertEqual(project.read_text(), content)


@pytest.mark.parametrize("constraint", [">=0.4.1,<0.5.0", ">=0.4.1,!=0.5.0"])
def test_rejects_incompatible_release(tmp_path, constraint):
    project = tmp_path / "pyproject.toml"
    content = f'[project]\ndependencies = ["pte-adapter-model-explorer{constraint}"]\n'
    project.write_text(content)
    with pytest.raises(ValueError, match="violates existing constraints"):
        updater.update_dependency(
            project, "pte-adapter-model-explorer", "0.5.0"
        )
    _ASSERT.assertEqual(project.read_text(), content)


def test_missing_or_unsupported_dependency(tmp_path):
    project = tmp_path / "pyproject.toml"
    content = '[project]\ndependencies = ["other>=0.1.0"]\n'
    project.write_text(content)
    with pytest.raises(ValueError, match="not found"):
        updater.update_dependency(
            project, "pte-adapter-model-explorer", "0.5.0"
        )
    with pytest.raises(ValueError, match="Unsupported"):
        updater.update_dependency(project, "other", "0.5.0")
    _ASSERT.assertEqual(project.read_text(), content)


def test_cli_outputs_are_normalized(tmp_path):
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\ndependencies = ["pte-adapter-model-explorer>=0.4.1"]\n'
    )
    output = tmp_path / "github-output"
    subprocess.run(  # nosec B603: current Python, repository script and test-owned arguments.
        [
            sys.executable,
            str(SCRIPT),
            "pte-adapter-model-explorer",
            "v0.5.1",
            "--pyproject",
            str(project),
            "--github-output",
            str(output),
        ],
        check=True,
    )
    _ASSERT.assertEqual(
        output.read_text(),
        "dependency=pte-adapter-model-explorer\nversion=0.5.1\n",
    )
