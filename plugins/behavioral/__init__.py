"""behavioral plugin — protoTrader Slice 5 (Shadow Account). Parses a trade
journal into a behavioral profile + bias flags. ADR 0018."""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.behavioral")


def register(registry) -> None:
    from .tools import get_behavioral_tools

    registry.register_tools(get_behavioral_tools())
    log.info("[behavioral] registered trade-journal analysis tool")
