import argparse
import json

from src.analysis import analyze_timeseries
from src.data import fetch_single_ticker
from src.paths import DEFAULT_TICKER_START


def main():
    parser = argparse.ArgumentParser(description="Fetch and analyze a single ticker.")
    parser.add_argument("symbol", help="Ticker symbol, e.g. AAPL")
    parser.add_argument(
        "--start",
        default=DEFAULT_TICKER_START,
        help=f"Start date for history (default: {DEFAULT_TICKER_START})",
    )
    args = parser.parse_args()

    ticker = args.symbol.upper()
    df = fetch_single_ticker(ticker, start=args.start)
    result = analyze_timeseries(df, ticker)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()