"""finance-data plugin — protoTrader Slice 1 (market data).

Contributes the no-auth market-data **tools** (yfinance for US equities/ETFs,
ccxt for crypto). Tools degrade to a clear "install requirements-finance.txt"
error when the optional deps are absent, so the plugin is safe to enable even on
a base install. A fork that doesn't want it: `plugins: { disabled: [finance-data] }`.

Built on the plugin reach (ADR 0018/0019) — no core edit. Later finance slices
(backtest, factors, broker) add their own plugins/skills/subagents/workflows.
"""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.finance-data")


def register(registry) -> None:
    from .tools import get_finance_tools

    registry.register_tools(get_finance_tools())
    log.info("[finance-data] registered market-data tools (equities + crypto)")
