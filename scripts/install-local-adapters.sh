#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

PYTHON_BIN="${PYTHON:-python}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADAPTER_SOURCE_ROOT="${ADAPTER_SOURCE_ROOT:-$(cd "${REPO_ROOT}/.." && pwd)}"
ADAPTER_REMOTE_BASE="${ADAPTER_REMOTE_BASE:-https://github.com/arm}"
CLONE_MISSING="${CLONE_MISSING:-1}"

adapters=(
  "pte-adapter-model-explorer"
  "etrecord-adapter-model-explorer"
  "etdump-data-provider-model-explorer"
)

for adapter in "${adapters[@]}"; do
  adapter_dir="${ADAPTER_SOURCE_ROOT}/${adapter}"

  if [[ ! -d "${adapter_dir}/.git" ]]; then
    if [[ "${CLONE_MISSING}" != "1" ]]; then
      echo "Missing ${adapter_dir}; set CLONE_MISSING=1 to clone it."
      exit 1
    fi

    echo "Cloning ${adapter} into ${adapter_dir}"
    git clone "${ADAPTER_REMOTE_BASE}/${adapter}.git" "${adapter_dir}"
  fi

  echo "Installing ${adapter} from ${adapter_dir}"
  "${PYTHON_BIN}" -m pip install -e "${adapter_dir}" --group dev
done

echo "Installing umbrella package from ${REPO_ROOT}"
"${PYTHON_BIN}" -m pip install -e "${REPO_ROOT}" --group dev
