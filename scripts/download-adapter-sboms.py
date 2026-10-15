#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

"""Download SBOM release assets for adapter dependency lower bounds."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ADAPTER_REPOSITORIES = {
    "pte-adapter-model-explorer": "arm/pte-adapter-model-explorer",
    "etrecord-adapter-model-explorer": "arm/etrecord-adapter-model-explorer",
    "etdump-data-provider-model-explorer": (
        "arm/etdump-data-provider-model-explorer"
    ),
}

SBOM_ASSET_SUFFIXES = (".spdx.json", ".cdx.json")
GITHUB_DOWNLOAD_HOSTS = {
    "api.github.com",
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}


def validate_github_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in GITHUB_DOWNLOAD_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("SBOM downloads require a trusted GitHub HTTPS URL")
    return url


class GitHubRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_github_url(newurl)
        redirected = super().redirect_request(
            req, fp, code, msg, headers, newurl
        )
        if redirected is not None and (
            urlsplit(req.full_url).hostname != urlsplit(newurl).hostname
        ):
            redirected.remove_header("Authorization")
        return redirected


def github_request(url: str, token: str | None, headers: dict[str, str]):
    validate_github_url(url)
    if token and urlsplit(url).hostname in {"api.github.com", "github.com"}:
        headers = {**headers, "Authorization": f"Bearer {token}"}
    return Request(url, headers=headers)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download adapter SBOM assets for dependency lower bounds in "
            "pyproject.toml."
        )
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to the umbrella package pyproject.toml.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("sbom/dependencies"),
        help="Directory to write downloaded adapter SBOMs.",
    )
    parser.add_argument(
        "--github-token",
        default=None,
        help="Optional GitHub token for release asset downloads.",
    )
    return parser.parse_args()


def pinned_adapter_versions(pyproject: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    dependency_pattern = re.compile(
        r'^\s*"(?P<name>[A-Za-z0-9_.-]+)>=(?P<version>[^"]+)",?\s*$'
    )

    in_dependencies = False
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.strip() == "dependencies = [":
            in_dependencies = True
            continue
        if in_dependencies and line.strip() == "]":
            break
        if not in_dependencies:
            continue

        match = dependency_pattern.match(line)
        if not match:
            continue
        name = match.group("name")
        if name in ADAPTER_REPOSITORIES:
            versions[name] = match.group("version")

    missing = sorted(set(ADAPTER_REPOSITORIES) - set(versions))
    if missing:
        raise RuntimeError(
            "Missing adapter dependency lower bounds in pyproject.toml: "
            + ", ".join(missing)
        )
    return versions


def github_json(url: str, token: str | None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    request = github_request(url, token, headers)
    with build_opener(GitHubRedirectHandler()).open(
        request, timeout=30
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, output: Path, token: str | None) -> None:
    headers = {"Accept": "application/octet-stream"}
    request = github_request(url, token, headers)
    with build_opener(GitHubRedirectHandler()).open(
        request, timeout=60
    ) as response:
        output.write_bytes(response.read())


def download_adapter_sboms(
    versions: dict[str, str],
    output_dir: Path,
    token: str | None,
) -> dict[str, list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[str]] = {}

    for package_name, version in sorted(versions.items()):
        repo = ADAPTER_REPOSITORIES[package_name]
        release_url = (
            f"https://api.github.com/repos/{repo}/releases/tags/v{version}"
        )
        release = github_json(release_url, token)
        if not isinstance(release, dict):
            raise RuntimeError(
                f"Unexpected release response for {repo} v{version}"
            )

        assets = release.get("assets", [])
        if not isinstance(assets, list):
            raise RuntimeError(
                f"Unexpected assets response for {repo} v{version}"
            )

        sbom_assets = [
            asset
            for asset in assets
            if isinstance(asset, dict)
            and str(asset.get("name", "")).endswith(SBOM_ASSET_SUFFIXES)
        ]
        if not sbom_assets:
            raise RuntimeError(
                f"No JSON SBOM assets found for {repo} v{version}"
            )

        downloaded: list[str] = []
        package_output_dir = output_dir / package_name
        package_output_dir.mkdir(parents=True, exist_ok=True)
        for asset in sbom_assets:
            asset_name = str(asset["name"])
            if (
                "/" in asset_name
                or "\\" in asset_name
                or ":" in asset_name
                or "\x00" in asset_name
                or asset_name in {".", ".."}
            ):
                raise ValueError("SBOM asset name must be a plain filename")
            browser_download_url = str(asset["browser_download_url"])
            output = package_output_dir / asset_name
            download_file(browser_download_url, output, token)
            downloaded.append(str(output))
            print(f"Downloaded {repo} v{version} SBOM: {output}")

        manifest[f"{package_name}=={version}"] = downloaded

    return manifest


def main() -> None:
    args = parse_args()
    try:
        versions = pinned_adapter_versions(args.pyproject)
        manifest = download_adapter_sboms(
            versions,
            args.output_dir,
            args.github_token,
        )
    except (HTTPError, URLError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    manifest_path = args.output_dir / "adapter-sbom-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote adapter SBOM manifest: {manifest_path}")


if __name__ == "__main__":
    main()
