# coding: utf-8
import os
from tqdm import tqdm
from src.czsc.utils.kline_generator import KlineGenerator
from src.czsc.utils.io import read_pkl

cur_path = os.path.split(os.path.realpath(__file__))[0]
file_kline = os.path.join(cur_path, "data/000001.XSHG_1MIN.pkl")
kline = read_pkl(file_kline)


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
    assert len(kg.m5) == 402
    assert len(kg.m15) == 134

    # 测试实盘连续输入
    for _ in range(5):
        kg.update(bars[-1])
        assert len(kg.m1) == 2000

