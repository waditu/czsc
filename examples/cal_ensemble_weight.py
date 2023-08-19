import czsc
import pandas as pd


def run_by_weights():
    """从持仓权重样例数据中回测"""
    dfw = pd.read_feather(r"C:\Users\zengb\Desktop\230814\weight_example.feather")
    wb = czsc.WeightBacktest(dfw, digits=1, fee_rate=0.0002, res_path=r"C:\Users\zengb\Desktop\230814\weight_example")
    res = wb.backtest()


def run_by_ensemble():
    """从单个 trader 中获取持仓权重，然后回测"""
    trader = czsc.dill_load(r"C:\Users\zengb\Desktop\230814\DLi9001.trader")

    def __ensemble_method(x):
        return x['A股日线SMA#5多头'] + 0.5 * x['A股日线SMA#5空头']
    
    dfw = czsc.get_ensemble_weight(trader, method=__ensemble_method)
    wb = czsc.WeightBacktest(dfw, digits=1, fee_rate=0.0002, res_path=r"C:\Users\zengb\Desktop\230814\DLi9001_ensemble")
    res = wb.backtest()

