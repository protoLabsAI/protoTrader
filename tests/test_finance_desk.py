"""Slice 3 — the desk: subagents register + workflow presets are valid and
reference real subagents."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


def _subagents_module():
    spec = importlib.util.spec_from_file_location(
        "finance_desk_sub", "plugins/finance-desk/subagents.py",
        submodule_search_locations=["plugins/finance-desk"],
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_three_desk_subagents_with_tools():
    m = _subagents_module()
    subs = {s.name: s for s in m.desk_subagents()}
    assert set(subs) == {"market-analyst", "quant", "risk-manager"}
    for s in subs.values():
        assert s.system_prompt.strip()
        assert s.tools  # each has a non-empty tool allowlist
    # the quant must be able to backtest; the analyst must reach the data tools
    assert "backtest_strategy" in subs["quant"].tools
    assert "stock_quote" in subs["market-analyst"].tools


def test_workflow_presets_valid_and_reference_desk_subagents():
    desk = {"market-analyst", "quant", "risk-manager"}
    for name in ("investment-committee", "quant-desk"):
        wf = yaml.safe_load(Path(f"workflows/{name}.yaml").read_text())
        assert wf["name"] == name
        assert wf["inputs"] and wf["steps"]
        step_ids = {s["id"] for s in wf["steps"]}
        for s in wf["steps"]:
            assert s["subagent"] in desk, f"{name}/{s['id']} → unknown subagent {s['subagent']!r}"
            for dep in s.get("depends_on", []):
                assert dep in step_ids, f"{name}/{s['id']} depends on missing step {dep!r}"
        assert "{{steps." in wf["output"]  # output wires a step
