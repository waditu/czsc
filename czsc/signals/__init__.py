"""czsc.signals —— 信号函数命名空间总入口。

本包是 CZSC 项目中所有“信号函数（signal functions）”的统一入口，按类别拆分为多个子模块：

- :mod:`czsc.signals.bar`      —— K 线级别信号（如成交量累计、振幅、跳空等）
- :mod:`czsc.signals.cxt`      —— 上下文信号（缠论结构、分型、笔、线段等）
- :mod:`czsc.signals.tas`      —— 技术指标信号（MACD、KDJ、BOLL 等基于 ``ta-lib`` 的指标族）
- :mod:`czsc.signals.vol`      —— 成交量类信号
- :mod:`czsc.signals.pressure` —— 价格压力/支撑相关信号
- :mod:`czsc.signals.obv`      —— OBV 能量潮相关信号
- :mod:`czsc.signals.cvolp`    —— 累积成交量分布（CVOLP）相关信号

底层实现说明
============
这些子模块仅提供薄薄一层 Python 转发壳。真正的信号计算逻辑由 Rust crate
``czsc-signals`` 实现，并通过 ``czsc._native.call_signal`` 暴露给 Python。Rust 端
利用 ``inventory::collect!`` 在编译期收集所有标注了 ``#[signal(...)]`` 宏的函数，
形成一张全局信号清单（inventory），运行时由 Python 通过名字查找并派发。

调用约定
========
- 由 :class:`czsc.CzscSignals` / :func:`czsc.generate_czsc_signals` 等高层接口
  统一驱动信号的批量生成；
- 单个 Rust 信号函数当前的入参为 ``(&CZSC, &HashMap, &mut TaCache)``，因此还不能
  直接在 Python 端用普通函数调用。各子模块仅负责暴露“命名空间契约 + 共享辅助
  工具”，便于上层做信号注册、参数模板查询和结构化解析。
"""

# 显式导入各信号子模块，确保 ``czsc.signals.xxx`` 始终可用，并触发其内部的延迟注册逻辑
from czsc.signals import bar, cvolp, cxt, obv, pressure, tas, vol

# 对外暴露的子模块名单（与 ``import czsc.signals`` 之后的 ``czsc.signals.xxx`` 一一对应）
__all__ = ["bar", "cxt", "tas", "vol", "pressure", "obv", "cvolp"]
