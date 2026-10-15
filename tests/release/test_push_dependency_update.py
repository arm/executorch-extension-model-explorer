# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0
"""Exercise direct updates against disposable local Git repositories."""

import os
import shlex
import shutil
import subprocess  # nosec B404: only local test repositories and trusted scripts.
import sys
import unittest
from pathlib import Path

import pytest

_ASSERT = unittest.TestCase()
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
GIT = shutil.which("git")
BASH = shutil.which("bash")
PTE = "pte-adapter-model-explorer"
ETRECORD = "etrecord-adapter-model-explorer"


def run(cwd, *command, check=True):
    env = dict(os.environ)
    env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env['PATH']}"
    return subprocess.run(  # nosec B603: test-owned arguments, no shell.
        command, cwd=cwd, env=env, check=check, capture_output=True, text=True
    )


def git(cwd, *args):
    return run(cwd, GIT, *args).stdout.strip()


def push_update(work, version="v0.5.1", check=True):
    return run(
        work,
        BASH,
        "scripts/push-dependency-update.sh",
        PTE,
        version,
        check=check,
    )


@pytest.fixture
def repos(tmp_path):
    if os.name != "posix":
        pytest.skip("Direct-push workflow runs on Ubuntu, not Windows")
    if not GIT or not BASH:
        pytest.skip("Git and Bash required for workflow tests")
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    peer = tmp_path / "peer"
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    git(tmp_path, "clone", str(remote), str(work))
    git(work, "config", "user.name", "Workflow test")
    git(work, "config", "user.email", "workflow@example.invalid")
    git(work, "config", "commit.gpgsign", "false")
    (work / "scripts").mkdir()
    for name in ("update-dependency-pin.py", "push-dependency-update.sh"):
        shutil.copyfile(SCRIPTS / name, work / "scripts" / name)
    (work / "pyproject.toml").write_text(
        f'[project]\ndependencies = ["{PTE}>=0.4.1", "{ETRECORD}>=0.1.0"]\n'
    )
    git(work, "add", ".")
    git(work, "commit", "-m", "Initial test state")
    git(work, "push", "origin", "main")
    git(tmp_path, "clone", str(remote), str(peer))
    git(peer, "config", "user.name", "Concurrent workflow test")
    git(peer, "config", "user.email", "workflow@example.invalid")
    git(peer, "config", "commit.gpgsign", "false")
    return remote, work, peer


def test_pushes_only_dependency_file_and_repeated_update_is_noop(repos):
    remote, work, _ = repos
    (work / "unrelated.txt").write_text("Must not be committed")
    push_update(work)
    first = git(remote, "rev-parse", "main")
    _ASSERT.assertIn(
        f"{PTE}>=0.5.1", git(remote, "show", "main:pyproject.toml")
    )
    _ASSERT.assertEqual(
        git(
            remote, "diff-tree", "--no-commit-id", "--name-only", "-r", "main"
        ),
        "pyproject.toml",
    )
    push_update(work)
    push_update(work, "v0.4.2")
    _ASSERT.assertEqual(git(remote, "rev-parse", "main"), first)


@pytest.mark.parametrize(
    "version", ["v0.5.1rc1", "v0.5.1-dev", "v0.5.1.post1"]
)
def test_nonclean_release_never_commits_or_pushes(repos, version):
    remote, work, _ = repos
    before = git(remote, "rev-parse", "main")
    result = push_update(work, version, check=False)
    _ASSERT.assertNotEqual(result.returncode, 0)
    _ASSERT.assertIn("Expected a clean release version", result.stderr)
    _ASSERT.assertEqual(git(remote, "rev-parse", "main"), before)
    _ASSERT.assertEqual(git(work, "status", "--porcelain"), "")


@pytest.mark.parametrize(
    "dependency,version", [(ETRECORD, "0.2.0"), (PTE, "0.6.0")]
)
def test_concurrent_update_is_preserved_without_downgrading(
    repos, dependency, version
):
    remote, work, peer = repos
    run(
        peer,
        sys.executable,
        "scripts/update-dependency-pin.py",
        dependency,
        version,
    )
    git(peer, "commit", "-am", "Concurrent dependency update")
    # Publish the competing commit after this workflow commits but before it pushes.
    hook = work / ".git/hooks/pre-push"
    hook.write_text(
        "#!/usr/bin/env bash\nset -eu\n"
        'rm -- "$0"\n'
        f"{shlex.quote(GIT)} -C {shlex.quote(str(peer))} push origin main\n"
    )
    hook.chmod(0o700)
    push_update(work)
    content = git(remote, "show", "main:pyproject.toml")
    _ASSERT.assertIn(f"{dependency}>={version}", content)
    if dependency == ETRECORD:
        _ASSERT.assertIn(f"{PTE}>=0.5.1", content)
    git(
        remote,
        "merge-base",
        "--is-ancestor",
        git(peer, "rev-parse", "HEAD"),
        "main",
    )


def test_push_rejection_fails_without_overriding_remote(repos):
    remote, work, _ = repos
    before = git(remote, "rev-parse", "main")
    hook = remote / "hooks/pre-receive"
    hook.write_text("#!/usr/bin/env bash\nexit 1\n")
    hook.chmod(0o700)
    result = push_update(work, check=False)
    _ASSERT.assertNotEqual(result.returncode, 0)
    _ASSERT.assertIn("Unable to push dependency update", result.stderr)
    _ASSERT.assertEqual(git(remote, "rev-parse", "main"), before)
