import sys

sys.path.insert(0, ".")
sys.path.insert(0, "..")
import czsc
import pandas as pd

assert czsc.WeightBacktest.version == "V240627"


def run_by_weights():
    """从持仓权重样例数据中回测"""
    dfw = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")
    wb = czsc.WeightBacktest(dfw, digits=1, fee_rate=0.0002, n_jobs=1)
    # wb = czsc.WeightBacktest(dfw, digits=1, fee_rate=0.0002)
    dailys = wb.dailys
    print(wb.stats)
    print(wb.alpha_stats)
    print(wb.bench_stats)

    # 计算等权组合的超额
    df1 = dailys.groupby("date").agg({"return": "mean", "n1b": "mean"})
    df1["alpha"] = df1["return"] - df1["n1b"]

    # ------------------------------------------------------------------------------------
    # 查看绩效评价
    # ------------------------------------------------------------------------------------
    print(wb.results["绩效评价"])
    # {'开始日期': '20170103',
    #  '结束日期': '20230731',
    #  '年化': 0.093,                       # 品种等权之后的年化收益率
    #  '夏普': 1.19,                        # 品种等权之后的夏普比率
    #  '最大回撤': 0.1397,                  # 品种等权之后的最大回撤
    #  '卡玛': 0.67,
    #  '日胜率': 0.5228,                    # 品种等权之后的日胜率
    #  '年化波动率': 0.0782,
    #  '非零覆盖': 1.0,
    #  '盈亏平衡点': 0.9782,                # 品种等权之后的盈亏平衡点，这个值越小越好，正常策略的范围应该在 0.85~0.98 之间
    #  '单笔收益': 25.6,                    # 将所有品种的单笔汇总之后的平均收益，单位是 BP，即 0.01%
    #  '交易胜率': 0.3717,                  # 将所有品种的单笔汇总之后的交易胜率
    #  '持仓天数': 3.69,                    # 将所有品种的单笔汇总之后的平均持仓天数
    #  '持仓K线数': 971.66}                 # 将所有品种的单笔汇总之后的平均持仓 K 线数

    # ------------------------------------------------------------------------------------
    # 获取指定品种的回测结果
    # ------------------------------------------------------------------------------------
    symbol_res = wb.results[wb.symbols[0]]
    print(symbol_res)

    wb.report(res_path=r"C:\Users\zengb\Desktop\231005\weight_example")


if __name__ == "__main__":
    run_by_weights()
