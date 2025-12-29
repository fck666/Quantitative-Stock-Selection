from pathlib import Path
from src.universe import get_sp500_tickers
from src.data import download_ohlcv, save_parquet, load_parquet, download_ohlcv_stooq
from src.factors import calc_factors
from src.rank import rank_stocks
from src.logger import get_logger
log = get_logger()


from src.paths import RAW_DIR, OUTPUT_DIR
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    tickers = get_sp500_tickers()
    log.info(f"tickers: {len(tickers)}")

    # 如果本地已经有缓存，优先用缓存（更快更稳）
    cache_name = "sp500_ohlcv"
    cache_path = RAW_DIR / "sp500_ohlcv.parquet"
    if cache_path.exists():
        log.info("loading cached data:", cache_path)
        px = load_parquet(cache_name)
    else:
        # px = download_ohlcv(tickers, start="2018-01-01", batch_size=50, retries=3)
        px = download_ohlcv_stooq(tickers, start="2018-01-01", sleep=0.2)
        save_parquet(px, cache_name)

    factors = calc_factors(px)
    ranked = rank_stocks(factors)

    top20 = ranked.head(20).copy()
    top20.to_csv(OUTPUT_DIR / "top20.csv")
    log.info("saved: output/top20.csv")

if __name__ == "__main__":
    main()
