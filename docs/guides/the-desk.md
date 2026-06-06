# The desk — finance subagents & workflows

protoTrader ships a small **research desk**: three specialist subagents and two
declarative workflows that compose them and the [finance
tools](/reference/finance-tools). They map Vibe-Trading's swarm roles onto the
protoAgent [subagent](/guides/subagents) + [workflow](/guides/workflows)
primitives — no swarm engine, just `register_subagent` + workflow YAML. Everything
lives in the `finance-desk` plugin and `workflows/*.yaml`; nothing edits an
upstream file, so it survives re-syncs from protoAgent.

Disable the whole desk with `plugins.disabled: [finance-desk]`.

## Subagents

The lead agent delegates to these via the `task` / `task_batch` tools (it never
exposes them as direct endpoints). Each has a scoped tool allowlist — the
research-and-cite contract enforced by which tools it can reach.

| Subagent | Role | Tools |
|---|---|---|
| **market-analyst** | One-instrument read: price/trend, fundamentals (equities), dated news/catalysts → a sourced, structured view (never buy/sell). | `stock_*`, `crypto_*`, `web_search`, `fetch_url`, `memory_*`, `current_time` |
| **quant** | Tests ideas empirically — backtests with realistic costs, reads the result honestly (beat buy-and-hold? OOS holds? CI clears 0? enough trades?). | `backtest_strategy`, `list_strategies`, `stock_price_history`, `crypto_price_history`, `web_search`, `memory_recall`, `current_time` |
| **risk-manager** | The skeptic — drawdown/tail, regime sensitivity, liquidity, concentration, position sizing. Finds what breaks the thesis. | `stock_price_history`, `crypto_price_history`, `stock_quote`, `backtest_strategy`, `calculator`, `memory_recall`, `current_time` |

Delegation is automatic — ask the lead an open-ended question and it routes:

```
"Get me a committee view on NVDA — bull, bear, and the key risks before I decide."
→ lead runs the investment-committee workflow (or task()s the subagents)
```

## Workflows

Declarative presets in `workflows/`. Invoke by name via the `run_workflow` tool,
the console Studio → Workflows panel, or `POST /api/workflows/{name}/run`.

### `investment-committee`

Debate an instrument/thesis from both sides, stress-test it, and return a
committee view with sizing/levels.

```
input:  subject  (e.g. "NVDA", "long SPY into year-end")
steps:  bull (market-analyst) + bear (market-analyst)
        -> risk (risk-manager) -> view (market-analyst)
output: the synthesized committee stance (constructive / neutral / cautious --
        not buy/sell), strongest side, key levels, sizing/stop, what changes it
```

### `quant-desk`

Take a trading idea from setup → backtest → risk review → a go/no-go call, with
the numbers.

```
input:  idea  (e.g. "RSI mean-reversion on AAPL", "20/50 MA cross on SPY")
steps:  setup (market-analyst) → test (quant) → risk (risk-manager)
        → audit (quant): GO / NO-GO / REFINE + why, in the numbers
output: the final desk call
```

## Skills

The lead also has finance **[skills](/guides/skills)** (`config/skills/`,
auto-retrieved SKILL.md) that shape how it runs the single-tool flows:
`research-a-ticker`, `backtest-a-strategy`, `evaluate-a-factor`, `shadow-account`
(behavioral journal), and `place-a-paper-trade` (the gated broker flow:
confirm armed → size against mandate → preview → operator approval → fill).

## Evals {#evals}

The desk and the finance tools are covered by the `finance` category in the
[eval harness](/guides/evals) (`evals/tasks.json`):

```bash
python -m evals.runner --category finance
```

Ten side-effect-verified cases — one per capability: live market data, backtest,
factor IC, the behavioral journal, **broker gating** (asserts the agent refuses
an unguarded order and never fakes a fill), desk delegation, and the `quant-desk`
workflow end-to-end. The broker case deliberately tests the *refusal* path
(mandate off) so it completes rather than parking on the approval `interrupt`.

## Related

- [Finance tools](/reference/finance-tools) — the tools these subagents call
- [Configure subagents](/guides/subagents) · [Reusable workflows](/guides/workflows) — the generic mechanics
- [Eval your fork](/guides/evals) — the harness behind the `finance` suite
