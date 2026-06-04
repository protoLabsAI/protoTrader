"""broker plugin — protoTrader Slice 6 (gated paper execution).

Contributes the paper-trading **tools** behind the full gated-execution stack
(mandate → kill-switch → per-order human approval → simulated fill → audit). The
broker is **OFF by default**: with no ``broker_mandate.yaml`` (or ``enabled:
false``) every order is refused, so enabling the plugin is safe. ``mode: live`` is
deliberately not implemented — this slice cannot move real money.

Built on the plugin reach (ADR 0018/0019) — no core edit.
"""

from __future__ import annotations

import logging

log = logging.getLogger("protoagent.plugins.broker")


def register(registry) -> None:
    from .tools import get_broker_tools

    registry.register_tools(get_broker_tools())
    log.info("[broker] registered paper-execution tools (gated, OFF until a mandate is set)")
