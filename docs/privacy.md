# Privacy

Self-hosting keeps Saathi configuration, state, schedules, memory, skills, credentials, and local files on
infrastructure you administer. It does not keep model prompts local when a cloud provider is selected. The
sheet, prompt, conversation history, and relevant memories may be sent to that provider, whose free tier may
log or retain them.

Use only public source data, minimise profile detail, and never put secrets into prompts. Discord also stores
messages delivered through it. Review the privacy terms for Discord, the model provider, cloud host, and every
configured source.

Feed text is untrusted and can contain prompt injection. Prompt wording that labels sheets as data is a weak
model-level control. The stronger boundary for scheduled jobs is `platform_toolsets.cron: []`, which removes
all tools from non-interactive summaries because their data already arrives through the
collector script. Interactive Discord conversations still have the tools configured for Hermes; restrict the
Discord allowlist to the owner only.

The OAuth proxy listens on loopback, but it deliberately accepts any bearer token before attaching the real
credential. Any local process able to reach `127.0.0.1:8645` can therefore use it. Run only trusted local
software and do not treat loopback as per-process authentication.

For maximum privacy, run Hermes with Ollama on your own capable computer and disable cloud fallbacks. An
always-free 1 GB VM can host the scheduler and collectors but cannot run a useful local model. “Maximum
privacy” still requires securing the host, backups, chat endpoint, dependencies, and local model runtime.
