from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any
import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252
TRADING_DAYS_1M = 21
TRADING_DAYS_3M = 63


@dataclass
class TimeseriesStats:
    return_1m: float | None
    return_3m: float | None
    return_1y: float | None
    annual_vol: float | None
    max_drawdown: float | None
    ma5: float | None
    ma20: float | None
    ma60: float | None


def _compute_return(close: pd.Series, periods: int) -> float | None:
    if len(close) <= periods or close.iloc[-periods:].isna().any():
        return None
    try:
        return float(close.iloc[-1] / close.iloc[-periods] - 1.0)
    except Exception:
        return None


def _compute_drawdown(close: pd.Series) -> float | None:
    if close.empty:
        return None
    cum_max = close.cummax()
    dd = close / cum_max - 1.0
    if dd.empty:
        return None
    return float(dd.min())


def analyze_timeseries(df: pd.DataFrame, ticker: str) -> Dict[str, Any]:
    """
    计算常用指标，返回 JSON 可序列化的结构：
    - stats: 1M/3M/1Y 收益、年化波动、最大回撤、MA5/20/60
    - series: 可选绘图数据（日期、收盘价、均线）
    """
    if "Close" not in df.columns:
        raise ValueError("DataFrame must contain 'Close' column")

    close = df["Close"].dropna()
    returns = close.pct_change(fill_method=None)

    stats = TimeseriesStats(
        return_1m=_compute_return(close, TRADING_DAYS_1M),
        return_3m=_compute_return(close, TRADING_DAYS_3M),
        return_1y=_compute_return(close, TRADING_DAYS_PER_YEAR),
        annual_vol=float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if not returns.empty else None,
        max_drawdown=_compute_drawdown(close),
        ma5=float(close.rolling(5).mean().iloc[-1]) if len(close) >= 5 else None,
        ma20=float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None,
        ma60=float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None,
    )

    # 生成简洁的图表数据（末尾 180 个交易日）
    tail = df.tail(180).copy()
    tail["ma5"] = tail["Close"].rolling(5).mean()
    tail["ma20"] = tail["Close"].rolling(20).mean()
    tail["ma60"] = tail["Close"].rolling(60).mean()

    series: List[Dict[str, Any]] = []
    for idx, row in tail.iterrows():
        series.append({
            "date": idx.date().isoformat() if hasattr(idx, "date") else str(idx),
            "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
            "ma5": float(row["ma5"]) if pd.notna(row["ma5"]) else None,
            "ma20": float(row["ma20"]) if pd.notna(row["ma20"]) else None,
            "ma60": float(row["ma60"]) if pd.notna(row["ma60"]) else None,
            "volume": float(row["Volume"]) if "Volume" in tail.columns and pd.notna(row["Volume"]) else None,
        })

    return {
        "ticker": ticker,
        "stats": stats.__dict__,
        "latest": {
            "date": close.index[-1].date().isoformat() if hasattr(close.index[-1], "date") else str(close.index[-1]),
            "close": float(close.iloc[-1]),
        } if not close.empty else {},
        "series": series,
    }