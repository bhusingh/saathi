# Architecture

Saathi uses a small clean architecture.

```text
CLI (composition root)
  ├─ jobs/use cases ──> domain protocols and immutable models
  └─ adapters ────────> HTTP, feeds, JSON state, Discord, Hermes, Yahoo
                                │
                                └─ configured external systems
```

`domain/` has no network, file, process, or provider imports. It defines `Item`, `Sheet`, alerts, scheduled
jobs, formatting policies, config validation, and protocols. `adapters/` implements those protocols and owns
all I/O. `jobs/` composes sources, isolates failures, deduplicates canonical URLs, and exposes registries keyed
by config `type`. `markets/` contains pure calculations and narrowly scoped provider orchestration. `cli.py`
is the only composition root.

One HTTP adapter enforces HTTPS before and after redirects, the configured host allowlist, a 5 MB response
cap, timeout, and descriptive User-Agent. All feed-shaped inputs follow `RssSource`; all output items follow
one formatter; all item dedupe follows `DedupeStore`.
Persistent writes are atomic and private. Collection writes are staged, stdout is written, and only then are
seen hashes and source snapshots committed. This avoids losing items when script output fails; after Hermes
accepts stdout, a later transport delivery failure is not retried. A source exception is logged to stderr
and does not cancel sibling sources or create empty no-agent messages.

Source and collector registries make the common extension path data-only. An operator can add another RSS,
Reddit, Google News, YouTube, App Store, arXiv, Federal Register, openFDA, Hacker News, or GitHub source and
schedule it without changing code. A genuinely new protocol needs one adapter and a registered builder.

State is disposable operational data under `state/`: seen hashes, GitHub star snapshots, daily alert buckets,
and Discord channel mappings. It is gitignored. Prompts remain separate from schedules and profiles so they
can be reviewed independently.

Trade-offs: stdlib `urllib` keeps the dependency surface small; `feedparser` handles both RSS and Atom;
`yfinance` and `yt-dlp` are optional because they are large and less stable. Cron sync defaults to dry-run,
creates missing names, and edits changed definitions by Hermes job ID. A local desired-state fingerprint
covers the command, prompt, script filename, and interpreter to keep repeat runs idempotent without directly
patching Hermes' registry.
