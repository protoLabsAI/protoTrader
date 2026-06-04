"""factors plugin — protoTrader Slice 4. A tractable Alpha Zoo: price/volume
factors IC-scored over a universe. Needs requirements-finance.txt. ADR 0018."""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.factors")


def register(registry) -> None:
    from .tools import get_factor_tools

    registry.register_tools(get_factor_tools())
    log.info("[factors] registered factor-evaluation tools (Alpha Zoo)")
