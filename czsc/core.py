import os
from loguru import logger
from typing import Tuple, Optional


def check_rs_czsc() -> Tuple[bool, Optional[str]]:
    """
    检查 rs_czsc 库是否正确安装

    Returns:
        Tuple[bool, Optional[str]]: (是否安装成功, 版本号或错误信息)
    """
    try:
        import rs_czsc
        # 尝试获取版本信息
        version = getattr(rs_czsc, '__version__', 'unknown')
        return True, version
    except ImportError as e:
        return False, f"ImportError: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

installed, rs_czsc_version = check_rs_czsc()

if os.getenv('CZSC_USE_PYTHON', False) or not installed:
    logger.info("使用 python 版本对象")
    from czsc.py import (
        # 枚举类型
        Operate, Freq, Mark, Direction,
        # 核心分析类
        CZSC,
        # 分析函数
        remove_include, check_bi, check_fx, check_fxs,
        # K线生成器
        BarGenerator, freq_end_time, is_trading_time, format_standard_kline,
        # 数据对象
        RawBar, NewBar, FX, BI, FakeBI, ZS, Signal, Event, Position,
        # 回测
        WeightBacktest
    )
else:
    logger.info("使用 rust 版本对象")
    # 导入已经用 rust 复现的函数
    from rs_czsc import (
        # 枚举类型
        Operate, Freq, Mark, Direction,
        # 核心分析类
        CZSC,
        # K线生成器
        BarGenerator, format_standard_kline,
        # 数据对象
        RawBar, NewBar, FX, BI, FakeBI, ZS, Signal, Event, Position,
        # 回测
        WeightBacktest
    )
    # 从 py 模块导入未复现的函数
    from czsc.py import (
        # 分析函数（rust版本未实现）
        remove_include, check_bi, check_fx, check_fxs,
        # K线生成器函数（rust版本未实现）
        freq_end_time, is_trading_time
    )
    

__all__ = [
    # 枚举类型
    "Operate", "Freq", "Mark", "Direction",
    # 核心分析类
    "CZSC",
    # 分析函数
    "remove_include", "check_bi", "check_fx", "check_fxs",
    # K线生成器
    "BarGenerator", "freq_end_time", "is_trading_time", "format_standard_kline",
    # 数据对象
    "RawBar", "NewBar", "FX", "BI", "FakeBI", "ZS", "Signal", "Event", "Position",
    # 回测
    "WeightBacktest",
    # 工具函数
    "check_rs_czsc"
]    
