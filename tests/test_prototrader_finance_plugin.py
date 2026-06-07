"""protoTrader consumes the finance plugin via git install, not a vendored copy.

The plugin's logic (backtest / broker / factor / behavioral engines, the desk, the
dashboard) is tested in its own repo — protoLabsAI/prototrader-finance. Here we
only assert the **fork's wiring** of the dogfooding loop (ADR 0027): the plugin is
pinned in `plugins.lock`, and its code isn't vendored. Both checks are cheap and
self-contained (no host framework, no network) — actual install/load is verified
by running `python -m server plugin sync` locally and the plugin's own CI.
"""

from __future__ import annotations

import json
from pathlib import Path

PLUGIN = "prototrader-finance"
ROOT = Path(__file__).parent.parent


def test_plugin_is_locked():
    """The fork pins the plugin in plugins.lock with a resolved SHA."""
    lock = json.loads((ROOT / "plugins.lock").read_text())
    by_id = {p["id"]: p for p in lock.get("plugins", [])}
    assert PLUGIN in by_id, "prototrader-finance missing from plugins.lock"
    entry = by_id[PLUGIN]
    assert entry["source_url"].rstrip("/").endswith("prototrader-finance")
    assert entry["resolved_sha"], "lock entry has no pinned SHA"


def test_finance_code_is_not_vendored():
    """It's consumed via the lock, not copied into the tree (one source of truth)."""
    assert not (ROOT / "plugins" / PLUGIN).exists(), "plugin should not be vendored in the fork"
    for old in ("finance-data", "backtest", "factors", "behavioral", "broker", "finance-desk"):
        assert not (ROOT / "plugins" / old).exists(), f"stale plugin dir plugins/{old}"
