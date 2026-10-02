# Choosing your stack

Saathi's defaults target an always-on personal companion at $0, but every layer is a choice. **Default**
marks the documented path. GitHub counts below are rounded **stars as of Oct 2026**; popularity is context,
not a security or quality guarantee. Costs and free tiers can change, so verify them before deployment.

Vetted optional repository metadata and owner-run installation commands have one canonical source:
[`catalog/addons.yaml`](../catalog/addons.yaml). The comparison below does not duplicate those add-on facts.

The privacy baseline is the same for every combination: memory, files, skills, schedules, credentials, and
state live on infrastructure you control. Prompts go to the model provider you choose. Only a local model
keeps model prompts on your own machine.

## Agent runtime

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **Hermes Agent (default)** | Runtime with memory, skills, cron, tools, and 20+ messaging platforms | MIT | 250k | $0 | Fits a 1 GB VM with swap | Local state; prompts follow the chosen model | The complete $0 Saathi path |
| OpenClaw | Popular “does things” agent runtime | Not stated by GitHub API; check before use | 391k | $0 software | Check current deployment guidance | Depends on model and connectors | A broad action-oriented agent |
| n8n | Visual workflow automation with AI nodes | Fair-code | 206k | Self-hosted option; hosted plans available | Heavier; prefer 4 GB+ | Local workflows when self-hosted; connected services receive data | Visual, auditable automations |
| Huginn | Classic self-hosted monitoring agents; no LLM required | MIT | 50k | $0 | More than the default collector-only path | Can remain fully local except sources | Deterministic monitoring without an LLM |
| Letta | Stateful agent runtime centred on memory | Apache-2.0 | 25k | $0 software | Prefer more than 1 GB | Local memory; prompts follow model choice | Long-lived, memory-heavy agents |

Pick this if:

- Pick Hermes for the documented scheduler, skills, memory, and gateway integration.
- Pick n8n when non-programmers need to inspect and edit a visual flow and you can fund more RAM.
- Pick Huginn when rules and monitoring are enough and no model should see the data.
- Pick Letta when stateful memory is the main requirement; pick OpenClaw for its broader action ecosystem.
- Replacing Hermes needs code in the scheduling and delivery adapters; collectors and prompts can be reused.

## Agent framework (build your own runtime)

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **None (default)** | Use Hermes rather than maintaining a custom runtime | n/a | n/a | $0 | Lowest | Fewer moving parts | Most operators |
| LangGraph | Graph-based, stateful agent framework | MIT | 43k | $0 software | App-dependent; usually 2 GB+ to develop comfortably | Depends on storage, tools, and model | Explicit state machines and durable flows |
| CrewAI | Role-and-crew multi-agent framework | MIT | 59k | $0 software | App-dependent; usually 2 GB+ | Depends on tools and model | Role-based multi-agent collaboration |
| AutoGen | Microsoft's multi-agent programming framework | MIT | 61k | $0 software | App-dependent; usually 2 GB+ | Depends on tools and model | Existing AutoGen projects; last push was Apr 2026, so assess activity |

Pick this if:

- Stay with no framework when configuration and Markdown prompts cover the job.
- Pick LangGraph for explicit branching, checkpoints, and human approval states.
- Pick CrewAI when role-based delegation is the clearest mental model.
- Pick AutoGen only after checking its current maintenance pace and ecosystem fit.
- Any framework choice replaces runtime orchestration and therefore needs code; Saathi's domain ports and
  normalized collector output are intended reuse boundaries.

## Memory

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **Hermes memory (default)** | Runtime-managed conversation and skill memory | MIT | Included in Hermes' 250k | $0 | Fits the default VM | Stored on your host; recalled content goes to the model | A simple integrated setup |
| mem0 | Standalone memory layer for AI applications | Apache-2.0 | 66k | $0 software; hosted services may cost | Budget extra RAM and storage | Self-host for control; embeddings/models may receive content | Shared memory across custom agents |
| No long-term memory | Stateless prompts plus Saathi's small operational JSON state | n/a | n/a | $0 | Lowest | Minimizes retained personal data | Sensitive or narrowly scoped jobs |

Pick this if:

- Use Hermes memory for the default companion experience.
- Add mem0 when multiple custom applications must share memory; this needs a new adapter and deployment.
- Disable long-term memory when data minimization matters more than personalization.

## Web and data reach

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **Saathi collectors (default)** | Allowlisted RSS/API collectors with normalized, cited output | MIT | Included in this project | $0 | Fits 1 GB with swap | Public requests leave the host; no browser profile | Reliable scheduled research |
| Jina Reader | Converts a URL to model-friendly Markdown | Apache-2.0 | 12k | Free usage available; verify limits | Low locally | URLs/content pass through Jina | Simple article extraction |
| SearXNG | Self-hosted metasearch | AGPL-3.0 | 38k | $0 software | Prefer 2–4 GB+ | Queries stay on your host but go to upstream engines | Search independence on a larger host |
| OpenCLI | Drives sites through your logged-in browser | Apache-2.0 | 30k | $0 | Desktop browser required | High account/session exposure | Sites with no suitable public API |
| browser-use | Agentic browser automation | MIT | 117k | $0 software; model/browser costs vary | About 1–2 GB extra; not for `e2-micro` | Pages, sessions, and prompts may reach the model | Complex interactive sites |

Pick this if:

- Use built-in collectors whenever a public feed or API exists.
- See `catalog/addons.yaml` for vetted optional reach and public-video tooling.
- Pick browser-use only on a machine with another 1–2 GB available, never the free `e2-micro`.
- New feed/API types need a small registered source adapter. Browser tools need code or a runtime skill plus
  a larger host; allowlisted RSS instances remain configuration-only.

## Markets

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **yfinance data (default)** | Unofficial Yahoo market data used for deterministic sheets | Apache-2.0 | 25k | $0 | Fits 1 GB, though imports are slow | Ticker queries go to Yahoo | Lightweight quotes and fundamentals |
| ai-hedge-fund | Investor-persona research agents | MIT | 64k | $0 software; some data requires paid APIs | Prefer 4 GB+ | Prompts/data go to configured providers | Comparing investor-style viewpoints |
| FinRobot | Financial AI agent platform | Apache-2.0 | 8k | $0 software; providers may cost | Prefer 4 GB+ | Depends on model and data providers | Building finance-specific agents |
| claude-trading-skills | `SKILL.md` market-analysis packs usable by Hermes | MIT | 3k | $0 | Small beyond runtime/model | Skill inputs go to the chosen model | Extending Hermes without a second runtime |
| OpenBB | Large open financial data platform | Check current official terms | Not used here; old GitHub path redirected unexpectedly | Free and paid data vary | Heavy; use 4 GB+ | Depends on selected data providers | Broad professional data workflows |

Pick this if:

- Use yfinance for the default deterministic, delayed, unofficial data path.
- See `catalog/addons.yaml` for the vetted optional deep-dive repository and its risks.
- Pick the skills pack for lighter Hermes-native analysis, or ai-hedge-fund for persona comparisons.
- Pick FinRobot or OpenBB when building a larger finance workstation. The GitHub API redirected the old
  `OpenBB-finance/OpenBB` path to an organization named `openbq-org`; install OpenBB only from links on the
  official `openbb.co` site.
- yfinance and TradingAgents are already adapter/config integrations. Other market engines need code.

## Models and local chat

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **Nous Portal free models (default)** | OAuth plus a local OpenAI-compatible proxy | Provider terms | n/a | $0 while offered | Proxy fits 1 GB; inference is remote | Prompts leave your machine | The documented $0 cloud setup |
| OpenRouter `:free` | Rate-limited hosted free models behind one key | Provider/model terms | n/a | $0 tier | Low locally | Prompts leave your machine | More free-model choice and fallback |
| Any paid API | OpenAI-compatible or native commercial model API | Provider/model terms | n/a | Usage-based | Low locally | Prompts leave your machine | Reliability, quality, and support |
| Ollama | Run models on your own computer | MIT | 182k | $0 software; hardware/electricity apply | A capable laptop/desktop, commonly 8 GB+ | Maximum privacy: prompts and inference stay local | Private local inference |
| Open WebUI | Optional local chat UI, often paired with Ollama | Check current licence | 153k | $0 software | Budget about 1 GB plus model RAM | Local if every configured backend is local | A polished private browser UI |

Pick this if:

- Use Nous Portal for the $0 default, but expect free models to be withdrawn and keep a current fallback.
- Use OpenRouter `:free` for another free pool, accepting keys, rate limits, and remote prompts.
- Pay for an API when predictable availability matters more than $0 operation.
- Use Ollama on your own capable machine for maximum privacy; the free VM cannot run useful local models.
- Provider, model, and OpenAI-compatible base URL are configuration-level choices. Set
  `SAATHI_MODEL_PROVIDER`, `SAATHI_FREE_MODEL`, `SAATHI_FREE_FALLBACK`, and
  `SAATHI_MODEL_BASE_URL`; a provider with a non-compatible protocol needs code.

## Hosting

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **GCP `e2-micro` (default)** | Always-free-eligible small VM in qualifying regions | Service terms | n/a | $0 only within current limits; IPv4/egress may cost | 1 GB plus configured swap | Google hosts encrypted credentials and local state | Always-on collectors and remote models |
| Oracle Always Free Ampere | Arm VM with more RAM than `e2-micro` | Service terms | n/a | $0 within current limits | Shape/capacity dependent | Oracle hosts state | More headroom if signup and capacity work |
| Own Mac/PC/Raspberry Pi | Run on hardware you control | n/a | n/a | No hosting fee; power/hardware apply | Whatever the device provides | Best infrastructure control | Maximum privacy and local Ollama |
| Hetzner-class VPS | Small paid VM | Service terms | n/a | About EUR 4/month | Choose 4 GB+ | VPS operator hosts state | Browser automation, SearXNG, heavier runtimes |
| AWS/Azure credits | General cloud VM funded by introductory credits | Service terms | n/a | $0 temporarily, then billed | Shape-dependent | Cloud operator hosts state | Short experiments, not a permanent $0 plan |

Pick this if:

- Pick GCP for the documented always-on $0 path and recheck billing/free-tier rules.
- Try Oracle for more free RAM, expecting sign-up rejections and capacity errors.
- Use your own computer for Ollama, accepting that Saathi sleeps when it sleeps.
- Pay about EUR 4/month for 4 GB+ when browser-use, SearXNG, or a heavier runtime matters.
- Hosting swaps need deployment changes, not collector code; architecture-specific dependencies may need
  package adjustments.

## Command execution backend

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **Local (default)** | Commands run directly on the Saathi host | n/a | n/a | $0 | Lowest | Data stays on host except tool/model requests | Trusted personal scripts on a hardened VM |
| Docker | Per-command container isolation | Apache-2.0 | n/a | $0 software | More RAM/disk than local | Local, subject to image/tool networking | Dependency and filesystem isolation |
| Modal | Remote serverless execution | Service terms | n/a | $30/month free credit; usage beyond that costs | Reserve 1 GB, not the 5 GB default | Code/data leave the host | Bursty compute with explicit cost controls |
| Daytona | Sandbox infrastructure for running AI-generated code | Check current terms | 72k | Free/paid options vary | Host/service dependent | Code/data go to the selected deployment | Managed or self-hosted workspaces |

Pick this if:

- Use local for the small default host and fewest moving parts.
- Use Docker when isolation is worth the memory overhead.
- Use Modal only after setting a spending limit. It cannot reach a localhost proxy; use a remote model
  endpoint or an authenticated queue, set `modal_mode: direct`, and reserve 1 GB rather than 5 GB.
- Use Daytona for richer disposable workspaces after reviewing current deployment and licence terms.
- Hermes-supported backends are configuration-only through `SAATHI_TERMINAL_BACKEND`; an unsupported
  backend needs a command-runner adapter.

## Chat front end and notifications

| Option | What it is | Licence | Stars as of Oct 2026 | Cost | RAM need | Privacy | Best for |
|---|---|---:|---:|---:|---:|---|---|
| **Discord (default)** | Private channels per job, threads, and a fail-closed user allowlist | Service terms | n/a | $0 | Gateway fits the default VM | Discord stores delivered messages | Organized reports and operational channels |
| Telegram | Bot chat created through BotFather | Service terms | n/a | $0 | Low | Telegram stores bot messages | Simplest bot setup |
| Slack | Workspace app and channels via Hermes gateway | Service terms | n/a | Free/paid plans | Low locally | Slack stores delivered messages | Existing team workflows |
| WhatsApp / Signal / email / others | Additional transports supported by Hermes gateway | Service/provider terms | n/a | Varies | Varies | The chosen service receives messages | Meeting people in their existing inbox |

Pick this if:

- Use Discord for the documented setup, channel mapping, and fail-closed allowlist.
- Use Telegram for the shortest bot-creation flow, or Slack for an existing workspace.
- Use another Hermes gateway when its privacy and account terms fit. Set `notifier.target_prefix` in
  `config/stack.yaml`; Saathi's automatic target provisioning is Discord-specific, so provisioning another
  service needs an adapter or manually prepared target mappings.

## Recommended combinations

| Goal | Combination | Why |
|---|---|---|
| **$0 cloud (default)** | GCP `e2-micro` + Hermes + Nous Portal free models + local backend + Discord + built-in collectors | Always on, low RAM, and documented end to end; prompts still go to Nous |
| **Maximum privacy** | Own capable computer + Hermes + Ollama + local backend + local/public collectors | State and model inference remain on hardware you control; avoid cloud model fallbacks |
| **Power user** | About EUR 4/month 4 GB+ VPS + Hermes + browser-use + SearXNG + Docker/local backend | Enough memory for search and browser automation, with explicit isolation choices |
| **Markets-focused** | 4 GB+ host + yfinance + Hermes market skills + optional TradingAgents deep dives | Deterministic data first, model analysis second; no brokerage connection |
| **Creator-focused** | Hermes + built-in feeds + yt-dlp captions + optional Agent-Reach | Good public-video coverage; add logged-in routes only after accepting ban/privacy risk |

## What is configuration-only?

- Sources already in the registry, schedules, prompts, profiles, model/provider/base URL, Hermes-supported
  terminal backends, and an existing Hermes notification target are configuration-level choices.
- A new feed/API protocol needs a `Source` adapter and registry builder. A non-OpenAI-compatible model API
  needs a model integration. A non-Hermes execution system needs a `CommandRunner` adapter.
- Changing away from Hermes changes scheduling, memory, skills, and gateway APIs and needs runtime adapter
  work. Automatic channel/user setup for a chat service other than Discord also needs code.
