"""finance-desk plugin — protoTrader Slice 3. Registers the desk subagents
(market-analyst, quant, risk-manager) the lead agent delegates to and the
workflow presets compose. ADR 0018. Disable: plugins.disabled: [finance-desk]."""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.finance-desk")


def register(registry) -> None:
    from .subagents import desk_subagents

    for cfg in desk_subagents():
        registry.register_subagent(cfg)
    log.info("[finance-desk] registered subagents: market-analyst, quant, risk-manager")
