# https://s0cqcxuy3p.feishu.cn/wiki/Pf1fw1woQi4iJikbKJmcYToznxb
import sys

sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd

czsc.welcome()


def test_ensemble_weight():
    """从持仓权重样例数据中回测"""
    from czsc import WeightBacktest

    dfw = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")
    wb = WeightBacktest(dfw, digits=2, fee_rate=0.0002, n_jobs=1)
    ss = sorted(wb.stats.items())
    print(ss)


def test_rust_weight_backtest():
    """从持仓权重样例数据中回测"""
    from rs_czsc import WeightBacktest

    # from rs_czsc import daily_performance
    # from czsc import daily_performance

    # stats = daily_performance([0.01, 0.02, -0.03, 0.04, 0.05])
    dfw = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")

    # wb = WeightBacktest(czsc.to_arrow(dfw), digit=2, fee_rate=0.0002, n_jobs=1)
    wb = WeightBacktest(dfw, digits=2, fee_rate=0.0002, n_jobs=1)

    ss = sorted(wb.stats.items())
    print(ss)
