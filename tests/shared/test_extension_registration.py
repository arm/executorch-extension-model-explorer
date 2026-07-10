# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

from executorch_extension_model_explorer import main as extension


def test_extension_module_exports_all_extension_components() -> None:
    pte_metadata = extension.PTEAdapter.metadata
    assert not isinstance(pte_metadata, list)
    assert pte_metadata.id == "pte_adapter_model_explorer"
    assert pte_metadata.name == "PTE Adapter"
    assert pte_metadata.fileExts == ["pte"]

    etrecord_metadata = extension.ETRecordAdapter.metadata
    assert not isinstance(etrecord_metadata, list)
    assert etrecord_metadata.id == "etrecord_adapter"
    assert etrecord_metadata.name == "ETRecord Adapter"
    assert etrecord_metadata.fileExts == ["etrecord"]

    etdump_metadata = extension.ETDumpProfilingOverlayProvider.metadata
    assert not isinstance(etdump_metadata, list)
    assert etdump_metadata.id == "etdump_data_provider"
    assert etdump_metadata.name == "ETDump Profiling Overlay"
    assert etdump_metadata.filter is not None
    assert etdump_metadata.filter.adapterIds == ["etrecord_adapter"]
