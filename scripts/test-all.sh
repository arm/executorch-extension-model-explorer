#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

set -u

PYTHON_BIN="${PYTHON:-python}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADAPTER_SOURCE_ROOT="${ADAPTER_SOURCE_ROOT:-$(cd "${REPO_ROOT}/.." && pwd)}"
status=0

run_tests() {
  local name="$1"
  local directory="$2"

  if [[ ! -d "$directory" ]]; then
    echo "Skipping $name: $directory does not exist"
    return
  fi

  if [[ ! -f "$directory/pyproject.toml" ]]; then
    echo "Skipping $name: $directory is not initialized"
    return
  fi

  echo "Running $name tests"
  (
    cd "$directory" || exit 1
    "$PYTHON_BIN" -m pytest -q
  )
  local result=$?
  if [[ $result -ne 0 ]]; then
    status=$result
  fi
}

run_tests "umbrella" "${REPO_ROOT}"
run_tests "PTE adapter" "${ADAPTER_SOURCE_ROOT}/pte-adapter-model-explorer"
run_tests "ETRecord adapter" "${ADAPTER_SOURCE_ROOT}/etrecord-adapter-model-explorer"
run_tests "ETDump data provider" "${ADAPTER_SOURCE_ROOT}/etdump-data-provider-model-explorer"

exit "$status"
