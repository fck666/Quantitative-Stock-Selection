from __future__ import annotations
import time
from io import StringIO
from pathlib import Path
import pandas as pd
import yfinance as yf
import requests

from src.paths import RAW_DIR
RAW_DIR.mkdir(parents=True, exist_ok=True)

def download_ohlcv(tickers: list[str], start="2018-01-01", batch_size=10, retries=5) -> pd.DataFrame:
    all_parts: list[pd.DataFrame] = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"downloading {i+1}-{i+len(batch)} / {len(tickers)} ...")

        last_err = None
        for r in range(retries):
            try:
                df = yf.download(
                    tickers=batch,
                    start=start,
                    auto_adjust=True,
                    group_by="column",
                    threads=False,      # 关键：关并发，减少触发限速
                    progress=False,
                )
                if df is None or df.empty:
                    raise RuntimeError("empty dataframe")
                all_parts.append(df)
                break
            except Exception as e:
                last_err = e
                # 关键：限速时多等一会儿（1,2,4,8,16...秒不够，拉长）
                wait = min(60, 5 * (2 ** r))  # 5,10,20,40,60
                print(f"  retry {r+1}/{retries} after {wait}s because: {type(e).__name__}: {e}")
                time.sleep(wait)

        else:
            print(f"  SKIP batch {i+1}-{i+len(batch)} due to error: {last_err}")

        # 每批之间再停一下，进一步降低频率
        time.sleep(2)

    if not all_parts:
        raise RuntimeError("All batches failed; no data downloaded.")

    out = pd.concat(all_parts, axis=1)
    return out

def save_parquet(df: pd.DataFrame, name: str) -> Path:
    path = RAW_DIR / f"{name}.parquet"
    df.to_parquet(path)
    return path

def load_parquet(name: str) -> pd.DataFrame:
    path = RAW_DIR / f"{name}.parquet"
    return pd.read_parquet(path)

def download_ohlcv_stooq(tickers: list[str], start="2018-01-01", sleep=0.2) -> pd.DataFrame:
    """
    从 stooq 下载日线数据，返回与 yfinance 类似的结构：
    顶层列：Close/Volume（先够我们做MVP）
    二级列：ticker
    """
    frames = {}
    failed = []
    start_dt = pd.to_datetime(start)

    for i, tk in enumerate(tickers, 1):
        try:
            # stooq 美股格式：{ticker}.us
            url = f"https://stooq.com/q/d/l/?s={tk.lower()}.us&i=d"
            r = requests.get(url, timeout=30)
            r.raise_for_status()

            df = pd.read_csv(StringIO(r.text))
            if df.empty or "Date" not in df.columns:
                raise RuntimeError("empty/invalid csv")

            df["Date"] = pd.to_datetime(df["Date"])
            df = df[df["Date"] >= start_dt].set_index("Date").sort_index()

            # 有些票 stooq 可能缺数据/退市，跳过即可
            if "Close" not in df.columns or df["Close"].dropna().empty:
                raise RuntimeError("no close data")

            frames[tk] = df
        except Exception as e:
            failed.append((tk, f"{type(e).__name__}: {e}"))
            print(f"  skip {tk}: {type(e).__name__}: {e}")

        time.sleep(sleep)

    if not frames:
        raise RuntimeError("stooq: no data downloaded")

    if failed:
        from pathlib import Path
        Path("output").mkdir(exist_ok=True)
        with open("output/failed_tickers.txt", "w", encoding="utf-8") as f:
            for tk, msg in failed:
                f.write(f"{tk}\t{msg}\n")

    close = pd.concat({k: v["Close"] for k, v in frames.items()}, axis=1)
    vol = pd.concat({k: v["Volume"] for k, v in frames.items() if "Volume" in v.columns}, axis=1)

    out = pd.concat({"Close": close, "Volume": vol}, axis=1)
    return out
