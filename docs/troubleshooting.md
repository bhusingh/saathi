# Troubleshooting

Each entry starts with the symptom, then the likely cause and fix.

## Installation and cloud

**`externally-managed-environment` on macOS/Homebrew Python.** The system Python follows PEP 668. Do not use
`--break-system-packages`; create a venv for Saathi, and use Hermes' supported installer (or `pipx` for other
Python command-line tools).

**Oracle says “account creation failed” despite a valid card.** Oracle's identity/payment checks can reject a
valid application without a useful cause. Retry support/sign-up later or use the documented GCP free-tier
path. **A1 says “out of capacity.”** Try another availability domain, a smaller shape, or PAYG; capacity is not
guaranteed.

**GCP budget creation returns `INVALID_ARGUMENT`.** The amount's currency differs from the billing account.
Use that account's currency, for example `1CAD` rather than `1USD`.

**The disk estimate is not free.** The console defaulted to Balanced. Recreate with `pd-standard`. Spot VMs
are preempted and are not the intended always-on choice. External IPv4 may be billed; check current pricing.

**First SSH attempt says “connection refused.”** A newly created VM is still booting or starting SSH. Wait a
minute and retry. Confirm the firewall source range includes your current public address.

**SSH stopped working after my home IP changed.** From an authenticated Cloud Shell or an existing session,
run `gcloud compute firewall-rules update saathi-ssh --source-ranges=NEW_IP/32`. The restriction is expected
to reject a changed residential address; do not restore `default-allow-ssh` as a workaround.

## Hermes and models

**`node: error while loading shared libraries: libatomic.so.1`.** Install it with
`sudo apt-get install libatomic1`, then rerun the Hermes installer.

**The installer wizard hangs or says it needs a TTY.** Install with `--skip-setup`, then run
`ssh -t ... hermes portal` from your local terminal.

**`HTTP 404: This model is no longer free`.** Free models are withdrawn without notice. Run the model picker,
choose another current `:free` model, update the fallback, and rerun the guardrail script.

**`hermes config set` fails on an auxiliary key.** Not every key beneath `auxiliary` is a mapping: retry,
`free_only`, `openrouter_model`, and streaming settings have different types. Use the explicit task list in
`configure-free-models.sh`; do not loop blindly over the whole section.

**Nous says “You need available funds to create or use API keys.”** The free Portal plan may not issue API
keys. Log in with OAuth and use `hermes proxy start` bound to loopback; it attaches the OAuth credential.

**A tool running on Modal cannot reach the Hermes proxy.** `127.0.0.1` inside Modal is the Modal sandbox, not
your VM. Use the local terminal backend, or design an authenticated queue; never expose the unauthenticated
proxy. If Modal is used, choose `modal_mode: direct` and set a spending limit first.

**The first answer takes 20–60 seconds on `e2-micro`.** Cold imports, process startup, swap, and provider warm-
up are slow on one shared vCPU/1 GB RAM. This is normal unless the health check reports sustained pressure.

## Discord

**The Developer Portal asks “what are you building?”** Choose bot or blank. The template does not matter.

**The invite link shows no server.** Create a server first with Add a Server in the Discord app, not in the
Developer Portal, and ensure your Discord account can manage that server.

**The bot is online but ignores DMs/messages.** Enable Message Content Intent and make sure your numeric user
ID is in `DISCORD_ALLOWED_USERS`. Hermes Discord does not issue a pairing code and denies unlisted users.

**The allowlist still fails.** You may have copied the bot/application ID or a username. Enable Developer Mode
and Copy User ID, use the `\@username` trick, or let `saathi discord setup` discover the guild owner.

**“No home channel is set.”** Set `DISCORD_HOME_CHANNEL` to the intended numeric channel ID in
`~/.hermes/.env`, then restart the gateway.

**Copy User ID is absent.** Turn on Developer Mode in Discord's Advanced settings.

**Automatic channel creation is forbidden.** Temporarily add Manage Channels, rerun setup, then remove it.
Do not add Administrator, Manage Server, or Manage Roles.

**“Opus codec not found.”** This voice warning is harmless for a text-only bot.

## Data sources

**Yahoo options show almost-zero IV or zero open interest.** Off-hours Yahoo option snapshots can be stale.
Saathi skips IV, Greeks, and OI outside 09:45–16:45 US/Eastern weekdays.

**An openFDA result treats PET packaging as a pet recall.** Ensure local word-boundary filtering remains
enabled. Uppercase “PET” often means polyethylene terephthalate, not an animal.

**USCIS RSS returns 403 from a cloud VM.** Do not bypass it with cookies. Use the Federal Register API and a
configured public news search instead.

**Reddit or X asks for cookies/login.** Cookies create privacy and account-ban risk. Prefer RSS and documented
public APIs. Never automate a user account or self-bot.

**GitHub starts returning rate-limit errors.** Unauthenticated repository search allows roughly ten searches
per minute. Reduce topics or keep at least the configured delay between searches.

## Diagnosis

Run these before filing an issue, and redact addresses, IDs, paths, and tokens from the output:

```bash
saathi doctor
hermes config check
hermes cron status
systemctl --user status hermes-gateway hermes-proxy
journalctl --user -u hermes-gateway -n 100 --no-pager
```
