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
    wb = WeightBacktest(dfw, digits=1, fee_rate=0.0002)
    ss = sorted(wb.stats.items())
    print(ss)


def test_rust_weight_backtest():
    """从持仓权重样例数据中回测"""
    from rs_czsc import PyBacktest as WeightBacktest

    dfw = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")

    wb = WeightBacktest(czsc.to_arrow(dfw), digits=1, fee_rate=0.0002, n_jobs=1)

    ss = sorted(wb.stats.items())
    print(ss)
