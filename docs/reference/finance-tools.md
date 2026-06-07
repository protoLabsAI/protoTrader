# Finance tools

protoTrader's **finance domain layer** — the tools the fork adds on top of the
[starter tools](/reference/starter-tools). They ship as **one full-bundle plugin**,
`plugins/prototrader-finance` (the plugin-devkit pattern) — tools + the research
desk subagents + the `quant-desk` / `investment-committee` workflows + finance
skills + a Quant Desk dashboard console view, in a single self-contained directory.
Disable it with `plugins.disabled: [prototrader-finance]`; it edits no upstream
file, so it survives re-syncs from protoAgent, and it installs into any protoAgent
via `plugin install <git-url>` (ADR 0027).

All finance tools return a **human-readable string** (no raw JSON) and degrade
to a clear `Error: …` string rather than raising — the model reads the error and
recovers. The market-data, backtest, and factor tools need the finance extras
(`pip install -r requirements-finance.txt` → `yfinance`, `ccxt`; backtest/factors
also use `pandas`/`numpy`); without them the tool returns a one-line install hint.

| Plugin | Tools | Network | Side effects |
|---|---|---|---|
| `finance-data` | `stock_quote`, `stock_price_history`, `stock_fundamentals`, `crypto_quote`, `crypto_price_history` | yes (yfinance / ccxt) | none (read-only) |
| `backtest` | `backtest_strategy`, `list_strategies` | yes (for data) | none (simulation) |
| `factors` | `factor_eval`, `factor_zoo` | yes (yfinance) | none (read-only) |
| `behavioral` | `analyze_trade_journal` | no | none (analysis only) |
| `broker` | `broker_account`, `broker_place_order`, `broker_orders` | for quotes | **writes** paper state + audit |

> **Not advice.** Every analytical tool appends a disclaimer — these are research
> and analysis tools, not investment advice. The broker is **paper-only and
> gated** (see [`broker_place_order`](#broker-place-order)).

## finance-data

### `stock_quote`

```python
@tool
async def stock_quote(symbol: str) -> str
```

Current quote + key stats for a US stock/ETF (via `yfinance`). `symbol` is a
ticker (`"NVDA"`, `"SPY"`).

```
**NVDA** — $X.XX (+Y% vs prev close)
day range: $lo–$hi | 52w range: $lo–$hi
market cap: $… | volume: …
```

Unknown ticker → `"Error: no quote for 'XYZ' (unknown ticker, or data source down)."`

### `stock_price_history`

```python
@tool
async def stock_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> str
```

OHLCV history with a compact summary (charting / backtest context). `period` ∈
`1d,5d,1mo,3mo,6mo,1y,2y,5y,ytd,max`; `interval` ∈ `1d,1wk,1mo` (+ intraday
`1m`…`1h`). Returns `N bars`, total return, high/low, and the last 5 bars.

### `stock_fundamentals`

```python
@tool
async def stock_fundamentals(symbol: str) -> str
```

Sector / industry, valuation (P/E ttm, fwd P/E, P/B), margins, revenue growth,
52-week range, beta.

### `crypto_quote`

```python
@tool
async def crypto_quote(symbol: str, exchange: str = "okx") -> str
```

Current ticker for a crypto pair from a **public, no-auth** exchange (via
`ccxt`). `symbol` is a pair (`"BTC/USDT"`, `"ETH/USDT"`); `exchange` is any ccxt
id. Returns last price, 24h change, bid/ask, 24h high/low, volume.

### `crypto_price_history`

```python
@tool
async def crypto_price_history(symbol: str, timeframe: str = "1d", limit: int = 90, exchange: str = "okx") -> str
```

OHLCV history for a crypto pair. `timeframe` ∈ `1m,5m,15m,1h,4h,1d,1w`; `limit`
≤ ~1000. Same compact summary shape as the equity history tool.

## backtest

### `backtest_strategy`

```python
@tool
async def backtest_strategy(
    symbol: str, strategy: str = "ma_cross", params: dict | None = None,
    period: str = "2y", interval: str = "1d",
    cost_bps: float = 5.0, slippage_bps: float = 2.0,
) -> str
```

Vectorized backtest of a canonical strategy on an equity ticker or crypto pair,
with realistic costs, an in-sample/out-of-sample split, a buy-and-hold benchmark,
and a bootstrap Sharpe CI. `strategy` ∈ `ma_cross`, `rsi_meanrev`, `breakout`,
`buy_hold` (see [`list_strategies`](#list-strategies) for params).

Returns a markdown table — total return / CAGR / Sharpe / Sortino / max drawdown
/ trades / exposure for **strategy vs buy-and-hold** — plus the overfit gap
(IS→OOS Sharpe) and the bootstrap CI (`Sharpe 90% CI [lo, hi]`, `P(Sharpe>0)`),
and a one-line "beat / trailed buy-and-hold" read.

> A pretty Sharpe on a handful of trades is not a signal — the OOS split and
> bootstrap CI are there to surface curve-fitting.

### `list_strategies`

```python
@tool
async def list_strategies() -> str
```

Lists the backtest strategies and their tunable params (no network): `ma_cross`
(fast 20 / slow 50), `rsi_meanrev` (period 14, oversold 30, overbought 55),
`breakout` (lookback 20), `buy_hold`.

## factors

### `factor_eval`

```python
@tool
async def factor_eval(factor: str, universe: list[str] | None = None, period: str = "3y") -> str
```

Evaluate **one** factor by Information Coefficient over a universe. `factor` ∈
`momentum_12_1`, `reversal_1m`, `low_vol`, `trend_200d`, `volume_trend`.
`universe` defaults to a 20-name large-cap set. Reports mean IC, rank IC, IR, hit
rate, and a verdict — `alive` / `weak` / `reversed` / `dead`.

### `factor_zoo`

```python
@tool
async def factor_zoo(universe: list[str] | None = None, period: str = "3y") -> str
```

Scores **all** bundled factors over a universe and ranks them by |IR|, strongest
first. Same per-factor stats + verdict as `factor_eval`. IC is sample/regime
specific — a factor alive in one regime can be dead in another.

## behavioral

### `analyze_trade_journal`

```python
@tool
async def analyze_trade_journal(csv_text: str) -> str
```

The **Shadow Account** — parse a trade-journal CSV into a behavioral profile and
bias flags. No network. `csv_text` is the file contents; columns are matched
tolerantly (`symbol`/`ticker`, `side`/`action`, `qty`/`shares`, `price`/`fill`,
`date`/`datetime`, with spacing/hyphen normalization — e.g. `Fill Price`,
`Trade Date`). Round-trips are paired FIFO (longs and shorts separately).

Returns win rate, total/realized P&L, profit factor, expectancy, avg win/loss,
avg hold for wins vs losses, largest win/loss, max cumulative-P&L drawdown — then
**behavioral flags**: *loss aversion* (holding losers longer than winners),
*asymmetric losers* (avg loss ≫ avg win), *revenge sizing* (oversized trades
right after a loss), *cutting winners early*, and *negative edge* (profit
factor < 1).

## broker (gated paper execution)

The broker is **paper-only** and **off by default**. It refuses to do anything
until a mandate is armed in `config/broker_mandate.yaml`
(copy `plugins/prototrader-finance/broker/broker_mandate.example.yaml`); `mode: live` is deliberately
refused, and a `config/TRADING_HALT` file is an instant kill-switch.

### `broker_account`

```python
@tool
async def broker_account() -> str
```

Read-only. Shows armed/halted status, cash, equity + gross exposure, realized
P&L, open positions (with unrealized P&L), and the active mandate limits. With no
mandate file: `🔴 OFF — no mandate`.

### `broker_place_order` {#broker-place-order}

```python
@tool
async def broker_place_order(
    symbol: str, side: str, qty: float,
    order_type: str = "market", limit_price: float | None = None,
) -> str
```

Place a **paper** order — gated through a non-negotiable chain:

1. **Mandate gate** — refuses unless `enabled: true`, `mode: paper`, and no
   kill-switch file. With no mandate: `🔴 Order refused — trading is DISABLED`.
2. **Per-order validation** — universe, daily order cap, per-order notional cap,
   per-name %, gross exposure %, sufficient cash (buys), existing position
   (sells; long-only v1). Failure → `🔴 Order rejected by mandate — <reason>`.
3. **Human approval** — when `require_approval: true`, the tool issues a
   LangGraph `interrupt()`: the A2A task goes to `input-required` carrying the
   order preview and **pauses** until the operator replies `APPROVE` (anything
   else cancels). Lead-agent only.
4. **Simulated fill** — applies slippage (5 bps) + commission (1 bps/side),
   updates cash/positions/realized-P&L, persists `config/broker_paper.json`, and
   appends to `config/broker_audit.jsonl`.

> **Side effects:** steps 1–2 may append a rejection to the audit log; step 4
> mutates paper state **and** the audit log. The approval interrupt means an
> armed order leaves the task `input-required` until answered — the eval suite's
> [`fin_broker_gating`](/guides/the-desk#evals) case asserts the *refusal* path
> (mandate off) precisely so it completes without that pause.

### `broker_orders`

```python
@tool
async def broker_orders(limit: int = 20) -> str
```

Recent paper orders (fills, newest first) from the audit trail, or
`"No orders yet."`.

## Related

- [The desk](/guides/the-desk) — the `market-analyst` / `quant` / `risk-manager`
  subagents and the `quant-desk` / `investment-committee` workflows that compose
  these tools
- [Starter tools](/reference/starter-tools) — the inherited substrate tools
  (`web_search`, `memory_*`, `calculator`, …) these build on
- [Configure subagents](/guides/subagents) · [Reusable workflows](/guides/workflows) — the generic mechanics
- [Plugins](/guides/plugins) — how each finance plugin registers its tools
