"""The prototrader-finance plugin loads as ONE full bundle (the plugin-devkit pattern).

Verifies the consolidation: the six former finance plugins + two global workflows
are now a single self-contained plugin contributing tools + subagents + a console
view + bundled skills/ + workflows/, and the old plugin dirs are gone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from graph.config import LangGraphConfig
from graph.plugins.loader import load_plugins

PLUGIN = "prototrader-finance"
ROOT = Path(__file__).parent.parent

# The 13 finance tools the bundle registers (market data → backtest → factors →
# behavioral → gated paper broker).
EXPECTED_TOOLS = {
    "stock_quote", "stock_price_history", "stock_fundamentals",
    "crypto_quote", "crypto_price_history",
    "backtest_strategy", "list_strategies",
    "factor_eval", "factor_zoo",
    "analyze_trade_journal",
    "broker_place_order", "broker_orders", "broker_account",
}
DESK = {"market-analyst", "quant", "risk-manager"}


@pytest.fixture
def loaded():
    cfg = LangGraphConfig()
    cfg.plugins_enabled = [PLUGIN]
    # isolate from other default-on plugins (discord) so counts are about us
    cfg.plugins_disabled = ["discord", "google", "coding_agent", "delegates", "plugin-devkit", "hello"]
    return load_plugins(cfg)


def test_bundle_loads_with_every_surface(loaded):
    meta = {e["id"]: e for e in loaded.meta}.get(PLUGIN)
    assert meta and meta["loaded"], "prototrader-finance did not load"

    names = {t.name for t in loaded.tools}
    assert EXPECTED_TOOLS <= names, f"missing tools: {EXPECTED_TOOLS - names}"

    assert {s.name for s in loaded.subagents} == DESK
    assert loaded.routers, "no dashboard router registered"

    # console view declared (ADR 0026)
    view_ids = {v["id"] for v in meta["views"]}
    assert "dashboard" in view_ids
    assert meta["views"][0]["path"] == "/plugins/prototrader-finance/dashboard"

    # full-bundle auto-discovery (ADR 0027): skills/ + workflows/ subdirs
    assert any(str(d).endswith(f"{PLUGIN}/skills") for d in loaded.skill_dirs)
    assert any(str(d).endswith(f"{PLUGIN}/workflows") for d in loaded.workflow_dirs)


def test_workflows_and_skills_are_bundled_in_the_plugin():
    wf = {p.stem for p in (ROOT / "plugins" / PLUGIN / "workflows").glob("*.yaml")}
    assert {"quant-desk", "investment-committee"} <= wf
    skills = {p.name for p in (ROOT / "plugins" / PLUGIN / "skills").iterdir() if p.is_dir()}
    assert {"research-a-ticker", "backtest-a-strategy", "place-a-paper-trade"} <= skills
    # …and no longer in the global dirs (moved, not copied)
    assert not (ROOT / "workflows" / "quant-desk.yaml").exists()


def test_old_finance_plugins_are_gone():
    for old in ("finance-data", "backtest", "factors", "behavioral", "broker", "finance-desk"):
        assert not (ROOT / "plugins" / old).exists(), f"stale plugin dir plugins/{old}"


async def test_dashboard_router_serves_page_and_api(loaded):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    for r in loaded.routers:  # each is {plugin_id, router, prefix} with prefix baked in
        app.include_router(r["router"], prefix=r["prefix"])
    client = TestClient(app)

    page = client.get("/plugins/prototrader-finance/dashboard")
    assert page.status_code == 200 and "Quant Desk" in page.text

    strat = client.get("/plugins/prototrader-finance/api/strategies")
    assert strat.status_code == 200 and "ma_cross" in strat.json()["strategies"]

    # bad strategy degrades cleanly (no 500), proving the error path
    bad = client.get("/plugins/prototrader-finance/api/backtest?strategy=nope")
    assert bad.status_code == 200 and bad.json()["ok"] is False
