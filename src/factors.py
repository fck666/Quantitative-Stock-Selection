import numpy as np
import pandas as pd

def _get_close(df: pd.DataFrame) -> pd.DataFrame:
    # yfinance返回的结构里 Close 在顶层列
    close = df["Close"].copy()
    close = close.dropna(axis=1, how="all")
    return close

def calc_factors(price_df: pd.DataFrame) -> pd.DataFrame:
    close = _get_close(price_df)

    # 日收益
    ret = close.pct_change()

    # 近3个月≈63交易日，近12个月≈252交易日
    m3 = 63
    y1 = 252

    mom_3m = close.pct_change(m3)
    mom_12m = close.pct_change(y1)

    vol_3m = ret.rolling(m3).std() * np.sqrt(252)  # 年化波动
    # 最大回撤：用滚动窗口的高点计算
    rolling_max = close.rolling(y1).max()
    dd_12m = close / rolling_max - 1.0  # 回撤是负数，越接近0越好

    factors = pd.DataFrame({
        "mom_3m": mom_3m.iloc[-1],
        "mom_12m": mom_12m.iloc[-1],
        "vol_3m": vol_3m.iloc[-1],
        "dd_12m": dd_12m.iloc[-1],
    })

    # 清理：去掉缺失多的
    factors = factors.dropna()
    return factors
