#!/usr/bin/env bash
set -euo pipefail

PROJECT=${GCP_PROJECT:?Set GCP_PROJECT}
ZONE=${GCP_ZONE:-us-west1-b}
VM_NAME=${GCP_VM_NAME:-saathi}
SSH_KEY_FILE=${SAATHI_SSH_PUBLIC_KEY:?Set SAATHI_SSH_PUBLIC_KEY to a dedicated .pub path}
DISABLE_DEFAULT_RULES=${SAATHI_DISABLE_DEFAULT_FIREWALL_RULES:-}
SSH_METADATA=$(mktemp)
trap 'rm -f "${SSH_METADATA}"' EXIT

if [[ ! -f ${SSH_KEY_FILE} ]]; then
  echo "SSH public key file not found: ${SSH_KEY_FILE}" >&2
  exit 1
fi
printf 'hermes:%s\n' "$(<"${SSH_KEY_FILE}")" > "${SSH_METADATA}"

case "${ZONE}" in
  us-west1-*|us-central1-*|us-east1-*) ;;
  *) echo "Use an always-free eligible region: us-west1, us-central1, or us-east1." >&2; exit 1 ;;
esac

default_rules=()
for rule in default-allow-ssh default-allow-rdp; do
  if gcloud compute firewall-rules describe "${rule}" --project="${PROJECT}" >/dev/null 2>&1; then
    default_rules+=("${rule}")
  fi
done
if (( ${#default_rules[@]} )); then
  if [[ ${DISABLE_DEFAULT_RULES} != yes ]]; then
    if [[ -t 0 ]]; then
      read -r -p "Delete permissive ${default_rules[*]} before continuing? [y/N] " answer
      [[ ${answer} == y || ${answer} == Y ]] || {
        echo "Refusing to create a restricted-SSH VM while permissive default rules exist." >&2
        exit 1
      }
    else
      echo "Set SAATHI_DISABLE_DEFAULT_FIREWALL_RULES=yes to remove: ${default_rules[*]}" >&2
      exit 1
    fi
  fi
  gcloud compute firewall-rules delete "${default_rules[@]}" \
    --project="${PROJECT}" --quiet
fi

if gcloud compute instances describe "${VM_NAME}" \
  --project="${PROJECT}" --zone="${ZONE}" >/dev/null 2>&1; then
  echo "VM already exists; skipping: ${VM_NAME}"
else
  gcloud compute instances create "${VM_NAME}" \
    --project="${PROJECT}" \
    --zone="${ZONE}" \
    --machine-type=e2-micro \
    --provisioning-model=STANDARD \
    --image-family=ubuntu-2404-lts-amd64 \
    --image-project=ubuntu-os-cloud \
    --boot-disk-type=pd-standard \
    --boot-disk-size=30GB \
    --metadata=block-project-ssh-keys=TRUE \
    --metadata-from-file="ssh-keys=${SSH_METADATA}" \
    --no-service-account \
    --no-scopes \
    --tags=saathi-ssh
fi

if gcloud compute firewall-rules describe saathi-ssh \
  --project="${PROJECT}" >/dev/null 2>&1; then
  echo "Firewall rule already exists; skipping: saathi-ssh"
else
  gcloud compute firewall-rules create saathi-ssh \
    --project="${PROJECT}" \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges="${SSH_SOURCE_RANGE:?Set SSH_SOURCE_RANGE to your trusted CIDR}" \
    --target-tags=saathi-ssh
fi

echo "VM created. External IPv4 addresses may be billed; review your current Google Cloud pricing."
