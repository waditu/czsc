# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/29 10:04
describe: 
"""
import re
from loguru import logger
from parse import parse
from czsc.objects import Signal
from czsc.utils import import_by_name


class SignalsParser:
    """解析一串信号，生成信号函数配置"""

    def __init__(self, signals_module='czsc.signals'):
        """

        :param signals_module: 指定信号函数所在模块
        """
        self.signals_module = signals_module
        sig_name_map = {}
        sig_pats_map = {}

        signals_module = import_by_name(signals_module)
        for name in dir(signals_module):
            if "_" not in name:
                continue

            try:
                doc = getattr(signals_module, name).__doc__
                # 解析信号函数参数
                pats = re.findall(r"参数模板：\"(.*)\"", doc)
                if pats:
                    sig_pats_map[name] = pats[0]

                # 解析信号列表
                sigs = re.findall(r"Signal\('(.*)'\)", doc)
                if sigs:
                    sig_name_map[name] = [Signal(x) for x in sigs]

            except Exception as e:
                logger.error(f"解析信号函数 {name} 出错：{e}")

        self.sig_name_map = sig_name_map
        self.sig_pats_map = sig_pats_map

    def parse_params(self, name, signal):
        """获取信号函数参数

        :param name: 信号函数名称
        :param signal: 需要解析的信号
        :return:
        """
        key = Signal(signal).key
        pats = self.sig_pats_map.get(name, None)
        if not pats:
            return None

        try:
            params = parse(pats, key).named
            if 'di' in params:
                params['di'] = int(params['di'])

            params['name'] = f"{self.signals_module}.{name}"
            return params
        except Exception as e:
            logger.error(f"解析信号 {signal} - {name} - {pats} 出错：{e}")
            return None

    def get_function_name(self, signal):
        """获取信号函数名称"""
        sig_name_map = self.sig_name_map
        _signal = Signal(signal)
        _k3_match = list({k for k, v in sig_name_map.items() if v[0].k3 == _signal.k3})

        if len(_k3_match) == 1:
            return _k3_match[0]
        else:
            logger.error(f"信号 {signal} 有多个匹配函数：{_k3_match}，请手动解析信号")
            return None

    def parse(self, signal_seq):
        """解析信号序列"""
        res = []
        for signal in signal_seq:
            name = self.get_function_name(signal)
            if name in self.sig_pats_map:
                row = self.parse_params(name, signal)
                if row and row not in res:
                    res.append(row)
            else:
                logger.warning(f"未找到解析函数：{name}，请手动解析信号：{signal}")
        return res
