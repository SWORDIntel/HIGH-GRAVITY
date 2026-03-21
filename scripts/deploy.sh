#!/usr/bin/env bash

# HIGHGRAVITY Deployment Script
# This script sets up the environment and dependencies for HIGHGRAVITY.

set -e

echo "[*] Setting up HIGHGRAVITY..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 is required but not installed. Aborting."
    exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "[!] pip3 is required but not installed. Aborting."
    exit 1
fi

echo "[*] Installing Python dependencies..."
pip3 install -r requirements.txt 2>/dev/null || pip3 install requests rich

echo "[*] Ensuring scripts are executable..."
chmod +x launcher.py
chmod +x scripts/proxy.py

echo "[+] Deployment setup complete."
echo "    You can now run the dashboard and proxy with:"
echo "    ./launcher.py --dashboard --start-proxy"
