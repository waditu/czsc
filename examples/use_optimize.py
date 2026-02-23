# -*- coding: utf-8 -*-
"""
OpensOptimize / ExitsOptimize 使用示例

本示例展示如何使用 czsc 的策略优化工具进行入场和出场信号的优化。

OpensOptimize：遍历候选入场信号，找到最优入场信号组合
ExitsOptimize：遍历候选出场事件，找到最优出场信号组合

注意：
1. 优化需要基础策略的持仓配置文件（JSON格式），可通过 Strategy.save_positions() 生成
2. 多进程执行时需在 __main__ 中调用
3. 本示例使用 mock 数据，实际使用时替换为真实数据源的 read_bars 函数
"""
import os
from pathlib import Path
from czsc.mock import generate_symbol_kines
from czsc import format_standard_kline, Freq
from czsc.traders.optimize import OpensOptimize, ExitsOptimize


def read_mock_bars(symbol, freq, sdt, edt, **kwargs):
    """使用 mock 数据模拟 read_bars 接口"""
    freq_map = {'日线': ('日线', Freq.D), '30分钟': ('30分钟', Freq.F30), '15分钟': ('15分钟', Freq.F15)}
    mock_freq, bar_freq = freq_map.get(freq, ('日线', Freq.D))
    df = generate_symbol_kines(symbol, mock_freq, sdt, edt, seed=42)
    bars = format_standard_kline(df, freq=bar_freq)
    return bars


def create_base_positions(results_path):
    """创建基础策略持仓配置文件

    优化工具需要基础策略的 JSON 配置文件作为输入。
    这里创建一个简单的日线笔方向策略作为基础策略，
    使用 CzscStrategyBase.save_positions 保存以确保格式正确（含 MD5 校验）。
    """
    from czsc import CzscStrategyBase, Event, Position

    class BaseStrategy(CzscStrategyBase):
        @property
        def positions(self):
            long_pos = Position(
                name="日线笔方向多头",
                symbol=self.symbol,
                opens=[Event.load({
                    "operate": "开多",
                    "signals_all": ["日线_D1_表里关系V230101_向上_任意_任意_0"],
                    "signals_any": [], "signals_not": [],
                })],
                exits=[], interval=3600 * 4, timeout=16 * 30, stop_loss=500,
            )
            short_pos = Position(
                name="日线笔方向空头",
                symbol=self.symbol,
                opens=[Event.load({
                    "operate": "开空",
                    "signals_all": ["日线_D1_表里关系V230101_向下_任意_任意_0"],
                    "signals_any": [], "signals_not": [],
                })],
                exits=[], interval=3600 * 4, timeout=16 * 30, stop_loss=500,
            )
            return [long_pos, short_pos]

    pos_path = Path(results_path)
    pos_path.mkdir(parents=True, exist_ok=True)

    tactic = BaseStrategy(symbol='symbol')
    tactic.save_positions(str(pos_path))

    # 返回生成的文件列表
    return [str(f) for f in sorted(pos_path.glob("*.json"))]


def run_opens_optim():
    """入场优化示例

    在基础策略的入场信号上叠加候选信号，测试哪些候选信号组合能提升策略绩效。
    """
    results_path = '/tmp/czsc_examples/optimize'
    symbols = [f'mock_{i:06d}' for i in range(1, 4)]
    files_position = create_base_positions(os.path.join(results_path, 'base_positions'))

    # 候选入场信号（这些信号会被逐一叠加到基础策略的入场条件上）
    candidate_signals = [
        "日线_D1MACD12#26#9_BS辅助V230313_多头_任意_任意_0",
        "日线_D1MACD12#26#9_BS辅助V230313_空头_任意_任意_0",
    ]

    oop = OpensOptimize(
        symbols=symbols,
        files_position=files_position,
        task_name='入场优化示例',
        candidate_signals=candidate_signals,
        read_bars=read_mock_bars,
        results_path=results_path,
        signals_module_name='czsc.signals',
        bar_sdt='20180101',
        bar_edt='20230101',
        sdt='20200101',
    )
    oop.execute(n_jobs=1)


def run_exits_optim():
    """出场优化示例

    在基础策略上叠加候选出场事件，测试哪些出场条件能提升策略绩效。
    """
    results_path = '/tmp/czsc_examples/optimize'
    symbols = [f'mock_{i:06d}' for i in range(1, 4)]
    files_position = create_base_positions(os.path.join(results_path, 'base_positions'))

    # 候选出场事件
    candidate_events = [
        {
            'operate': '平多',
            'factors': [
                {
                    'name': 'MACD空头',
                    'signals_all': ["日线_D1MACD12#26#9_BS辅助V230313_空头_任意_任意_0"],
                }
            ],
        },
        {
            'operate': '平空',
            'factors': [
                {
                    'name': 'MACD多头',
                    'signals_all': ["日线_D1MACD12#26#9_BS辅助V230313_多头_任意_任意_0"],
                }
            ],
        },
    ]

    eop = ExitsOptimize(
        symbols=symbols,
        files_position=files_position,
        task_name='出场优化示例',
        candidate_events=candidate_events,
        read_bars=read_mock_bars,
        results_path=results_path,
        signals_module_name='czsc.signals',
        bar_sdt='20180101',
        bar_edt='20230101',
        sdt='20200101',
    )
    eop.execute(n_jobs=1)


if __name__ == '__main__':
    run_opens_optim()
    # 注意：出场优化（ExitsOptimize）在 Rust 版本的 Position 中存在兼容性问题。
    # 如果需要使用出场优化，请设置环境变量 CZSC_USE_PYTHON=1 启用 Python 版本。
    # run_exits_optim()
