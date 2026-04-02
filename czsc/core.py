import os

from rs_czsc import (
    BI,
    CZSC,
    FX,
    ZS,
    BarGenerator,
    Direction,
    Event,
    FakeBI,
    Freq,
    Mark,
    NewBar,
    Operate,
    Position,
    RawBar,
    Signal,
    WeightBacktest,
    format_standard_kline,
)

from czsc.utils.analysis.stats import cal_break_even_point


def check_rs_czsc() -> tuple[bool, str | None]:
    """
    检查 rs_czsc 库是否正确安装

    Returns:
        Tuple[bool, Optional[str]]: (是否安装成功, 版本号或错误信息)
    """
    try:
        import rs_czsc

        version = getattr(rs_czsc, "__version__", "unknown")
        return True, version
    except ImportError as e:
        return False, f"ImportError: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


installed, rs_czsc_version = check_rs_czsc()


__all__ = [
    "Operate",
    "Freq",
    "Mark",
    "Direction",
    "CZSC",
    "BarGenerator",
    "format_standard_kline",
    "RawBar",
    "NewBar",
    "FX",
    "BI",
    "FakeBI",
    "ZS",
    "Signal",
    "Event",
    "Position",
    "WeightBacktest",
    "check_rs_czsc",
    "cal_break_even_point",
]
