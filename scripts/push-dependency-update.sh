#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

dependency="$1"
version="$2"

for attempt in 1 2 3; do
  python scripts/update-dependency-pin.py "$dependency" "$version"
  git add -- pyproject.toml
  if git diff --cached --quiet; then
    echo "No dependency update required."
    exit 0
  fi
  base=$(git rev-parse HEAD)
  git commit -m "fix(deps): update $dependency to $version"
  if git push origin HEAD:main; then
    exit 0
  fi

  git fetch origin main
  if [[ "$attempt" == 3 || "$(git rev-parse origin/main)" == "$base" ]]; then
    echo "Unable to push dependency update to main; check the push error above." >&2
    exit 1
  fi
  # Another release updated main. Reapply on its latest version, never force-push.
  git switch --detach origin/main
done
