# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates
# SPDX-License-Identifier: Apache-2.0
"""SBOM downloads must not expose tokens or escape the output directory."""

import importlib.util
import unittest
from pathlib import Path
from urllib.request import Request

import pytest

_ASSERT = unittest.TestCase()
SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts/download-adapter-sboms.py"
)
SPEC = importlib.util.spec_from_file_location("sbom_downloader", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load SBOM download script")
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://github.com/asset",
        "ftp://github.com/asset",
        "https://example.com/asset",
        "https://github.com.example.com/asset",
        "https://github.com@evil.example/asset",
        "https://user@github.com/asset",
        "https://github.com:444/asset",
    ],
)
def test_reject_untrusted_urls(url):
    with pytest.raises(ValueError):
        downloader.github_request(url, "test-token", {})
    request = Request("https://github.com/asset")
    with pytest.raises(ValueError):
        downloader.GitHubRedirectHandler().redirect_request(
            request, None, 302, "Found", {}, url
        )


def test_cross_host_redirect_removes_authorization():
    request = downloader.github_request(
        "https://github.com/asset", "test-token", {}
    )
    redirected = downloader.GitHubRedirectHandler().redirect_request(
        request,
        None,
        302,
        "Found",
        {},
        "https://release-assets.githubusercontent.com/asset?signature=example",
    )
    _ASSERT.assertIsNone(redirected.get_header("Authorization"))
    _ASSERT.assertEqual(
        redirected.full_url,
        "https://release-assets.githubusercontent.com/asset?signature=example",
    )


def test_same_host_redirect_keeps_authorization():
    request = downloader.github_request(
        "https://api.github.com/asset", "test-token", {}
    )
    redirected = downloader.GitHubRedirectHandler().redirect_request(
        request, None, 302, "Found", {}, "https://api.github.com/next"
    )
    _ASSERT.assertEqual(
        redirected.get_header("Authorization"), "Bearer test-token"
    )


def test_asset_host_does_not_receive_token():
    request = downloader.github_request(
        "https://objects.githubusercontent.com/asset", "test-token", {}
    )
    _ASSERT.assertIsNone(request.get_header("Authorization"))


@pytest.mark.parametrize(
    "name",
    [
        "../outside.cdx.json",
        "/outside.cdx.json",
        "..\\outside.cdx.json",
        "C:outside.cdx.json",
        "bad\x00.cdx.json",
    ],
)
def test_reject_unsafe_asset_names(monkeypatch, tmp_path, name):
    monkeypatch.setattr(
        downloader,
        "github_json",
        lambda *_: {
            "assets": [
                {
                    "name": name,
                    "browser_download_url": "https://github.com/asset",
                }
            ]
        },
    )
    with pytest.raises(ValueError, match="plain filename"):
        downloader.download_adapter_sboms(
            {"pte-adapter-model-explorer": "0.2.0"}, tmp_path, None
        )


def test_download_keeps_expected_output_location(monkeypatch, tmp_path):
    monkeypatch.setattr(
        downloader,
        "github_json",
        lambda *_: {
            "assets": [
                {
                    "name": "wheel.cdx.json",
                    "browser_download_url": "https://github.com/asset",
                }
            ]
        },
    )
    written = []
    monkeypatch.setattr(
        downloader, "download_file", lambda u, p, t: written.append((u, p, t))
    )
    manifest = downloader.download_adapter_sboms(
        {"pte-adapter-model-explorer": "0.2.0"}, tmp_path, None
    )
    output = tmp_path / "pte-adapter-model-explorer/wheel.cdx.json"
    _ASSERT.assertEqual(written, [("https://github.com/asset", output, None)])
    _ASSERT.assertEqual(
        manifest, {"pte-adapter-model-explorer==0.2.0": [str(output)]}
    )
