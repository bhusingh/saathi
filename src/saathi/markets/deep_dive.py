"""Optional TradingAgents integration through the loopback Hermes proxy."""

from __future__ import annotations

import os
import sys
from datetime import date
from importlib import import_module
from pathlib import Path
from typing import Any


def run_deep_dive(symbol: str, when: date, timeout: int = 1800) -> str:
    """Run an installed TradingAgents checkout with free-model proxy settings."""

    home = os.environ.get("TRADINGAGENTS_HOME")
    if not home:
        raise RuntimeError("TRADINGAGENTS_HOME is not set; see docs/markets.md")
    del timeout  # the caller/scheduler owns the long-running process timeout
    checkout = Path(home)
    if not (checkout / "tradingagents").is_dir():
        raise RuntimeError(f"TradingAgents package not found under: {checkout}")
    model = os.environ.get("SAATHI_FREE_MODEL", "")
    fallback = os.environ.get("SAATHI_FREE_FALLBACK", model)
    if not model.endswith(":free") or not fallback.endswith(":free"):
        raise RuntimeError("SAATHI_FREE_MODEL and fallback must identify current :free models")
    sys.path.insert(0, str(checkout))
    defaults_module = import_module("tradingagents.default_config")
    graph_module = import_module("tradingagents.graph.trading_graph")
    config: dict[str, Any] = dict(defaults_module.DEFAULT_CONFIG)
    config.update(
        llm_provider="openai_compatible",
        backend_url=os.environ.get("SAATHI_MODEL_BASE_URL", "http://127.0.0.1:8645/v1"),
        deep_think_llm=model,
        quick_think_llm=fallback,
        max_debate_rounds=1,
        max_risk_discuss_rounds=1,
        llm_max_retries=4,
    )
    vendors = dict(config.get("data_vendors", {}))
    if not os.environ.get("FRED_API_KEY"):
        vendors.pop("macro_data", None)
    config["data_vendors"] = vendors
    graph = graph_module.TradingAgentsGraph(debug=False, config=config)
    state, decision = graph.propagate(symbol, when.isoformat())
    return _format_result(state, decision)


def _format_result(state: dict[str, Any], decision: object) -> str:
    sections = (
        ("fundamentals_report", "FUNDAMENTALS"),
        ("market_report", "TECHNICALS"),
        ("news_report", "NEWS"),
        ("sentiment_report", "SENTIMENT"),
        ("investment_plan", "BULL vs BEAR - RESEARCH MANAGER"),
        ("final_trade_decision", "RISK TEAM / FINAL"),
    )
    lines = [f"\n===== {title} =====\n{state[key]}" for key, title in sections if state.get(key)]
    lines.append(
        f"\n===== MODEL RATING (one opinion from free AI models, not advice) =====\n{decision}"
    )
    return "\n".join(lines)
