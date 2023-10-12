import sys
sys.path.insert(0, r"D:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd
from pathlib import Path
from czsc.connectors.research import get_raw_bars


def test_read():
    bars = get_raw_bars(symbol='SQrb9001', sdt='20170101', edt='20230101', freq='日线')
    bars = get_raw_bars(symbol='SQrb9001', sdt='20170101', edt='20230101', freq='5分钟')


def test_check_freq_and_market():
    from czsc.utils.bar_generator import check_freq_and_market
    # gruop_name = "期货主力"
    gruop_name = "中证500成分股"
    files = Path(fr"D:\CZSC投研数据\{gruop_name}").glob("*.parquet")
    for file in files:
        df = pd.read_parquet(file)
        time_seq = sorted(list({x.strftime("%H:%M") for x in df['dt']}))
        x_freq, market = check_freq_and_market(time_seq=time_seq, freq='1分钟')
        print(file.stem, x_freq, market)
        if market == "默认":
            print(time_seq)


def get_future_times():
    files = Path(r"D:\CZSC投研数据\期货主力").glob("*.parquet")
    times = {}
    for file in files:
        df = pd.read_parquet(file)
        times[file.stem] = sorted(list({x.strftime("%H:%M") for x in df['datetime']}))
    uni_times = sorted(list({x for y in times.values() for x in y}))

    df = pd.read_excel(r"D:\test.xlsx")
    df.to_feather(r"D:\ZB\git_repo\waditu\czsc\czsc\utils\minites_split.feather")


def test():
    bars = get_raw_bars("SQag9001", '1分钟', sdt='20230101', edt='20230801')
    # time_seq = sorted(list({x.dt.strftime("%H:%M") for x in bars}))
    # x_freq, market = czsc.check_freq_and_market(time_seq=time_seq)

    bg = czsc.BarGenerator(base_freq='1分钟', freqs=['5分钟', '15分钟', '20分钟', '30分钟', '60分钟', '日线'], max_count=1000, market="期货")
    for bar in bars:
        bg.update(bar)

    df = czsc.resample_bars(pd.DataFrame(bars), '30分钟', raw_bars=True)
    bg = czsc.BarGenerator(base_freq='30分钟', freqs=['60分钟', '日线'], max_count=1000, market="期货")
    for bar in df:
        bg.update(bar)


    df = czsc.resample_bars(pd.DataFrame(bars), '15分钟', raw_bars=True)
    bg = czsc.BarGenerator(base_freq='15分钟', freqs=['30分钟', '60分钟', '日线'], max_count=1000, market="期货")
    for bar in df:
        bg.update(bar)

    df = czsc.resample_bars(pd.DataFrame(bars), '20分钟', raw_bars=True)
    bg = czsc.BarGenerator(base_freq='20分钟', freqs=['30分钟', '60分钟', '日线'], max_count=1000, market="期货")
    for bar in df:
        bg.update(bar)

    df = czsc.resample_bars(pd.DataFrame(bars), '5分钟', raw_bars=True)
    bg = czsc.BarGenerator(base_freq='5分钟', freqs=['15分钟', '20分钟', '30分钟', '60分钟', '日线'], max_count=1000, market="期货")
    for bar in df:
        bg.update(bar)
