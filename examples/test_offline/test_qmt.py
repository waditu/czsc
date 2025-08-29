import sys
sys.path.insert(0, '../..')
import czsc
from czsc.connectors import qmt_connector as qmc

czsc.welcome()

df = qmc.get_raw_bars(symbol="000001.SZ", freq="日线", sdt="20210101", edt="20210131")
df = qmc.get_raw_bars(symbol="000001.SZ", freq="1分钟", sdt="20210101", edt="20210131")
