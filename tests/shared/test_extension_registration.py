# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

import unittest

from executorch_extension_model_explorer import main as extension

_ASSERT = unittest.TestCase()


def test_extension_module_exports_all_extension_components() -> None:
    pte_metadata = extension.PTEAdapter.metadata
    if isinstance(pte_metadata, list):
        raise AssertionError("Expected one PTE metadata object")
    _ASSERT.assertEqual(pte_metadata.id, "pte_adapter_model_explorer")
    _ASSERT.assertEqual(pte_metadata.name, "PTE Adapter")
    _ASSERT.assertEqual(pte_metadata.fileExts, ["pte"])

    etrecord_metadata = extension.ETRecordAdapter.metadata
    if isinstance(etrecord_metadata, list):
        raise AssertionError("Expected one ETRecord metadata object")
    _ASSERT.assertEqual(etrecord_metadata.id, "etrecord_adapter")
    _ASSERT.assertEqual(etrecord_metadata.name, "ETRecord Adapter")
    _ASSERT.assertIn("etrecord", etrecord_metadata.fileExts)

    etdump_metadata = extension.ETDumpProfilingOverlayProvider.metadata
    if isinstance(etdump_metadata, list):
        raise AssertionError("Expected one ETDump metadata object")
    _ASSERT.assertEqual(etdump_metadata.id, "etdump_data_provider")
    _ASSERT.assertEqual(etdump_metadata.name, "ETDump Profiling Overlay")
    if etdump_metadata.filter is None:
        raise AssertionError("Expected ETDump adapter filter")
    _ASSERT.assertEqual(
        etdump_metadata.filter.adapterIds, ["etrecord_adapter"]
    )
