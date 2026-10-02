#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/bootstrap/server-harden.sh" >&2
  exit 1
fi

TIMEZONE=${SAATHI_TIMEZONE:-UTC}
HERMES_USER=${SAATHI_SERVICE_USER:-hermes}
SWAP_FILE=/swapfile

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git libatomic1 unattended-upgrades ufw

if ! id "${HERMES_USER}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "${HERMES_USER}"
fi

install -d -m 700 -o "${HERMES_USER}" -g "${HERMES_USER}" "/home/${HERMES_USER}/.ssh"
KEY_SOURCE="/home/${SUDO_USER:-root}/.ssh/authorized_keys"
KEY_TARGET="/home/${HERMES_USER}/.ssh/authorized_keys"
if [[ -f ${KEY_SOURCE} && ${KEY_SOURCE} != "${KEY_TARGET}" ]]; then
  install -m 600 -o "${HERMES_USER}" -g "${HERMES_USER}" \
    "${KEY_SOURCE}" "${KEY_TARGET}"
fi

install -d -m 755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/00-saathi.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin no
EOF
chmod 644 /etc/ssh/sshd_config.d/00-saathi.conf
sshd -t
systemctl reload ssh

timedatectl set-timezone "${TIMEZONE}"
dpkg-reconfigure -f noninteractive unattended-upgrades

if [[ ! -f ${SWAP_FILE} ]]; then
  fallocate -l 2G "${SWAP_FILE}"
  chmod 600 "${SWAP_FILE}"
  mkswap "${SWAP_FILE}"
fi
swapon --show=NAME --noheadings | grep -Fxq "${SWAP_FILE}" || swapon "${SWAP_FILE}"
grep -Fq "${SWAP_FILE} none swap sw 0 0" /etc/fstab || \
  echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable
loginctl enable-linger "${HERMES_USER}"

echo "Hardened host for ${HERMES_USER}. Confirm SSH key login in a second terminal before closing this one."
