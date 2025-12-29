import pandas as pd
import requests

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

def get_sp500_tickers() -> list[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    r = requests.get(WIKI_SP500, headers=headers, timeout=30)
    r.raise_for_status()

    from io import StringIO
    tables = pd.read_html(StringIO(r.text))
    df = tables[0]

    tickers = df["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist()
    return tickers
