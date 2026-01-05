from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException

from src.analysis import analyze_timeseries
from src.data import fetch_single_ticker
from src.paths import RAW_DIR, DEFAULT_TICKER_START, SINGLE_TICKER_CACHE_TTL_HOURS


app = FastAPI(title="Quantitative Stock Selection API")


def _cache_path(symbol: str) -> Path:
    return RAW_DIR / f"{symbol.upper()}_ohlcv.parquet"


def _load_cached(symbol: str) -> pd.DataFrame | None:
    cache_file = _cache_path(symbol)
    if not cache_file.exists():
        return None

    modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
    if datetime.now() - modified_time > timedelta(hours=SINGLE_TICKER_CACHE_TTL_HOURS):
        return None

    try:
        return pd.read_parquet(cache_file)
    except Exception:
        return None


def _save_cache(df: pd.DataFrame, cache_file: Path) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_file)


@app.get("/ticker/{symbol}")
def get_single_ticker(symbol: str, start: str = DEFAULT_TICKER_START, force_refresh: bool = False):
    ticker = symbol.upper()
    cache_file = _cache_path(ticker)

    df = None
    if not force_refresh:
        df = _load_cached(ticker)

    cached = df is not None
    if df is None:
        df = fetch_single_ticker(ticker, start=start)
        _save_cache(df, cache_file)

    try:
        payload = analyze_timeseries(df, ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    payload["cached"] = cached
    payload["cache_path"] = str(cache_file)
    payload["cache_ttl_hours"] = SINGLE_TICKER_CACHE_TTL_HOURS
    return payload