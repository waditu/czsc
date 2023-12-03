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
from typing import List, Dict
from czsc.objects import Signal
from czsc.utils import import_by_name, sorted_freqs


class SignalsParser:
    """解析一串信号，生成信号函数配置"""

    def __init__(self, signals_module: str = 'czsc.signals'):
        """

        函数执行逻辑：

        1. 将传入的 signals_module 参数赋给实例变量 self.signals_module，代表信号函数所在的模块，默认模块是czsc库的signals模块。
        2. 使用 import_by_name 函数导入了指定名称的模块 signals_module。
        3. 对于导入的模块中的每个属性名进行遍历：
            - 魔法函数和私有函数不进行处理。
            - 获取函数的注解信息，并通过正则表达式获取注解中的参数模板和信号列表。
            - 如果解析到了参数模板，则将其存储在 sig_pats_map 中，key是函数名称。
            - 如果解析到了信号列表，则将其存储在 sig_name_map 中，并且为每个信号创建了 Signal 对象并存储在列表中，key是函数名称。
        4. 最后将得到的 sig_name_map 和 sig_pats_map 存储在实例变量中，以便其他方法使用。

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

        函数执行逻辑：

        1. 首先根据传入的 name 和 signal 参数，通过 Signal(signal).key 获取一个键值。
        2. 然后从实例变量 sig_pats_map 中获取与指定名称对应的参数模板，并将其存储在 pats 中。
        3. 如果没有找到参数模板，则返回 None。
        4. 最后将信号函数的完整名称存储在参数字典中，并返回参数字典。

        :param name: 信号函数名称, 如：cxt_bi_end_V230222
        :param signal: 需要解析的信号, 如：15分钟_D1K_量柱V221218_低量柱_6K_任意_0
        :return:
        """
        key = Signal(signal).key
        pats = self.sig_pats_map.get(name, None)
        if not pats:
            return None

        try:
            params = parse(pats, key).named     # type: ignore
            if 'di' in params:
                params['di'] = int(params['di'])

            params['name'] = f"{self.signals_module}.{name}"
            return params
        except Exception as e:
            logger.error(f"解析信号 {signal} - {name} - {pats} 出错：{e}")
            return None

    def get_function_name(self, signal: str):
        """获取信号对应的信号函数名称

        函数执行逻辑：

        1. 创建一个 _signal 对象，通过传入的信号字符串进行初始化。
        2. 通过遍历 sig_name_map 中的项目，找出那些与 _signal.k3 相匹配的键，并将它们存储在 _k3_match 列表中。
        3. 如果只有一个匹配项，则返回该项；否则记录错误日志并返回 None。

        :param signal: 信号，数据样例：15分钟_D1K_量柱V221218_低量柱_6K_任意_0
        :return: 信号函数名称
        """
        sig_name_map = self.sig_name_map
        _signal = Signal(signal)
        _k3_match = list({k for k, v in sig_name_map.items() if v[0].k3 == _signal.k3})

        if len(_k3_match) == 1:
            return _k3_match[0]
        else:
            logger.error(f"信号 {signal} 有多个匹配函数：{_k3_match}，请手动解析信号")
            return None

    def config_to_keys(self, config: List[Dict]):
        """将信号函数配置转换为信号key列表

        函数执行逻辑：

        1. 首先创建了一个空列表 keys 用于存储信号key。
        2. 对于传入的 config 列表中的每个配置字典 conf 进行以下操作：
            - 获取信号函数的名称。
            - 如果该信号函数的名称在 self.sig_pats_map 中存在对应的模板，使用参数填充模板，并将结果添加到 keys 列表中。

        :param config: 信号函数配置

            config = [{'freq': '日线', 'max_overlap': '3', 'name': 'czsc.signals.cxt_bi_end_V230222'},
                     {'freq1': '日线', 'freq2': '60分钟', 'name': 'czsc.signals.cxt_zhong_shu_gong_zhen_V221221'}]

        :return: 信号key列表
        """
        keys = []
        for conf in config:
            name = conf['name'].split('.')[-1]
            if name in self.sig_pats_map:
                keys.append(self.sig_pats_map[name].format(**conf))
        return keys

    def parse(self, signal_seq: List[str]):
        """解析信号序列

        函数执行逻辑：

        1. 接受一个signal_seq 参数。
        2. 定义一个空列表res ，用于存储解析结果。
        3. 遍历信号序列signal_seq 中的每一个信号：

            - 调用get_function_name 方法，以信号为参数，获取该信号对应的函数名。
            - 进行函数名存在性判断，name 在sig_pats_map 中存在，
              调用parse_params 方法，以函数名和信号为参数，解析参数并返回结果。

        :param signal_seq: 信号序列, 样例：
            ['15分钟_D1K_量柱V221218_低量柱_6K_任意_0', '日线_D1K_量柱V221218_低量柱_6K_任意_0']
        :return: 信号函数配置
        """
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


def get_signals_config(signals_seq: List[str], signals_module: str = 'czsc.signals') -> List[Dict]:
    """获取信号列表对应的信号函数配置

    函数执行逻辑：

    1. 首先创建了一个 SignalsParser 类的实例对象 sp，传入了参数 signals_module进行初始化，
        初始化工作主要是解析signals_module下的信号函数，生成了sig_pats_map信号参数模板字典和sig_name_map信号列表字典。
    2. 然后使用 sp 实例调用 parse 方法，该方法解析 signals_seq 中的信号，并返回信号函数的配置信息。

    :param signals_seq: 信号列表
    :param signals_module: 信号函数所在模块
    :return: 信号函数配置
    """
    sp = SignalsParser(signals_module=signals_module)
    conf = sp.parse(signals_seq)
    return conf


def get_signals_freqs(signals_seq: List) -> List[str]:
    """获取信号列表对应的K线周期列表

    函数执行逻辑：

    1. 然后对于 signals_seq 中的每个信号进行以下操作：

        - 使用正则表达式从信号中提取信号周期，并将其存储在 _freqs 变量中。
        - 如果提取到了信号周期，则将其加入到 freqs 列表中。

    2. 最后验证数据是否符合sorted_freqs列表规范，并且以sorted_freqs列表的排序进行返回。

    :param signals_seq: 信号列表 / 信号函数配置列表
    :return: K线周期列表
    """
    freqs = []
    for signal in signals_seq:
        _freqs = re.findall('|'.join(sorted_freqs), str(signal))
        if _freqs:
            freqs.extend(_freqs)
    return [x for x in sorted_freqs if x in freqs]
