#!/bin/bash
set -e

# Non-interactive configuration
export DEBIAN_FRONTEND=noninteractive

# Detect OS
. /etc/os-release
OS=$ID
CODENAME=$VERSION_CODENAME

if command -v docker >/dev/null 2>&1; then
    echo "[~] Docker already installed, skipping to permissions check."
else
    echo "[*] Installing Docker for $OS $CODENAME (Non-Interactive)..."

    # Install dependencies
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg

    # Add GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Repo
    ARCH=$(dpkg --print-architecture)
    echo "deb [arch=$ARCH signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS $CODENAME stable" > /etc/apt/sources.list.d/docker.list

    # Install
    apt-get update -qq
    apt-get install -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
        docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Permissions
if ! groups john | grep -q "\bdocker\b"; then
    echo "[*] Adding user 'john' to docker group..."
    usermod -aG docker john
fi

echo "[+] Docker Installation/Check Complete."
