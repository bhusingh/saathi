# Customising

The normal path is conversational. In an interactive chat with the allowlisted owner, Hermes uses
`skills/saathi-config/SKILL.md` to stage the request and show its exact diff:

```text
Owner: add NVDA
Hermes: runs saathi config propose "add NVDA", then shows the diff and change ID
Owner: yes
Hermes: runs saathi config apply CHANGE_ID, then saathi jobs sync --apply
```

Other examples include “stop Reddit”, “shorter LinkedIn drafts”, “track robotics news daily”, “make creator
radar weekly”, “disable policy watch”, and “add https://example.org/feed.xml”. An HTTPS feed's host joins
`http.allowed_hosts` in the same proposed diff. Undo with `saathi config undo`, then resync jobs.

Requests containing a token, password, API key, other secret, non-HTTPS source, package installation, or
repository clone are refused. Credentials use hidden input and `~/.hermes/.env` mode `0600`. Add-ons are
reviewed from `catalog/addons.yaml` and installed manually. Scheduled jobs have no tools as a prompt-injection
boundary; only interactive owner chat may invoke config changes.

Record weekly output preferences with `saathi feedback record "shorter market briefs"`. Content prompts read
`state/feedback.md` as preferences, never as factual evidence.

## Advanced manual configuration

Configured YAML is the product's data layer. To add a feed, append a source to an existing collector in
`config/sources.yaml`; its host must also appear in `http.allowed_hosts`. Supported types are `rss`, `reddit`,
`google_news`, `hackernews`, `github`, `arxiv`, `youtube`, `appstore`, `openfda`, and `federal_register`.

To add a report, add a collector in `sources.yaml`, write a prompt in `prompts/`, add the channel name to
`discord.yaml`, and add a schedule to `jobs.yaml`. Rerun Discord setup if the channel is new, preview with
`saathi jobs sync`, then apply. Lists of feeds, creators, tickers, competitors, subreddits, schedules, prompt
names, and channels should never be added to Python.

Scheduled jobs define exactly one of `collector: configured_name` or a safe argument list under `command:`.
The latter can schedule any Saathi CLI path, for example `command: [markets, macro, week]`. Configure the
Python executable once as `runtime.interpreter` in `stack.yaml`.

Prompts support `{profile}`, `{feedback}`, and `{rules}`. Shared rules require citations, summaries rather
than copying, and no invented values. Keep a human in the loop for publishing, financial decisions, legal
decisions, outreach, or any external action.
