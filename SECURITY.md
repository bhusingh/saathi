# Security policy

## Reporting

Please report suspected vulnerabilities privately through GitHub's security-advisory feature for this
repository. Do not open a public issue containing tokens, credentials, private prompts, server addresses,
or exploit details. Maintainers should acknowledge a report within seven days and coordinate disclosure.

## Threat model summary

Saathi assumes the VM administrator and the configured Discord owner are trusted. It treats feeds, web
content, model output, and Discord messages as untrusted. Important controls are: environment-only secrets;
private file modes; an explicit Discord allowlist; no user-account automation; outbound host allowlisting;
network timeouts; safe YAML parsing; argument-list subprocesses; validated tickers/job names; isolated source
failures; a loopback-only credential proxy; least-privilege cloud/Discord permissions; and secret scanning.

Self-hosting does not make prompts private from the selected model provider. A compromised dependency,
operator account, VM, Discord bot token, OAuth refresh token, or model provider can expose data. Public-feed
content may attempt prompt injection; collector sheets are data, never instructions, and prompts constrain
the model to citation-backed summarisation. Scheduled cron agents are also restricted to the `todo` toolset.
These are defence-in-depth controls, not a proof that a model will ignore adversarial content. The strong
control is removing shell/network tools from the non-interactive cron execution boundary. Interactive
Discord chat still has the configured Hermes tools, so keep `DISCORD_ALLOWED_USERS` limited to the owner and
review model output before acting on it.

Never commit `.env`, configured YAML, state, logs, databases, provider auth files, or server inventory. Rotate
credentials after any suspected exposure. Keep Hermes, the OS, and dependencies updated. Never expose the
Hermes proxy publicly: it intentionally accepts arbitrary bearer strings and adds the real OAuth credential.
Any local process that can connect to `127.0.0.1:8645` can use that proxy credential; loopback prevents
remote access but does not authenticate processes on the host.

Supported security fixes target the latest main branch. Market and policy outputs are research summaries,
not financial or legal advice.
