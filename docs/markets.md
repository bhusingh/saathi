# Markets

Install the optional dependency group:

```bash
.venv/bin/pip install '.[markets]'
saathi markets brief
saathi markets fundamentals SPY QQQ
saathi markets alerts
saathi markets macro week
```

Numbers come from scripts, never model memory. Yahoo Finance is unofficial and usually delayed. Missing values
remain `n/a`. Options analytics are gated to 09:45–16:45 US/Eastern on weekdays because Yahoo can report near-
zero IV and open interest outside that window. Alerts are research notifications, deduplicated by daily
threshold bucket. They never place trades or connect to a brokerage.

For optional TradingAgents research, install it in its own environment and set `TRADINGAGENTS_HOME`,
`SAATHI_FREE_MODEL`, and `SAATHI_FREE_FALLBACK` in `~/.hermes/.env`. Saathi points the integration at
`SAATHI_MODEL_BASE_URL`, defaulting to `http://127.0.0.1:8645/v1`. Run only one deep dive at a time on a small
server; it can take 5–20 minutes. Its final rating is one opinion from free AI models, not a recommendation.
Optional FRED or vendor keys belong in `~/.hermes/.env`, never the repository.

Not financial advice—data may be delayed and unofficial.
