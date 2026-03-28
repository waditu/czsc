import os


def check_rs_czsc() -> tuple[bool, str | None]:
    """
    检查 rs_czsc 库是否正确安装

    Returns:
        Tuple[bool, Optional[str]]: (是否安装成功, 版本号或错误信息)
    """
    try:
        import rs_czsc

        # 尝试获取版本信息
        version = getattr(rs_czsc, "__version__", "unknown")
        return True, version
    except ImportError as e:
        return False, f"ImportError: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


installed, rs_czsc_version = check_rs_czsc()


if os.getenv("CZSC_USE_PYTHON", False) or not installed:
    from rs_czsc import WeightBacktest

    from czsc.py import (
        BI,
        # 核心分析类
        CZSC,
        FX,
        ZS,
        # K线生成器
        BarGenerator,
        Direction,
        Event,
        FakeBI,
        Freq,
        Mark,
        NewBar,
        # 枚举类型
        Operate,
        Position,
        # 数据对象
        RawBar,
        Signal,
        check_bi,
        check_fx,
        check_fxs,
        format_standard_kline,
        freq_end_time,
        is_trading_time,
        # 分析函数
        remove_include,
    )
else:
    # 导入已经用 rust 复现的函数
    from rs_czsc import (
        BI,
        # 核心分析类
        CZSC,
        FX,
        ZS,
        # K线生成器
        BarGenerator,
        Direction,
        Event,
        FakeBI,
        Freq,
        Mark,
        NewBar,
        # 枚举类型
        Operate,
        Position,
        # 数据对象
        RawBar,
        Signal,
        # 回测
        WeightBacktest,
        format_standard_kline,
    )

    # 从 py 模块导入未复现的函数
    from czsc.py import (
        check_bi,
        check_fx,
        check_fxs,
        # K线生成器函数（rust版本未实现）
        freq_end_time,
        is_trading_time,
        # 分析函数（rust版本未实现）
        remove_include,
    )


__all__ = [
    # 枚举类型
    "Operate",
    "Freq",
    "Mark",
    "Direction",
    # 核心分析类
    "CZSC",
    # 分析函数
    "remove_include",
    "check_bi",
    "check_fx",
    "check_fxs",
    # K线生成器
    "BarGenerator",
    "freq_end_time",
    "is_trading_time",
    "format_standard_kline",
    # 数据对象
    "RawBar",
    "NewBar",
    "FX",
    "BI",
    "FakeBI",
    "ZS",
    "Signal",
    "Event",
    "Position",
    # 回测
    "WeightBacktest",
    # 工具函数
    "check_rs_czsc",
    "cal_break_even_point",
]

# 从 utils 中导入统计分析函数
from czsc.utils.analysis.stats import cal_break_even_point
