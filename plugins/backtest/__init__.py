"""backtest plugin — protoTrader Slice 2. Vectorized strategy backtesting
(realistic costs, OOS split, buy-and-hold benchmark, bootstrap Sharpe CI).
Needs `requirements-finance.txt` + pandas/numpy (base deps). ADR 0018."""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.backtest")


def register(registry) -> None:
    from .tools import get_backtest_tools

    registry.register_tools(get_backtest_tools())
    log.info("[backtest] registered backtest tools")
