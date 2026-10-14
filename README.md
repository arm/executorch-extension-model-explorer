<!---
SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
SPDX-License-Identifier: Apache-2.0
--->

# ExecuTorch Extension Model Explorer

ExecuTorch Extension Model Explorer is a combined extension package for
[Model Explorer](https://github.com/google-ai-edge/model-explorer). It registers
adapters and data providers for inspecting ExecuTorch model artifacts and
profiling data in one package:

- [`PTEAdapter`](https://github.com/arm/pte-adapter-model-explorer)
  visualizes `.pte` model files.
- [`ETRecordAdapter`](https://github.com/arm/etrecord-adapter-model-explorer)
  visualizes `.etrecord` graph files.
- [`ETDumpProfilingOverlayProvider`](https://github.com/arm/etdump-data-provider-model-explorer)
  overlays runtime profiling data from `.etdp` or `.etdump` files onto ETRecord
  graphs.

## Supported File Types

| File type | Component | Purpose |
| --- | --- | --- |
| `.pte` | PTE Adapter | Visualize ExecuTorch program files. |
| `.etrecord` | ETRecord Adapter | Visualize exported ExecuTorch graph structure and metadata. |
| `.etdp`, `.etdump` | ETDump Profiling Overlay | Add per-node runtime latency data to ETRecord graphs. |

## Requirements

- Python >=3.10, <3.13
- Model Explorer, provided by `ai-edge-model-explorer`
- ExecuTorch Python packages for ETRecord and ETDump workflows
- PTE delegate support packages installed through the PTE adapter:
  `vgf-adapter-model-explorer`, `tosa-adapter-model-explorer`, and
  `flatbuffers`

The umbrella depends directly on PTE, ETRecord and ETDump only. Those packages
declare and install their own Model Explorer, ExecuTorch and delegate
requirements; the umbrella does not duplicate those version constraints.

## Installation

For local development from this repository:

```bash
scripts/install-editable.sh
```

Install the published package from PyPI:

```bash
pip install executorch-extension-model-explorer
```

## Usage

Launch Model Explorer with this combined extension package enabled:

```bash
model-explorer --extensions=executorch_extension_model_explorer
```

To load individual adapters or providers, pass the extension names directly:

```bash
model-explorer --extensions=pte_adapter_model_explorer
model-explorer --extensions=etrecord_adapter_model_explorer
model-explorer --extensions=etrecord_adapter_model_explorer,etdump_data_provider_model_explorer
```

### PTE Adapter

Open a `.pte` file in Model Explorer to inspect the ExecuTorch program. The PTE
adapter includes delegate support for Arm Ethos-U, Arm VGF, and XNNPACK. See the
[PTE adapter documentation](https://github.com/arm/pte-adapter-model-explorer)
for details and schema regeneration notes.

### ETRecord Adapter

Open an `.etrecord` file in Model Explorer to inspect exported ExecuTorch graph
structure, metadata, connections, inputs, and outputs. See the
[ETRecord adapter documentation](https://github.com/arm/etrecord-adapter-model-explorer)
for details.

### ETDump Data Provider

After opening an `.etrecord` graph, click `Add per-node data`, select
`ETDump Profiling Overlay`, upload an `.etdp` or `.etdump` file, and run the
provider. The overlay maps runtime latency metrics onto matching ETRecord graph
nodes. See the
[ETDump data provider documentation](https://github.com/arm/etdump-data-provider-model-explorer)
for details and mock artifact tooling.

## Development

Install the package in editable mode, then run the test suite with pytest:

```bash
scripts/install-editable.sh
scripts/test-all.sh
```

For coordinated development across all leaf repos, keep the adapter repositories
as sibling checkouts and install them in editable mode before the umbrella
package:

```bash
scripts/install-local-adapters.sh
```

The umbrella wheel uses the package versions pinned in `pyproject.toml`.
Local adapter checkouts are for multi-repo development and adapter-specific
testing; they are not the release pin.

Run adapter-specific tests from each adapter repository root so their local
fixtures and pytest configuration are resolved correctly.

Development dependency groups are declared in `pyproject.toml` for test,
coverage, lint, type-checking, and build tools.

### CI

Pull requests and pushes to `main` run the aggregate CI workflow. It
installs this package in editable mode, then runs Ruff, Pyright, and the
aggregate pytest suite. The workflow also builds a wheel after tests pass.

Internal pushes to `main` publish development builds to Artifactory. Internal
release tags publish release builds there for testing. Tags are not
automatically copied to the public repository.

Use the `Trigger Release` workflow to cut a release from the private repository.
It calculates the next version with git-cliff, updates `pyproject.toml`, pushes
the version bump commit, and pushes the internal release tag. After testing,
run `Sync release tag to public repo` with that tag. The public tag triggers
PyPI publication and a GitHub release. Main commits still sync automatically.

### Dependency update policy

This repository declares adapter/provider minimum versions in `pyproject.toml`.
PTE, ETRecord and ETDump notify it after successful internal tagged releases to
Artifactory, not after main development builds or public releases.

After installing the development dependencies, use the helper script for local
dependency lower-bound updates:

```bash
python scripts/update-dependency-pin.py etrecord-adapter-model-explorer v0.2.0
```

The same update can be automated through the `Update dependency lower bound` workflow.
Leaf release workflows can trigger it with a `repository_dispatch` event named
`update-dependency` and a payload containing `dependency` or `name`, plus
`version` or `tag`. The workflow also accepts the old `update-submodule`
dispatch name for compatibility, but it now updates `pyproject.toml`.
Stable versions and package prereleases such as `v0.5.1rc1` are accepted.
Updates preserve other constraints
and never lower an existing minimum. Each update opens a PR for normal CI and
review; it does not merge or publish the umbrella automatically.

## Trademark Notice

This project uses some of the Arm product, service, or technology trademarks,
as listed in the [Trademark List](https://www.arm.com/company/policies/trademarks/arm-trademark-list),
in accordance with the Arm [Trademark Use Guidelines](https://www.arm.com/company/policies/trademarks/guidelines-trademarks).

Subsequent uses of these trademarks throughout this repository do not need to
be prefixed with the Arm word trademark.

## Contributions

We are not accepting direct contributions at this time. If you have feedback or
feature requests, please use the repository issues section.
