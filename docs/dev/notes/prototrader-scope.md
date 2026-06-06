# protoTrader — scope & build plan

**Goal:** reimagine **[HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading)**
— an open-source natural-language trading *research* workspace — on the
**protoAgent paradigm** (A2A 1.0 agent on LangGraph). Research-primary; execution
is an optional, gated, last slice.

The win: protoAgent already *is* the engine Vibe-Trading hand-built. We inherit it
for free and add only the **finance domain layer**.

> **Built reference** (what shipped): [Finance tools](../../reference/finance-tools.md)
> (the 15 tools) and [The desk](../../guides/the-desk.md) (subagents + workflows).
> This doc is the *plan*; those are the *as-built* docs.

## What we inherit from protoAgent (do NOT rebuild)

| Vibe-Trading built… | protoAgent already provides |
|---|---|
| ReAct loop + tool-calling | LangGraph agent (`graph/agent.py`) |
| 5-layer context compression | compaction middleware |
| persistent cross-session memory + FTS5 search | `KnowledgeStore` (sqlite + FTS5) + memory tools, hot-facts |
| auto-discovered tools registry (31+) | `tools/` + **plugins** (`register_tools`) |
| skills system w/ CRUD, loadable | `SKILL.md` skills (disk + agent-emitted, self-improving, retrieved by KnowledgeMiddleware) |
| MCP server exposing 36 tools | MCP client + `register_mcp_server`; agent tools are MCP-exposable |
| swarm DAG multi-agent orchestration | **declarative workflows** (ADR 0002) over **subagents** |
| agent roles (researcher / quant / risk / trader) | **subagents** (`register_subagent` / `graph/subagents/`) |
| React chat + live activity rail + SSE | React operator console + A2A streaming + reactive **Activity thread** (ADR 0003) |
| FastAPI run/session/stream API | `server.py` + A2A 1.0 endpoints |
| gated broker connector: mandate, kill-switch, audit, HITL | HITL (`ask_human` / `request_user_input`) + **enforcement gate** + **egress allowlist** (ADR 0008) + **filesystem fence** (ADR 0007) + JSONL audit log |
| LLM provider abstraction (13+) | the protoLabs gateway via `graph/llm.py` (one alias, many models) |

**Net:** ~60% of Vibe-Trading is substrate we already have. We build the finance
**content** on top — as plugins (tools + managed data servers), skills, subagents,
and workflows — with **no core edits** (the whole point of the plugin reach,
ADR 0018/0019).

## What's net-new — the finance domain layer (the slices)

Each slice is a vertical that's useful on its own. Built as plugins/skills/
subagents/workflows so it ships without touching core.

- **Slice 1 — Market data + ticker research (MVP).**
  A `finance-data` plugin: price/OHLCV + fundamentals + news tools over a no-auth
  fallback chain (yfinance, CCXT/OKX public, AKShare) — mirroring Vibe-Trading's
  loader registry. A `research` finance subagent. 2–3 finance `SKILL.md`s
  (technical read, fundamental read, "research a ticker"). Persona already wired.
  Demo: *"Research NVDA — what's the setup, the bull/bear, the key levels?"*

- **Slice 2 — Backtesting.**
  A `backtest` tool (a `backtesting.py`-style engine) + a "strategy from prompt"
  skill. Point-in-time data, realistic costs/slippage, OOS split. Reports
  return / Sharpe / max-DD / win-rate / # trades / Monte-Carlo CI. Strategy export
  (Pine/TDX/MQL5) is a later add.

- **Slice 3 — The desk (multi-role).**
  `quant`, `risk`, (paper) `trader` subagents + the first **workflow presets** as
  declarative YAML DAGs: *investment committee* (bull/bear debate → risk → PM
  sign-off) and *quant desk* (screen → factor → backtest → audit). This is where
  protoAgent's workflow+subagent reach directly replaces Vibe-Trading's swarm.

- **Slice 4 — Factors / Alpha Zoo.**
  A curated alpha pack (start with a usable subset of the 158/101/191/academic
  zoos) + a factor-eval tool (IC / IR / alive-reversed-dead). Ships as a data pack
  + tool, not 452 alphas day one.

- **Slice 5 — Behavioral / Shadow Account.**
  Trade-journal ingest (CSV + common broker exports) → behavioral profile → rule
  extraction → Shadow-Account backtest (actual vs rule-based) → bias/break report.
  Leans on the existing file-read + memory + backtest pieces.

- **Slice 6 — Gated execution (LAST, opt-in, off by default).**
  A `broker` plugin: **paper-trading first**, then bounded live via a connector
  (e.g. Alpaca/IBKR). Mandate (symbol universe, size, exposure, leverage, daily
  cap) + per-order HITL approval + filesystem kill-switch + enforcement-gate hard
  limits + audit ledger. No custody; the broker holds funds. This is the one slice
  that touches real risk — it gets the most safety scaffolding and the slowest roll.

## Decisions / conventions

- **Private repo.** A trading agent touches strategy + credentials.
- **Data sources:** default to the no-auth fallback chain; optional Pro tokens
  (Tushare/Futu/broker keys) via plugin config/secrets (ADR 0019), never committed.
- **Internal name stays `protoagent`** (logger/env/paths); the agent's name is
  `identity.name = protoTrader`. Fixes flow down from `upstream` (protoAgent) via
  normal merges (history-preserving fork).
- **No autonomous trading.** Research-primary; execution gated behind Slice 6.

## Status

- ✅ Fork created (private, history-preserving), identity + persona + this scope doc.
- ✅ **Slice 1 — market data + ticker research.** `finance-data` plugin: 5 no-auth
  tools (`stock_quote` / `stock_price_history` / `stock_fundamentals` via yfinance;
  `crypto_quote` / `crypto_price_history` via ccxt). `research-a-ticker` skill drives
  the methodology. Live-verified: protoTrader researches a ticker end-to-end with
  real data + a structured read. (Also fixed a plugin-system gap surfaced here:
  the loader now supports **multi-module plugins** with relative imports —
  hyphenated id sanitized + module registered in `sys.modules` pre-exec. Needs
  upstreaming to protoAgent.)
- ✅ **Slice 2 — backtesting.** `backtest` plugin: vectorized engine (MA cross /
  RSI mean-rev / breakout / buy-hold) over fetched OHLCV, no look-ahead, realistic
  costs/slippage, OOS split, buy-and-hold benchmark, bootstrap Sharpe CI.
  `backtest-a-strategy` skill. Offline tests + live-verified (honest "trailed
  buy-and-hold" reads).
- ✅ **Slice 3 — the desk.** `finance-desk` plugin: 3 subagents (market-analyst,
  quant, risk-manager) + 2 workflow presets (investment-committee, quant-desk).
  Live-verified (lead → quant subagent backtest delegation).
- ✅ **Slice 4 — factors / Alpha Zoo.** `factors` plugin: cross-sectional IC /
  rank-IC / IR with sign-standardized alive/weak/reversed/dead verdicts over a
  factor zoo. `evaluate-a-factor` skill. Offline tests + live ("low_vol reversed").
- ✅ **Slice 5 — behavioral / Shadow Account.** `behavioral` plugin:
  `analyze_trade_journal` → FIFO round-trips → bias flags (loss aversion,
  asymmetric losers, negative edge, revenge sizing, cutting winners early).
  `shadow-account` skill. Offline tests.
- ✅ **Slice 6 — gated paper execution.** `broker` plugin: paper-only execution
  behind the full safety stack — mandate (master switch + per-order/exposure/daily
  limits, **OFF by default**) → filesystem kill-switch → **per-order human approval**
  (LangGraph `interrupt`, surfaces as `input-required`) → simulated fill at a live
  quote (+ friction) → append-only audit ledger. `mode: live` is deliberately not
  implemented (cannot move real money). `place-a-paper-trade` skill. Offline tests
  (gate, every limit, fill math, persistence) + live-verified (OFF→ARMED, kill-switch).
- ⬜ Upstream the loader multi-module fix to the protoAgent template; cut the
  first protoTrader release with Discord notes covering everything since the fork.

## Execution note (per operator: live execution IS a goal)

Markets for Slice 1: **US equities/ETFs + crypto**. Live order placement is an
intended eventual capability (Slice 6) — built **paper-first**, with the full gated
stack (mandate, per-order HITL, kill-switch, enforcement limits, audit), rolled
slowest. Research stays primary; nothing trades until Slice 6 is explicitly enabled.
