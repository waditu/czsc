# coding: utf-8
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")

import os
import pandas as pd
from czsc.utils import KlineGenerator


cur_path = os.path.split(os.path.realpath(__file__))[0]
file_kline = os.path.join(cur_path, "data/000001.XSHG_1MIN.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, "dt"] = pd.to_datetime(kline.dt)


def test_kline_generator():
    kg = KlineGenerator()
    for _, row in kline.iterrows():
        kg.update(row.to_dict())

    # 数量验证
    assert len(kg.m1) == 2640
    assert len(kg.m5) == len(kg.m1) // 5
    assert len(kg.m15) == len(kg.m1) // 15
    assert len(kg.m30) == len(kg.m1) // 30
    assert len(kg.m60) == len(kg.m1) // 60
    assert len(kg.D) == len(kg.m1) // 240

    # 验证周线
    assert kg.W[1]['open'] == 3187.84
    assert kg.W[1]['close'] == 3383.32
    assert kg.W[1]['high'] == 3456.97
    assert kg.W[1]['low'] == 3187.84

    # 测试实盘连续输入
    for _ in range(5):
        kg.update(kline.iloc[-1].to_dict())
        assert len(kg.m1) == 2640
        assert len(kg.m5) == len(kg.m1) // 5
        assert len(kg.m15) == len(kg.m1) // 15
        assert len(kg.m30) == len(kg.m1) // 30
        assert len(kg.m60) == len(kg.m1) // 60
        assert len(kg.D) == len(kg.m1) // 240
        assert kg.W[1]['open'] == 3187.84
        assert kg.W[1]['close'] == 3383.32
        assert kg.W[1]['high'] == 3456.97
        assert kg.W[1]['low'] == 3187.84

