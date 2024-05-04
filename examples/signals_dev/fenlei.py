import czsc
from czsc.connectors import research

bars = research.get_raw_bars("000001.SH", "15分钟", "20101101", "20210101", fq="前复权")

signals_config = [{"name": "czsc.signals.bar_accelerate_V240428", "freq": "60分钟", "t": 3, "w": 34}]
czsc.check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore
