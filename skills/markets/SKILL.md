---
name: markets
description: Deterministic stock and options research using Saathi's local market commands.
---

# Markets research

Research only. Never place trades, connect to a brokerage, or tell the user to buy or sell. Present data and
scenarios. End market answers with: “Not financial advice—data may be delayed and unofficial.”

Never state prices, ratios, earnings, or percentages from memory. Run `saathi markets fundamentals TICKER`
for valuation/earnings fields or `saathi markets brief` for technical context. Compare tickers only from the
command output. Preserve `n/a` rather than guessing.

Yahoo options data is used only from 09:45–16:45 US/Eastern on weekdays. Outside that window, explain that
IV, Greeks, and open interest are skipped because data may be stale.

Run deep dives one at a time. Label the result “one opinion from free AI models,” summarise its evidence and
risks separately, and never present its rating as a recommendation.
