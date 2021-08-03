# coding: utf-8
import os
from tqdm import tqdm

from czsc.utils.kline_generator import KlineGenerator
from .test_analyze import read_1min

cur_path = os.path.split(os.path.realpath(__file__))[0]
kline = read_1min()


def test_kline_generator():
    # 验证指定级别
    bars = kline[:2000]

    kg = KlineGenerator(freqs=['周线', '日线', '30分钟', '5分钟', '1分钟'])
    for row in tqdm(bars):
        kg.update(row)

    assert not kg.m60 and not kg.m15

    kg = KlineGenerator(max_count=2000, freqs=['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟'])
    for row in tqdm(bars):
        kg.update(row)

    assert kg.m60 and kg.m15

    # 验证K线获取
    klines = kg.get_klines({'1分钟': 100, '5分钟': 100})
    for k, v in klines.items():
        assert len(v) == 100

    # 数量验证
    assert len(kg.m1) == 2000
    assert len(kg.m5) == 401
    assert len(kg.m15) == 134

    # 测试实盘连续输入
    for _ in range(5):
        kg.update(bars[-1])
        assert len(kg.m1) == 2000

