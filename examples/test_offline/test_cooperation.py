import sys
sys.path.insert(0, r'D:\ZB\git_repo\waditu\czsc')
import czsc
from czsc.connectors.cooperation import *

czsc.welcome()


def test_cooperation():
    # 获取股票列表
    symbols = get_symbols(name="股票")
    print(f"股票数量：{len(symbols)}")

    # 获取日线数据
    kline = get_raw_bars(symbol="000001.SZ#STOCK", freq="日线", sdt="20220101", edt="20230101", fq="前复权")
    print(kline[-5:])

    # 获取60分钟数据
    kline = get_raw_bars(symbol="000001.SZ#STOCK", freq="60分钟", sdt="20220101", edt="20230101", fq="前复权")
    print(kline[-10:])

    # 获取ETF列表
    symbols = get_symbols(name="ETF")
    print(f"ETF数量：{len(symbols)}")

    # 获取指数列表
    symbols = get_symbols(name="A股指数")
    print(f"指数数量：{len(symbols)}")

    # 获取南华指数列表
    symbols = get_symbols(name="南华指数")
    print(f"南华指数数量：{len(symbols)}")

    # 获取期货主力列表
    symbols = get_symbols(name="期货主力")
    print(f"期货主力数量：{len(symbols)}")

    # 获取日线数据
    kline = get_raw_bars(symbol="SFIC9001", freq="日线", sdt="20210101", edt="20230101", fq="前复权")
    kline = get_raw_bars(symbol="SFIC9001", freq="30分钟", sdt="20220101", edt="20230101", fq="前复权")
