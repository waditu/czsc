# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/29 10:04
describe: 
"""
import re
from loguru import logger
from difflib import SequenceMatcher
from czsc.objects import Signal
from czsc.utils import import_by_name


class SignalsParser:
    """解析一串信号，生成信号函数配置"""

    def __init__(self, signals_module='czsc.signals', **kwargs):
        """

        :param signals_module: 指定信号函数所在模块
        :param kwargs:
            usr_parse_map: 用户自定义信号函数解析方法，字典类型，key 为信号函数名，value 为解析方法
        """
        self.signals_module = signals_module
        sig_name_map = {}
        signals_module = import_by_name(signals_module)
        for name in dir(signals_module):
            if "_" not in name:
                continue
            try:
                doc = getattr(signals_module, name).__doc__
                sigs = re.findall(r"Signal\('(.*)'\)", doc)
                if sigs:
                    sig_name_map[name] = [Signal(x) for x in sigs]
            except Exception as e:
                logger.error(f"解析信号函数 {name} 出错：{e}")
        self.sig_name_map = sig_name_map

        # 自动获取解析函数
        self._parse_map = {k: getattr(self, f"_SignalsParser__parse_{k}") for k in self.sig_name_map.keys()
                           if getattr(self, f"_SignalsParser__parse_{k}", None)}

        # 用户自定义信号函数解析方法传入
        if kwargs.get("usr_parse_map", None):
            self._parse_map.update(kwargs.get("usr_parse_map"))

    def get_function_name(self, signal):
        """获取信号函数名称"""
        sig_name_map = self.sig_name_map
        _signal = Signal(signal)
        _k3_match = list({k for k, v in sig_name_map.items() if v[0].k3 == _signal.k3})
        # 优先匹配 k3，满足条件直接返回
        if len(_k3_match) == 1:
            return _k3_match[0]

        if len(_k3_match) > 1:
            logger.warning(f"信号 {signal} 有多个匹配函数：{_k3_match}，请手动解析信号")
            return None

        _signal_k2_k3 = _signal.k2 + _signal.k3
        scores = {}
        for k, v in sig_name_map.items():
            # 计算 k2, k3 的相似度
            _vs = [SequenceMatcher(None, s.k2 + s.k3, _signal_k2_k3).ratio() for s in v]
            if max(_vs) >= 0.8:
                scores[k] = max(_vs)

        if not scores:
            return None

        return max(scores, key=scores.get)

    def parse(self, signal_seq):
        """解析信号序列"""
        res = []
        for signal in signal_seq:
            name = self.get_function_name(signal)
            if name in self._parse_map:
                row = self._parse_map[name](signal)
                row['name'] = f"{self.signals_module}.{name}"
                if row not in res:
                    res.append(row)
            else:
                logger.warning(f"未找到解析函数：{name}，请手动解析信号：{signal}")
        return res

    def parse_with_name(self, signal_map):
        """解析信号字典，信号字典的 key 为信号函数名，value 为信号序列"""
        res = []
        for name, signal_seq in signal_map.items():
            if name in self._parse_map:
                for signal in signal_seq:
                    row = self._parse_map[name](signal)
                    row['name'] = f"czsc.signals.{name}"
                    if row not in res:
                        res.append(row)
            else:
                logger.warning(f"未找到解析函数：{name}，请手动解析信号：{signal_seq}")
        return res

    @staticmethod
    def __remove_duplicates(_res):
        # 去除重复的信号配置
        _res = [dict(t) for t in {tuple(d.items()) for d in _res}]
        return _res

    @staticmethod
    def __parse_bar_single_V230214(signal):
        # https://czsc.readthedocs.io/en/0.9.13/api/czsc.signals.bar_single_V230214.html
        pats = re.findall(r"(.*?)_D(\d+)T(\d+)_", signal)[0]
        _row = {"freq": pats[0], "di": int(pats[1]), 't': int(pats[2]) / 10}
        return _row

    @staticmethod
    def __parse_cxt_third_bs_V230319(signal):
        pats = re.findall(r"(.*?)_D(\d+)(\D+)(\d+)_", signal)[0]
        _row = {"freq": pats[0], "di": int(pats[1]), 'ma_type': pats[2], 'timeperiod': int(pats[3])}
        return _row

    @staticmethod
    def __parse_byi_bi_end_V230107(signal):
        pats = re.findall(r"(.*?)_", signal)
        _row = {"freq": pats[0]}
        return _row

    @staticmethod
    def __parse_byi_bi_end_V230106(signal):
        pats = re.findall(r"(.*?)_", signal)
        _row = {"freq": pats[0]}
        return _row

    @staticmethod
    def __parse_bar_accelerate_V221110(signal):
        # https://czsc.readthedocs.io/en/0.9.13/api/czsc.signals.bar_accelerate_V221110.html
        pats = re.findall(r"(.*?)_D(\d+)W(\d+)_", signal)[0]
        _row = {"freq": pats[0], "di": int(pats[1]), 'window': int(pats[2])}
        return _row

    @staticmethod
    def __parse_bar_accelerate_V221118(signal):
        # https://czsc.readthedocs.io/en/0.9.13/api/czsc.signals.bar_accelerate_V221118.html
        pats = re.findall(r"(.*?)_D(\d+)W(\d+)(\D+)(\d+)_", signal)[0]
        _row = {
            "freq": pats[0],
            "di": int(pats[1]),
            "window ": int(pats[2]),
            "ma_type": pats[3],
            "timeperiod ": int(pats[4]),
        }
        return _row

    @staticmethod
    def __parse_bar_bpm_V230227(signal):
        # https://czsc.readthedocs.io/en/0.9.13/api/czsc.signals.bar_bpm_V230227.html
        pats = re.findall(r"(.*?)_D(\d+)N(\d+)T(\d+)_", signal)[0]
        _row = {"freq": pats[0], "di": int(pats[1]), "n ": int(pats[2]), "th ": int(pats[3])}
        return _row
