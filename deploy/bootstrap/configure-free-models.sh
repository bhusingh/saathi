#!/usr/bin/env bash
set -euo pipefail

MODEL=${SAATHI_FREE_MODEL:-}
FALLBACK=${SAATHI_FREE_FALLBACK:-}
PROVIDER=${SAATHI_MODEL_PROVIDER:-nous}
TERMINAL_BACKEND=${SAATHI_TERMINAL_BACKEND:-local}
MODAL_MODE=${SAATHI_MODAL_MODE:-direct}

if [[ -z ${MODEL} || ${MODEL} != *:free ]]; then
  echo "Set SAATHI_FREE_MODEL to a currently available model ending in :free." >&2
  exit 1
fi
if [[ -n ${FALLBACK} && ${FALLBACK} != *:free ]]; then
  echo "SAATHI_FREE_FALLBACK must end in :free." >&2
  exit 1
fi

hermes config set model.default "${MODEL}"
hermes config set model.provider "${PROVIDER}"
hermes config set auxiliary.free_only true
hermes config set auxiliary.openrouter_model "${MODEL}"

for task in vision compression title_generation session_search background_review \
  skills_hub mcp approval triage_specifier curator moa_reference; do
  hermes config set "auxiliary.${task}.provider" "${PROVIDER}"
  hermes config set "auxiliary.${task}.model" "${MODEL}"
done

hermes config set delegation.model "${MODEL}"
hermes config set delegation.provider "${PROVIDER}"
hermes config set delegation.fallback_providers \
  "[{provider: ${PROVIDER}, model: '${FALLBACK:-${MODEL}}'}]"
hermes config set terminal.backend "${TERMINAL_BACKEND}"
hermes config set terminal.modal_mode "${MODAL_MODE}"
hermes config set toolsets '["hermes-cli"]'
hermes config set platform_toolsets.cron '[]'

if [[ -n ${FALLBACK} ]]; then
  hermes config set fallback_providers "[{provider: ${PROVIDER}, model: '${FALLBACK}'}]"
else
  hermes config set fallback_providers "[]"
fi

echo "Free-only guardrails written. Review with: hermes config show"
