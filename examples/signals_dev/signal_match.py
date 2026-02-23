# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/30 12:08
describe: 信号匹配和解析示例

本示例展示如何：
1. 解析 czsc.signals 模块中所有信号函数的信号定义
2. 使用 SignalsParser 解析信号配置
3. 使用 generate_czsc_signals 生成信号
"""
import re
import czsc
from loguru import logger
from czsc.utils import import_by_name
from czsc import SignalsParser

czsc.welcome()

signals_module_name = "czsc.signals"
signals_seq = []
signals_module = import_by_name(signals_module_name)
for name in dir(signals_module):
    if "_" not in name:
        continue

    try:
        doc = getattr(signals_module, name).__doc__
        # 解析信号列表
        sigs = re.findall(r"Signal\('(.*)'\)", doc)
        if sigs:
            signals_seq.extend(sigs)
    except Exception as e:
        logger.error(f"解析信号函数 {name} 出错：{e}")


if __name__ == "__main__":
    sp = SignalsParser(signals_module=signals_module_name)
    conf = sp.parse(signals_seq)
    parsed_name = {x["name"] for x in conf}
    print(f"total signal functions: {len(sp.sig_name_map)}; parsed: {len(parsed_name)}")

    # 测试信号配置生成信号
    from czsc import generate_czsc_signals, get_signals_freqs, get_signals_config
    from czsc.mock import generate_symbol_kines
    from czsc import format_standard_kline, Freq

    # 使用 mock 数据代替外部数据源
    df = generate_symbol_kines('test', '1分钟', '20220101', '20230101', seed=42)
    bars = format_standard_kline(df, freq=Freq.F1)

    conf = get_signals_config(signals_seq)
    freqs = get_signals_freqs(signals_seq)
    sigs = generate_czsc_signals(bars, signals_config=conf, sdt="20220601", df=True)
    print(sigs.shape)
