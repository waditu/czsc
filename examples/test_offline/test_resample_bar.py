import sys
sys.path.insert(0, r"D:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd
from czsc.connectors.research import get_raw_bars


bars = get_raw_bars("SQrb9001", '1分钟', sdt='20190101', edt='20200101')
time_seq = sorted(list({x.dt.strftime("%H:%M") for x in bars}))
df = czsc.resample_bars(pd.DataFrame(bars), '60分钟', raw_bars=True)
x_freq, market = czsc.check_freq_and_market(time_seq=time_seq)
