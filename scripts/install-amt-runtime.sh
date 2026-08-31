#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${ROOT_DIR}/runtime/amt-git-refresh.json.example"
SERVICES_DIR="${GTD_RUNTIME_SERVICES_DIR:-${HOME}/.ai/gtd/runtime/services}"
TARGET="${SERVICES_DIR}/amt-git-refresh.json"

mkdir -p "${SERVICES_DIR}" "${HOME}/.ai/amt/runtime"
HOME_VALUE="${HOME}" perl -0pe 's#/Users/you#$ENV{HOME_VALUE}#g' "${SOURCE}" >"${TARGET}"

echo "installed: ${TARGET}"
