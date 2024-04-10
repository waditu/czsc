# https://s0cqcxuy3p.feishu.cn/wiki/Pf1fw1woQi4iJikbKJmcYToznxb
import sys
sys.path.insert(0, r"D:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd

czsc.welcome()


def test_ensemble_weight():
    """从持仓权重样例数据中回测"""
    dfw = pd.read_feather(r"C:\Users\zengb\Desktop\weight_example.feather")
    wb = czsc.WeightBacktest(dfw, digits=1, fee_rate=0.0002, res_path=r"C:\Users\zengb\Desktop\weight_example")
    res = wb.backtest()

