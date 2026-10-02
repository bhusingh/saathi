#!/usr/bin/env bash
set -euo pipefail

BILLING_ACCOUNT=${GCP_BILLING_ACCOUNT:?Set GCP_BILLING_ACCOUNT}
PROJECT=${GCP_PROJECT:?Set GCP_PROJECT}
AMOUNT=${GCP_BUDGET_AMOUNT:?Set GCP_BUDGET_AMOUNT, including billing currency amount}

gcloud billing budgets create \
  --billing-account="${BILLING_ACCOUNT}" \
  --display-name="Saathi guardrail" \
  --budget-amount="${AMOUNT}" \
  --filter-projects="projects/${PROJECT}" \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0

echo "Budget alerts notify; they do not stop resources. Verify the amount uses the billing account currency."
