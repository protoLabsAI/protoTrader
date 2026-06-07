"""protoTrader is the host harness for the prototrader-finance plugin.

The plugin's own logic (backtest / broker / factor / behavioral engines) is
unit-tested in its repo — protoLabsAI/prototrader-finance. Here we verify the
**host** side of the dogfooding loop (ADR 0027):

- the plugin is **locked** in `plugins.lock` (the fork pins it), and
- when **installed** (CI runs `python -m server plugin sync` to restore it from
  the lock), it loads through the real plugin loader with its full surface —
  tools, the research desk subagents, the dashboard view + route, and the
  auto-discovered skills/ + workflows/.

The install-dependent tests skip cleanly when the plugin isn't synced yet, so a
bare local `pytest` stays green; CI syncs first.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from graph.config import LangGraphConfig
from graph.plugins.installer import live_plugins_dir
from graph.plugins.loader import load_plugins

PLUGIN = "prototrader-finance"
ROOT = Path(__file__).parent.parent
PLUGIN_DIR = live_plugins_dir() / PLUGIN

EXPECTED_TOOLS = {
    "stock_quote", "stock_price_history", "stock_fundamentals",
    "crypto_quote", "crypto_price_history",
    "backtest_strategy", "list_strategies",
    "factor_eval", "factor_zoo",
    "analyze_trade_journal",
    "broker_place_order", "broker_orders", "broker_account",
}
DESK = {"market-analyst", "quant", "risk-manager"}

# Skip the install-dependent tests until the plugin is synced from the lock.
needs_install = pytest.mark.skipif(
    not PLUGIN_DIR.exists(),
    reason=f"{PLUGIN} not installed — run `python -m server plugin sync` (CI does before tests)",
)


# ── host contract (no install needed) ─────────────────────────────────────────


def test_plugin_is_locked():
    """The dogfood contract: the fork pins the plugin in plugins.lock with a SHA."""
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


# ── installed-surface contract (after `plugin sync`) ──────────────────────────


@pytest.fixture
def loaded():
    cfg = LangGraphConfig()
    cfg.plugins_enabled = [PLUGIN]
    cfg.plugins_disabled = ["discord", "google", "coding_agent", "delegates", "plugin-devkit", "hello"]
    return load_plugins(cfg)


@needs_install
def test_installed_plugin_loads_full_surface(loaded):
    meta = {e["id"]: e for e in loaded.meta}.get(PLUGIN)
    assert meta and meta["loaded"], "synced prototrader-finance did not load"

    names = {t.name for t in loaded.tools}
    assert EXPECTED_TOOLS <= names, f"missing tools: {EXPECTED_TOOLS - names}"

    assert {s.name for s in loaded.subagents} == DESK
    assert loaded.routers, "no dashboard router registered"
    assert "dashboard" in {v["id"] for v in meta["views"]}

    assert any(str(d).endswith(f"{PLUGIN}/skills") for d in loaded.skill_dirs)
    assert any(str(d).endswith(f"{PLUGIN}/workflows") for d in loaded.workflow_dirs)


@needs_install
def test_installed_desk_subagents_have_tools(loaded):
    subs = {s.name: s for s in loaded.subagents}
    assert "backtest_strategy" in subs["quant"].tools
    assert "stock_quote" in subs["market-analyst"].tools


@needs_install
def test_installed_workflows_reference_desk_subagents():
    for name in ("quant-desk", "investment-committee"):
        wf = yaml.safe_load((PLUGIN_DIR / "workflows" / f"{name}.yaml").read_text())
        assert wf["name"] == name and wf["inputs"] and wf["steps"]
        for s in wf["steps"]:
            assert s["subagent"] in DESK, f"{name}/{s['id']} → unknown subagent {s['subagent']!r}"


@needs_install
async def test_installed_dashboard_route_serves(loaded):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    for r in loaded.routers:  # {plugin_id, router, prefix} with prefix baked in
        app.include_router(r["router"], prefix=r["prefix"])
    client = TestClient(app)

    page = client.get(f"/plugins/{PLUGIN}/dashboard")
    assert page.status_code == 200 and "Quant Desk" in page.text

    strat = client.get(f"/plugins/{PLUGIN}/api/strategies")
    assert strat.status_code == 200 and "ma_cross" in strat.json()["strategies"]

    bad = client.get(f"/plugins/{PLUGIN}/api/backtest?strategy=nope")  # degrades, no 500
    assert bad.status_code == 200 and bad.json()["ok"] is False
