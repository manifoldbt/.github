"""The data behind the profile hero: one real parameter sweep, nothing drawn by hand.

    pip install "manifoldbt[pandas]"
    python hero_surface.py surface.json
"""
import json
import sys

import manifoldbt as mbt
from manifoldbt.helpers import Interval, Slippage, time_range
from manifoldbt.indicators import close, ema

FAST = list(range(5, 50, 3))     # 15 values
SLOW = list(range(60, 270, 14))  # 15 values

store = mbt.ingest(provider="binance", symbol="BTCUSDT", symbol_id=1, interval="1h",
                   start="2023-01-01T00:00:00Z", end="2025-01-01T00:00:00Z")

fast = ema(close, mbt.param("fast"))
slow = ema(close, mbt.param("slow"))
strategy = (
    mbt.Strategy.create("ema_grid")
    .signal("fast", fast)
    .signal("slow", slow)
    .size(mbt.when(fast > slow, 0.5, -0.5))
)

start, end = time_range("2023-01-01", "2025-01-01")
config = mbt.BacktestConfig(
    universe=[1], time_range_start=start, time_range_end=end,
    bar_interval=Interval.hours(1), initial_capital=10_000, warmup_bars=256,
    execution=mbt.ExecutionConfig(allow_short=True),
    fees=mbt.FeeConfig.binance_perps(),
    slippage=Slippage.fixed_bps(2),
)

sweep = mbt.run_sweep(strategy, {"fast": FAST, "slow": SLOW}, config, store)
surface = sweep.to_df(backend="pandas").pivot(
    index="param_fast", columns="param_slow", values="sharpe")

json.dump({
    "manifoldbt": mbt.__version__,
    "fast": FAST,
    "slow": SLOW,
    "sharpe": [[round(float(surface.loc[f, s]), 4) for s in SLOW] for f in FAST],
}, open(sys.argv[1], "w"))
print(surface.round(2).to_string())
