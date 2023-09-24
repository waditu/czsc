# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/30 12:08
describe:
"""
import os
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '...')
sys.path.insert(0, '../../..')
# # 插入用户自定义信号函数模块所在目录
# sys.path.insert(0, os.path.join(os.path.expanduser('~'), '.czsc/czsc_usr_signals'))

import re
import czsc
from loguru import logger
from czsc.utils import import_by_name
from czsc import SignalsParser

czsc.welcome()

signals_module_name = 'czsc.signals'
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


if __name__ == '__main__':
    sp = SignalsParser(signals_module=signals_module_name)
    conf = sp.parse(signals_seq)
    parsed_name = {x['name'] for x in conf}
    print(f"total signal functions: {len(sp.sig_name_map)}; parsed: {len(parsed_name)}")
    # total signal functions: 197; parsed: 197

    # 测试信号配置生成信号
    from czsc import generate_czsc_signals, get_signals_freqs, get_signals_config
    from test.test_analyze import read_1min
    bars = read_1min()
    conf = get_signals_config(signals_seq)
    freqs = get_signals_freqs(signals_seq)
    sigs = generate_czsc_signals(bars, signals_config=conf, sdt='20190101', df=True)
    print(sigs.shape)
