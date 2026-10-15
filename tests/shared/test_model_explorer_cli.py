# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

import os
import queue
import shutil
import socket
import subprocess  # nosec B404: exercise the installed CLI without a shell.
import sys
import threading
import time
import unittest
from pathlib import Path

import pytest

_ASSERT = unittest.TestCase()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    ("extensions", "searched_lines"),
    [
        ("pte_adapter_model_explorer", ["PTE Adapter"]),
        ("etrecord_adapter_model_explorer", ["ETRecord Adapter"]),
        (
            "etrecord_adapter_model_explorer,etdump_data_provider_model_explorer",
            ["ETRecord Adapter", "ETDump Profiling Overlay"],
        ),
        (
            "executorch_extension_model_explorer",
            ["PTE Adapter", "ETRecord Adapter", "ETDump Profiling Overlay"],
        ),
    ],
)
def test_model_explorer_smoke(
    extensions: str, searched_lines: list[str]
) -> None:
    cli_path = None
    local_cli = Path(sys.executable).parent / "model-explorer"
    if local_cli.is_file():
        cli_path = str(local_cli)
    if cli_path is None:
        cli_path = shutil.which("model-explorer")

    if cli_path is None:
        pytest.skip("model-explorer CLI is not installed in this environment")

    cmd = [
        cli_path,
        "--no_open_in_browser",
        f"--extensions={extensions}",
        "--host=127.0.0.1",
        f"--port={_unused_port()}",
    ]

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")
    repo_root = Path(__file__).resolve().parents[2]
    pythonpath_entries = [
        repo_root / "src",
    ]
    env["PYTHONPATH"] = os.pathsep.join(
        [str(path) for path in pythonpath_entries]
        + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )

    proc = subprocess.Popen(  # nosec B603: trusted CLI path and parametrized test arguments.
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
        universal_newlines=True,
        env=env,
    )

    seen_lines = dict.fromkeys(searched_lines, False)
    output_lines: list[str] = []
    deadline = time.monotonic() + 20

    if proc.stdout is None:
        raise AssertionError("Process stdout not captured")
    line_queue: queue.Queue[str] = queue.Queue()

    def read_output() -> None:
        if proc.stdout is None:
            raise AssertionError("Process stdout not captured")
        for line in proc.stdout:
            line_queue.put(line)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()

    try:
        while proc.poll() is None and time.monotonic() < deadline:
            try:
                line = line_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            output_lines.append(line)
            for searched_line in searched_lines:
                if searched_line in line:
                    seen_lines[searched_line] = True
            if all(seen_lines.values()):
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)

    _ASSERT.assertTrue(
        all(seen_lines.values()),
        msg=f"Not all expected lines were seen: {seen_lines}\nOutput:\n{''.join(output_lines)}",
    )


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
