import pandas as pd

def test():
    import matplotlib.pyplot as plt
    from czsc.sensors.feature import FixedNumberSelector

    dfs = pd.read_feather(r"D:\QMT投研\因子测试\features.feather")
    cols = ['dt', 'symbol', 'open', 'close', 'high', 'low', 'vol', 'amount', 'n1b', 'score']
    dfs['score'] = dfs['trend'].astype(float)
    dfs = dfs[cols].copy()

    fns = FixedNumberSelector(dfs, k=200, d=50, is_stocks=True)

    dfh = pd.concat(fns.holds.values(), ignore_index=True)
    dfh.groupby('dt')[['n1b', 'edge']].mean().cumsum().plot(figsize=(20, 4), grid=True, title="nv")
    plt.show()

    dfh.groupby('dt')['symbol'].count().describe()


if __name__ == '__main__':
    test()
