#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -eq 0 ]]; then
  echo "Run as the non-root hermes user, not root." >&2
  exit 1
fi

installer=$(mktemp)
trap 'rm -f "${installer}"' EXIT
ref=${HERMES_INSTALL_REF:-}
expected_sha=${HERMES_INSTALLER_SHA256:-}
if [[ -n ${ref} ]]; then
  [[ ${ref} =~ ^[A-Za-z0-9._/-]+$ ]] || {
    echo "HERMES_INSTALL_REF contains unsupported characters." >&2
    exit 1
  }
  installer_url="https://raw.githubusercontent.com/NousResearch/hermes-agent/${ref}/scripts/install.sh"
else
  installer_url="https://hermes-agent.nousresearch.com/install.sh"
fi
curl --proto '=https' --tlsv1.2 -fsSL \
  "${installer_url}" -o "${installer}"
if [[ -n ${expected_sha} ]]; then
  if command -v sha256sum >/dev/null 2>&1; then
    actual_sha=$(sha256sum "${installer}")
  else
    actual_sha=$(shasum -a 256 "${installer}")
  fi
  actual_sha=${actual_sha%% *}
  if [[ ${actual_sha} != "${expected_sha}" ]]; then
    echo "Hermes installer SHA-256 mismatch." >&2
    exit 1
  fi
fi
install_args=(--skip-setup --skip-browser)
if [[ -n ${ref} ]]; then
  install_args+=(--commit "${ref}")
fi
bash "${installer}" "${install_args[@]}"

echo "Hermes installed non-interactively. Next: ssh -t HOST hermes portal"
