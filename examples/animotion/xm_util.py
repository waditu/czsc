# -*- coding: utf-8 -*-

def indicator_xm(df):
    """

    """
    import math
    import pandas as pd
    import operator

    def MA(S, N):
        return pd.Series(S).rolling(N, min_periods=1).mean().values

    def HHV(S, N):
        return pd.Series(S).rolling(N, min_periods=1).max().values

    def LLV(S, N):
        return pd.Series(S).rolling(N, min_periods=1).min().values

    def EMA(S, N):  # alpha=2/(span+1)
        return pd.Series(S).ewm(span=N, adjust=False).mean().values

    high = df['high']
    low = df['low']
    close = df['close']

    d_long = (HHV(high, 34) - LLV(low, 34))
    d_long[d_long == 0] = 0.00001
    d1 = -100 * (HHV(high, 34) - close) / d_long
    A = MA(d1, 19)
    d_short = (HHV(high, 14) - LLV(low, 14))
    d_short[d_short == 0] = 0.00001
    B = -100 * (HHV(high, 14) - close) / d_short
    D = EMA(d1, 4)
    long = [50 if math.isnan(x) else round(x + 100, 4) for x in A]
    short = [50 if math.isnan(x) else round(x + 100, 4) for x in B]
    mid = [50 if math.isnan(x) else round(x + 100, 4) for x in D]
    hist = [round(x, 4) for x in list(map(operator.sub, mid, long))]  # -100 ~ 100 -> 0 - 100 : (x+100)/2

    return short, mid, long, hist
