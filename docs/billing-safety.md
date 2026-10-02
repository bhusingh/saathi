# Billing safety: stay at $0

Several services in this guide ask for a payment card even on free plans. A card on file means a mistake
can turn into a bill. Read this page **before** you add a card anywhere, and keep it open while you set up.

> Free tiers, credits and prices change. Everything below was true when written (October 2026); check each
> provider's current terms before you rely on it.

## The three rules

1. **Do not add a card unless the service will not work without one.** Where a card is optional, skip it.
2. **When a card is required, use a card you can limit.** A virtual or single-purpose card with a low spending
   limit (for example 1-5 in your currency), or a prepaid card, means a mistake gets declined instead of
   billed. Many banks offer virtual cards with per-card limits; some card apps let you lock or set a monthly
   cap per merchant. Lock or delete it if you stop using the service.
3. **Set the provider's own limit or alert as well.** Card limits stop charges; provider limits stop the
   usage that causes them, and alerts tell you early.

## Service by service

| Service | Card needed? | What can charge you | What to do |
|---|---|---|---|
| **Google Cloud** (VM) | **Yes**, for identity verification | Wrong machine type or region, a **Balanced** disk instead of Standard, Spot/extra VMs, snapshots, static or external IPv4 addresses, network egress beyond the free allowance, leaving the 90-day trial credit and staying on paid resources | Limited/virtual card. Create **only** what `deploy/gcp/create-vm.sh` creates (e2-micro, us-west1/us-central1/us-east1, `pd-standard` 30 GB, `STANDARD` provisioning). Run `deploy/gcp/budget.sh` with a tiny amount **in your billing account's currency**. Check the Billing → Reports page after 2-3 days and monthly. Delete anything you are not using. |
| **Oracle Cloud** (alternative host) | **Yes**, for verification | Upgrading to Pay-As-You-Go (often suggested to get past "out of capacity") and then creating non-Always-Free shapes or storage | Limited/virtual card. Only create resources marked **Always Free**. If you upgrade to Pay-As-You-Go, set a budget alert immediately and double-check every shape and volume. |
| **Nous Portal** (models) | **No** for the free plan | Adding credits or a subscription, then using paid models or the paid **Tool Gateway** (web search, image generation, browser, cloud terminal) | **Do not add a card or top up.** With a $0 balance, paid calls fail instead of charging you. Keep `configure-free-models.sh` settings: free main + fallback models, `auxiliary.free_only: true`, image generation disabled, Tool Gateway declined. |
| **Modal** (optional command backend) | Check at sign-up | Usage above the monthly free credit, especially a container left running or the default 5 GB memory reservation | **Set a workspace spending limit before connecting it** (equal to the free credit, or lower). Reserve 1 GB, keep idle shutdown on, use `terminal.modal_mode: direct`. Check the usage page after the first days. |
| **OpenRouter** (optional models) | **No** for `:free` models | Adding credits, then using non-free models | Do not add credits. Use only models ending in `:free`. |
| **AWS / Azure** (optional hosts) | **Yes** | Credits run out or the trial ends and resources keep running on paid rates | Limited/virtual card. Set budgets on day one. Note the credit expiry date in your calendar and delete resources before it. |
| **Cloudflare** (optional tunnel/pages) | **No** on the free plan | Enabling paid add-ons (Workers Paid, Containers, extra products) | Stay on the free plan; do not add a card unless you deliberately upgrade. |
| **Discord, GitHub** | **No** | Paid plans you opt into | Nothing to do. Saathi needs no paid features. |
| **TradingAgents data vendors** (optional) | Depends on vendor | Paid API tiers (e.g. some market-data keys) | Leave paid vendor keys unset; the defaults (Yahoo Finance, SEC EDGAR, FRED) are free. A free FRED key needs no card. |

## Common ways people get charged by accident

- **Budget alerts are not caps.** Google and most clouds email you after spending happens; they do not stop
  it. Your protection is the limited card plus creating only free resources. (Advanced: Google documents a
  way to disable billing automatically from a budget notification; it uses extra services, so only set it up
  if you understand it.)
- **Wrong disk type.** The console's default boot disk is often "Balanced", which is billed. Use Standard.
- **Wrong region.** The free VM is only free in specific US regions.
- **"Just one more VM".** The free allowance covers one e2-micro. A second VM, a bigger machine, or a GPU is
  billed from the first hour.
- **Public IPv4 addresses** may be billed by some providers. Check your first invoice; Saathi works with
  Cloudflare Tunnel if you remove the public address later.
- **Free model withdrawn.** A model that stops being free returns an error on a $0 balance (good). With a
  card or credits on file, it might silently bill instead. That is exactly why rule 1 matters for Nous and
  OpenRouter.
- **Paid tools switched on by a wizard.** Setup wizards (Hermes `portal`/`setup`, provider dashboards) may
  offer image generation, web search or managed sandboxes. Decline anything not marked free.
- **Trial credit expiry.** "$300 for 90 days" style credits end; whatever is still running then is billed.
- **Forgotten resources.** Snapshots, unattached disks, static IPs and old projects keep billing. Delete
  them, or delete the whole project when you are done.

## Five-minute monthly check

1. Cloud billing page: this month's cost is 0 (or what you expect). No new line items.
2. Resources list: one e2-micro VM, one 30 GB Standard disk, nothing else.
3. Nous / OpenRouter: balance still $0, no payment method added.
4. Modal (if used): usage below the limit, no long-running containers.
5. Your limited card's transaction list: no charges, or only expected tiny verification holds (these are
   usually reversed).

## Stopping completely

Uninstall in this order: stop the Hermes services, delete the VM, disk, firewall rules, static addresses and
budget (or delete the whole project), revoke the Discord bot and Portal OAuth, then lock or delete the
limited card. Deleting the VM/project is the only reliable way to stop infrastructure charges.
