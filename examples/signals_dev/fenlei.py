import czsc
from czsc.connectors import research

bars = research.get_raw_bars("000001.SH", '15分钟', '20101101', '20210101', fq='前复权')

signals_config = [{'name': "czsc.signals.tas_macd_first_bs_V221201", 'freq': "60分钟"}]
czsc.check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore
