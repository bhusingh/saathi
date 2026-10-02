# Cost guardrails

Start with [Billing safety](billing-safety.md): which services need a card, how to use a limited card, and
the common ways people get charged by accident.

The $0 path is conditional, not a guarantee. Confirm current Google Cloud free-tier eligibility in your
billing region. Use `e2-micro`, a free-tier region, `--provisioning-model=STANDARD`, a 30 GB `pd-standard`
disk, no unused snapshots, and minimal network egress. Balanced disks are billed; Spot VMs are preemptible;
external IPv4 can be billed.

Create a budget alert in the billing account's own currency (`1CAD` for a CAD account, for example). Alerts
do not cap spend. Review billing regularly and delete the VM, disk, static addresses, and firewall resources
when done.

Choose only models currently marked `:free`, retain at least one free fallback, set
`auxiliary.free_only: true`, pin auxiliary and delegation tasks, disable image generation, and decline paid
Tool Gateway features. Free models can disappear or return 404; reselect rather than silently moving to paid.

If using Modal, configure its spending limit before credentials are added. Prefer `modal_mode: direct`.
Saathi avoids paid Tool Gateway services. TradingAgents may use other data providers; leave optional vendor
keys unset unless you understand their billing.

