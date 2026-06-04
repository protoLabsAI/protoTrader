"""Offline tests for the paper broker (Slice 6) — gate, limits, fill math.

No network: we drive the engine directly with explicit prices. The HITL approval
gate and live quotes live in tools.py and are exercised separately (live).
"""

from __future__ import annotations

import importlib.util


def _engine(tmp_path, monkeypatch):
    import sys
    spec = importlib.util.spec_from_file_location(
        "brk_engine", "plugins/broker/engine.py",
        submodule_search_locations=["plugins/broker"],
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["brk_engine"] = m  # dataclasses resolve cls.__module__ here
    spec.loader.exec_module(m)
    # Redirect all broker files into a temp config dir.
    monkeypatch.setattr(m, "_config_dir", lambda: tmp_path)
    return m


def _armed(m, **over):
    kw = dict(enabled=True, mode="paper", starting_cash=100_000.0,
              max_order_usd=50_000.0, max_position_pct=100.0,
              max_gross_exposure_pct=100.0, daily_order_cap=10)
    kw.update(over)
    return m.Mandate(**kw)


def test_disabled_by_default(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    ok, why = m.Mandate().gate()  # no mandate file → disabled
    assert ok is False and "DISABLED" in why


def test_live_mode_refused(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    ok, why = _armed(m, mode="live").gate()
    assert ok is False and "paper-only" in why


def test_killswitch_halts(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    (tmp_path / "TRADING_HALT").write_text("halt")
    ok, why = _armed(m).gate()
    assert ok is False and "KILL-SWITCH" in why


def test_buy_then_sell_pnl_and_cash(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m))
    ok, _ = b.validate("AAPL", "buy", 100, 180.0)
    assert ok
    b.fill("AAPL", "buy", 100, 180.0, "market")
    assert b.state.positions["AAPL"]["qty"] == 100
    assert b.state.cash < 100_000  # paid ~18k + friction
    # Sell into a higher price → positive realized, flat after.
    b.fill("AAPL", "sell", 100, 200.0, "market")
    assert "AAPL" not in b.state.positions
    assert b.state.realized_pnl > 0
    # Round-trip net of frictions should be close to (200-180)*100 = 2000.
    assert 1900 < b.state.realized_pnl < 2000


def test_per_order_cap(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m, max_order_usd=1000.0))
    ok, why = b.validate("AAPL", "buy", 100, 180.0)  # $18k > $1k
    assert ok is False and "per-order cap" in why


def test_concentration_cap(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m, max_position_pct=10.0))
    ok, why = b.validate("AAPL", "buy", 100, 180.0)  # $18k = 18% > 10%
    assert ok is False and "per-name cap" in why


def test_universe_allowlist(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m, universe=["SPY", "QQQ"]))
    ok, why = b.validate("AAPL", "buy", 1, 180.0)
    assert ok is False and "universe" in why


def test_no_naked_short(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m))
    ok, why = b.validate("AAPL", "sell", 10, 180.0)  # nothing held
    assert ok is False and "long-only" in why


def test_daily_cap(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m, daily_order_cap=1))
    b.fill("AAPL", "buy", 1, 180.0, "market")  # uses the 1 allowed
    ok, why = b.validate("AAPL", "buy", 1, 180.0)
    assert ok is False and "daily order cap" in why


def test_state_persists(tmp_path, monkeypatch):
    m = _engine(tmp_path, monkeypatch)
    b = m.PaperBroker(_armed(m))
    b.fill("AAPL", "buy", 10, 180.0, "market")
    b2 = m.PaperBroker(_armed(m))  # reload from disk
    assert b2.state.positions["AAPL"]["qty"] == 10
    # Audit ledger was written.
    assert (tmp_path / "broker_audit.jsonl").exists()
