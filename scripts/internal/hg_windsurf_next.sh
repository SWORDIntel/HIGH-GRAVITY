#!/usr/bin/env bash
set -euo pipefail

export NODE_EXTRA_CA_CERTS="${NODE_EXTRA_CA_CERTS:-/home/john/HIGH-GRAVITY/certs/proxy.ca.crt}"
export HG_PROXY_URL="${HG_PROXY_URL:-https://proxy.windsurf.com}"
export HG_PROXY_MODE="${HG_PROXY_MODE:-full}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export SSL_CERT_DIR="${SSL_CERT_DIR:-/etc/ssl/certs}"
export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export GIT_SSL_CAINFO="${GIT_SSL_CAINFO:-/etc/ssl/certs/ca-certificates.crt}"
export NODE_TLS_REJECT_UNAUTHORIZED="${NODE_TLS_REJECT_UNAUTHORIZED:-0}"

unset ELECTRON_RUN_AS_NODE
unset ELECTRON_NO_ATTACH_CONSOLE
unset VSCODE_CLI
unset VSCODE_CWD
unset VSCODE_ESM_ENTRYPOINT
unset VSCODE_HANDLES_UNCAUGHT_ERRORS
unset VSCODE_IPC_HOOK
unset VSCODE_NLS_CONFIG
unset VSCODE_PID
unset VSCODE_RESOLVING_ENVIRONMENT

exec /usr/share/windsurf-next/windsurf-next --ignore-certificate-errors "$@"
