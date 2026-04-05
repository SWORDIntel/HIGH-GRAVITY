#!/usr/bin/env python3
"""
NPU Bridge Release Management and Distribution System
Automated release pipeline with version management and binary distribution
"""

import hashlib
import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import semver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReleaseAsset:
    """Release asset metadata"""

    name: str
    download_url: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    target_platform: str
    features: List[str]


@dataclass
class ReleaseInfo:
    """Complete release information"""

    version: str
    tag_name: str
    name: str
    body: str
    draft: bool
    prerelease: bool
    created_at: str
    published_at: str
    assets: List[ReleaseAsset]
    download_count: int


class NPUReleaseManager:
    """
    NPU Bridge Release Management System
    Handles versioning, releases, and binary distribution
    """

    def __init__(
        self,
        repo_owner: str = "SWORDIntel",
        repo_name: str = "claude-backups",
        github_token: Optional[str] = None,
    ):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")

        self.api_base = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "NPU-Bridge-Release-Manager/1.0",
        }

        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"

    def get_latest_release(self) -> Optional[ReleaseInfo]:
        """Get latest release information"""
        try:
            response = requests.get(
                f"{self.api_base}/releases/latest", headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                return self._parse_release_data(data)
            else:
                logger.warning(
                    f"Failed to fetch latest release: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"Error fetching latest release: {e}")
            return None

    def get_all_releases(self, limit: int = 10) -> List[ReleaseInfo]:
        """Get all releases (up to limit)"""
        try:
            response = requests.get(
                f"{self.api_base}/releases",
                headers=self.headers,
                params={"per_page": limit},
            )
            if response.status_code == 200:
                releases = []
                for data in response.json():
                    releases.append(self._parse_release_data(data))
                return releases
            else:
                logger.warning(f"Failed to fetch releases: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching releases: {e}")
            return []

    def get_release_by_version(self, version: str) -> Optional[ReleaseInfo]:
        """Get specific release by version tag"""
        try:
            tag_name = version if version.startswith("v") else f"v{version}"
            response = requests.get(
                f"{self.api_base}/releases/tags/{tag_name}", headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                return self._parse_release_data(data)
            else:
                logger.warning(f"Release {version} not found: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching release {version}: {e}")
            return None

    def _parse_release_data(self, data: Dict[str, Any]) -> ReleaseInfo:
        """Parse GitHub release data into ReleaseInfo"""
        assets = []
        for asset_data in data.get("assets", []):
            # Extract platform and features from asset name
            asset_name = asset_data["name"]
            target_platform = self._extract_platform_from_name(asset_name)
            features = self._extract_features_from_name(asset_name)

            assets.append(
                ReleaseAsset(
                    name=asset_name,
                    download_url=asset_data["browser_download_url"],
                    size_bytes=asset_data["size"],
                    content_type=asset_data["content_type"],
                    checksum_sha256="",  # Will be calculated if needed
                    target_platform=target_platform,
                    features=features,
                )
            )

        return ReleaseInfo(
            version=data["tag_name"],
            tag_name=data["tag_name"],
            name=data["name"],
            body=data["body"],
            draft=data["draft"],
            prerelease=data["prerelease"],
            created_at=data["created_at"],
            published_at=data["published_at"],
            assets=assets,
            download_count=sum(
                asset["download_count"] for asset in data.get("assets", [])
            ),
        )

    def _extract_platform_from_name(self, asset_name: str) -> str:
        """Extract target platform from asset name"""
        if "x86_64-unknown-linux-gnu" in asset_name:
            return "x86_64-unknown-linux-gnu"
        elif "x86_64-unknown-linux-musl" in asset_name:
            return "x86_64-unknown-linux-musl"
        elif "x86_64-pc-windows-msvc" in asset_name:
            return "x86_64-pc-windows-msvc"
        elif "x86_64-apple-darwin" in asset_name:
            return "x86_64-apple-darwin"
        else:
            return "unknown"

    def _extract_features_from_name(self, asset_name: str) -> List[str]:
        """Extract features from asset name"""
        features = []

        feature_patterns = {
            "avx512": ["avx512", "meteor-lake"],
            "avx2": ["avx2", "fma"],
            "static": ["static"],
            "intel-npu": ["intel-npu"],
        }

        for pattern, feature_list in feature_patterns.items():
            if pattern in asset_name:
                features.extend(feature_list)

        return features

    def find_best_asset_for_platform(
        self, release: ReleaseInfo, target_platform: str = None
    ) -> Optional[ReleaseAsset]:
        """Find best asset for target platform"""
        if target_platform is None:
            # Auto-detect platform
            target_platform = self._detect_current_platform()

        # Filter assets by platform
        compatible_assets = [
            asset
            for asset in release.assets
            if asset.target_platform == target_platform
        ]

        if not compatible_assets:
            logger.warning(f"No assets found for platform: {target_platform}")
            return None

        # Rank assets by optimization level (prefer more optimized)
        def optimization_score(asset: ReleaseAsset) -> int:
            score = 0
            if "avx512" in asset.features:
                score += 30
            elif "avx2" in asset.features:
                score += 20
            if "intel-npu" in asset.features:
                score += 10
            if "meteor-lake" in asset.features:
                score += 5
            return score

        best_asset = max(compatible_assets, key=optimization_score)
        logger.info(
            f"Selected asset: {best_asset.name} (score: {optimization_score(best_asset)})"
        )

        return best_asset

    def _detect_current_platform(self) -> str:
        """Detect current platform for asset selection"""
        import platform

        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "linux":
            # Check if musl or glibc
            try:
                with open("/etc/os-release", "r") as f:
                    os_info = f.read()
                if "alpine" in os_info.lower():
                    return "x86_64-unknown-linux-musl"
            except FileNotFoundError:
                pass
            return "x86_64-unknown-linux-gnu"
        elif system == "windows":
            return "x86_64-pc-windows-msvc"
        elif system == "darwin":
            return "x86_64-apple-darwin"
        else:
            return "unknown"

    def download_asset(
        self, asset: ReleaseAsset, output_path: str, verify_checksum: bool = True
    ) -> bool:
        """Download release asset with progress and verification"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Downloading {asset.name} ({asset.size_bytes / 1024 / 1024:.1f} MB)"
        )

        try:
            response = requests.get(
                asset.download_url, stream=True, headers=self.headers
            )
            response.raise_for_status()

            downloaded = 0
            chunk_size = 8192
            start_time = time.time()

            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress indicator
                        if downloaded % (1024 * 1024) == 0:  # Every 1MB
                            elapsed = time.time() - start_time
                            speed = (
                                downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
                            )
                            progress = (
                                (downloaded / asset.size_bytes) * 100
                                if asset.size_bytes > 0
                                else 0
                            )
                            logger.info(f"Progress: {progress:.1f}% ({speed:.1f} MB/s)")

            elapsed = time.time() - start_time
            speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0
            logger.info(f"Download completed: {speed:.1f} MB/s")

            # Verify file size
            actual_size = output_file.stat().st_size
            if actual_size != asset.size_bytes:
                logger.error(
                    f"Size mismatch: expected {asset.size_bytes}, got {actual_size}"
                )
                return False

            # Verify checksum if provided
            if verify_checksum and asset.checksum_sha256:
                if not self._verify_checksum(output_file, asset.checksum_sha256):
                    logger.error("Checksum verification failed")
                    return False

            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def _verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify file checksum"""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        actual_sha256 = hasher.hexdigest()
        return actual_sha256.lower() == expected_sha256.lower()

    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics across all releases"""
        releases = self.get_all_releases(limit=50)

        stats = {
            "total_releases": len(releases),
            "total_downloads": sum(r.download_count for r in releases),
            "latest_version": releases[0].version if releases else None,
            "platforms": {},
            "features": {},
            "release_timeline": [],
        }

        for release in releases:
            stats["release_timeline"].append(
                {
                    "version": release.version,
                    "published_at": release.published_at,
                    "download_count": release.download_count,
                    "asset_count": len(release.assets),
                }
            )

            for asset in release.assets:
                # Platform stats
                platform = asset.target_platform
                if platform not in stats["platforms"]:
                    stats["platforms"][platform] = {"count": 0, "total_size": 0}
                stats["platforms"][platform]["count"] += 1
                stats["platforms"][platform]["total_size"] += asset.size_bytes

                # Feature stats
                for feature in asset.features:
                    if feature not in stats["features"]:
                        stats["features"][feature] = 0
                    stats["features"][feature] += 1

        return stats

    def create_install_script(self, output_path: str) -> None:
        """Create universal installation script"""
        script_content = (
            '''#!/bin/bash
set -euo pipefail

# NPU Bridge Universal Installer
# Generated by NPU Release Manager

REPO_OWNER="'''
            + self.repo_owner
            + '''"
REPO_NAME="'''
            + self.repo_name
            + """"
VERSION="${NPU_BRIDGE_VERSION:-latest}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log() { echo -e "${BLUE}[NPU-BRIDGE]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Detect platform
detect_platform() {
    local os_type=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)

    case "$os_type" in
        linux)
            if [[ -f /etc/alpine-release ]]; then
                echo "x86_64-unknown-linux-musl"
            else
                echo "x86_64-unknown-linux-gnu"
            fi
            ;;
        darwin)
            echo "x86_64-apple-darwin"
            ;;
        msys*|mingw*|cygwin*)
            echo "x86_64-pc-windows-msvc"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Get latest release
get_latest_release() {
    local api_url="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest"
    local headers=""

    if [[ -n "$GITHUB_TOKEN" ]]; then
        headers="-H \"Authorization: token $GITHUB_TOKEN\""
    fi

    curl -sSL $headers "$api_url" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\\1/'
}

# Find best asset for platform
find_best_asset() {
    local version="$1"
    local platform="$2"
    local api_url="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/tags/${version}"
    local headers=""

    if [[ -n "$GITHUB_TOKEN" ]]; then
        headers="-H \"Authorization: token $GITHUB_TOKEN\""
    fi

    # Get release data and find best matching asset
    local release_data=$(curl -sSL $headers "$api_url")

    # Look for platform-specific asset with best optimization
    local asset_url=""
    local asset_name=""

    # Priority order: avx512 > avx2 > basic
    for optimization in "avx512" "avx2" ""; do
        asset_name=$(echo "$release_data" | jq -r ".assets[] | select(.name | contains(\\"$platform\\") and contains(\\"$optimization\\")) | .name" | head -1)
        if [[ -n "$asset_name" && "$asset_name" != "null" ]]; then
            asset_url=$(echo "$release_data" | jq -r ".assets[] | select(.name == \\"$asset_name\\") | .browser_download_url")
            break
        fi
    done

    if [[ -n "$asset_url" && "$asset_url" != "null" ]]; then
        echo "$asset_url|$asset_name"
    else
        error "No compatible asset found for platform: $platform"
    fi
}

# Download and install
install_npu_bridge() {
    local platform=$(detect_platform)
    log "Detected platform: $platform"

    local version="$VERSION"
    if [[ "$version" == "latest" ]]; then
        version=$(get_latest_release)
        log "Latest version: $version"
    fi

    local asset_info=$(find_best_asset "$version" "$platform")
    local asset_url=$(echo "$asset_info" | cut -d'|' -f1)
    local asset_name=$(echo "$asset_info" | cut -d'|' -f2)

    log "Downloading: $asset_name"
    log "URL: $asset_url"

    # Create temporary directory
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    # Download with retry
    local max_attempts=3
    for attempt in $(seq 1 $max_attempts); do
        log "Download attempt $attempt/$max_attempts"
        if curl -sSL -f "$asset_url" -o "$temp_dir/package.tar.gz"; then
            break
        elif [[ $attempt -eq $max_attempts ]]; then
            error "Download failed after $max_attempts attempts"
        else
            warn "Download failed, retrying in 2 seconds..."
            sleep 2
        fi
    done

    # Extract and install
    log "Extracting package..."
    cd "$temp_dir"
    tar -xzf package.tar.gz

    local extracted_dir=$(find . -maxdepth 1 -type d -name "npu-coordination-bridge-*" | head -1)
    if [[ -z "$extracted_dir" ]]; then
        error "No extracted directory found"
    fi

    cd "$extracted_dir"

    log "Installing to $INSTALL_DIR..."
    if [[ $EUID -eq 0 ]]; then
        ./install.sh "$INSTALL_DIR"
    else
        sudo ./install.sh "$INSTALL_DIR"
    fi

    success "NPU Bridge installed successfully!"

    # Verify installation
    if command -v npu-bridge-server >/dev/null 2>&1; then
        log "Verifying installation..."
        npu-bridge-server --version || true
    fi
}

# Main
main() {
    log "NPU Bridge Universal Installer"
    log "Repository: ${REPO_OWNER}/${REPO_NAME}"
    log "Version: $VERSION"
    log "Install directory: $INSTALL_DIR"

    # Check dependencies
    for cmd in curl tar jq; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error "Required command not found: $cmd"
        fi
    done

    install_npu_bridge

    success "Installation complete! 🚀"
    log "Run 'npu-bridge-server --help' to get started"
}

main "$@"
"""
        )

        with open(output_path, "w") as f:
            f.write(script_content)

        os.chmod(output_path, 0o755)
        logger.info(f"Install script created: {output_path}")

    def generate_release_matrix(self) -> Dict[str, Any]:
        """Generate build matrix for CI/CD"""
        matrix = {
            "targets": [
                {
                    "name": "Intel Meteor Lake (AVX-512 + NPU)",
                    "target": "x86_64-unknown-linux-gnu",
                    "features": "intel-npu,avx512,meteor-lake",
                    "cpu_features": "-C target-cpu=skylake-avx512 -C target-feature=+avx512f,+avx512dq",
                    "description": "Optimized for Intel Core Ultra (Meteor Lake) with NPU",
                },
                {
                    "name": "Intel Haswell+ (AVX2/FMA)",
                    "target": "x86_64-unknown-linux-gnu",
                    "features": "intel-npu,avx2,fma",
                    "cpu_features": "-C target-cpu=haswell -C target-feature=+avx2,+fma",
                    "description": "Optimized for Intel Haswell+ processors with AVX2",
                },
                {
                    "name": "Portable Linux (Static)",
                    "target": "x86_64-unknown-linux-musl",
                    "features": "intel-npu,static",
                    "cpu_features": "-C target-cpu=x86-64-v2",
                    "description": "Portable static build for broad Linux compatibility",
                },
            ],
            "rust_version": "stable",
            "optimization_level": "3",
            "lto": "fat",
            "codegen_units": "1",
        }

        return matrix


def main():
    """Command-line interface for release management"""
    import argparse

    parser = argparse.ArgumentParser(
        description="NPU Bridge Release Management and Distribution"
    )
    parser.add_argument(
        "--list-releases", action="store_true", help="List all releases"
    )
    parser.add_argument(
        "--latest", action="store_true", help="Show latest release info"
    )
    parser.add_argument("--version", help="Get specific version info")
    parser.add_argument(
        "--download",
        metavar="OUTPUT_PATH",
        help="Download best asset for current platform",
    )
    parser.add_argument(
        "--platform", help="Target platform for download (auto-detect if not specified)"
    )
    parser.add_argument("--stats", action="store_true", help="Show download statistics")
    parser.add_argument(
        "--create-installer",
        metavar="OUTPUT_PATH",
        help="Create universal installation script",
    )
    parser.add_argument(
        "--build-matrix", action="store_true", help="Generate CI/CD build matrix"
    )
    parser.add_argument(
        "--repo",
        default="SWORDIntel/claude-backups",
        help="GitHub repository (owner/name)",
    )
    parser.add_argument("--token", help="GitHub token for API access")

    args = parser.parse_args()

    # Parse repository
    if "/" in args.repo:
        repo_owner, repo_name = args.repo.split("/", 1)
    else:
        repo_owner, repo_name = "SWORDIntel", args.repo

    manager = NPUReleaseManager(repo_owner, repo_name, args.token)

    if args.list_releases:
        releases = manager.get_all_releases()
        print(f"📦 Found {len(releases)} releases:")
        for release in releases:
            status = "📋 Draft" if release.draft else "🚀 Published"
            prerelease = " (Pre-release)" if release.prerelease else ""
            print(
                f"   {status} {release.version}{prerelease} - {release.download_count} downloads"
            )

    elif args.latest:
        release = manager.get_latest_release()
        if release:
            print(f"📦 Latest Release: {release.version}")
            print(f"   Published: {release.published_at}")
            print(f"   Downloads: {release.download_count}")
            print(f"   Assets: {len(release.assets)}")
            for asset in release.assets:
                print(f"     - {asset.name} ({asset.target_platform})")
        else:
            print("❌ No releases found")

    elif args.version:
        release = manager.get_release_by_version(args.version)
        if release:
            print(f"📦 Release {release.version}:")
            print(f"   Name: {release.name}")
            print(f"   Published: {release.published_at}")
            print(f"   Downloads: {release.download_count}")
            print(f"   Assets:")
            for asset in release.assets:
                features_str = ", ".join(asset.features) if asset.features else "basic"
                print(f"     - {asset.name}")
                print(f"       Platform: {asset.target_platform}")
                print(f"       Features: {features_str}")
                print(f"       Size: {asset.size_bytes / 1024 / 1024:.1f} MB")
        else:
            print(f"❌ Release {args.version} not found")

    elif args.download:
        release = (
            manager.get_latest_release()
            if not args.version
            else manager.get_release_by_version(args.version)
        )
        if release:
            asset = manager.find_best_asset_for_platform(release, args.platform)
            if asset:
                success = manager.download_asset(asset, args.download)
                if success:
                    print(f"✅ Downloaded: {args.download}")
                else:
                    print("❌ Download failed")
            else:
                print("❌ No compatible asset found")
        else:
            print("❌ Release not found")

    elif args.stats:
        stats = manager.get_download_stats()
        print(f"📊 Download Statistics:")
        print(f"   Total Releases: {stats['total_releases']}")
        print(f"   Total Downloads: {stats['total_downloads']}")
        print(f"   Latest Version: {stats['latest_version']}")
        print(f"   Platforms:")
        for platform, data in stats["platforms"].items():
            print(
                f"     - {platform}: {data['count']} assets, {data['total_size'] / 1024 / 1024:.1f} MB total"
            )
        print(f"   Features:")
        for feature, count in stats["features"].items():
            print(f"     - {feature}: {count} assets")

    elif args.create_installer:
        manager.create_install_script(args.create_installer)
        print(f"✅ Install script created: {args.create_installer}")

    elif args.build_matrix:
        matrix = manager.generate_release_matrix()
        print("🔧 Build Matrix (JSON):")
        print(json.dumps(matrix, indent=2))

    else:
        # Default: show latest release
        release = manager.get_latest_release()
        if release:
            print(f"📦 Latest Release: {release.version}")
            print(f"   Downloads: {release.download_count}")
            print(f"   Assets: {len(release.assets)}")
        else:
            print("❌ No releases found")


if __name__ == "__main__":
    main()
