import pandas as pd

def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / (s.std(ddof=0) + 1e-12)

def rank_stocks(factors: pd.DataFrame) -> pd.DataFrame:
    df = factors.copy()

    # 做成“同一尺度”：z分数
    z_mom3 = zscore(df["mom_3m"])
    z_mom12 = zscore(df["mom_12m"])
    z_vol = zscore(df["vol_3m"])
    z_dd = zscore(df["dd_12m"])

    # 规则：涨得多加分，波动/回撤扣分
    df["score"] = (
        0.35 * z_mom3 +
        0.45 * z_mom12 -
        0.10 * z_vol +
        # 回撤越小（越接近0）越好，这里应当加分
        0.10 * z_dd
    )

    # 附加：把风险指标也保留，方便你肉眼判断
    out = df.sort_values("score", ascending=False)
    return out
