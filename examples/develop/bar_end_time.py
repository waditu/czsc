# 创建K线分割规则
import pandas as pd
from czsc.connectors.research import get_raw_bars


def init_kline():
    bars = get_raw_bars(symbol="000001.SH", freq="1分钟", sdt="20210903", edt="20210904", fq="后复权")
    dft = pd.DataFrame(bars)
    dft['time'] = dft['dt'].dt.strftime('%H:%M')
    dft[['time']].to_excel('test.xlsx')


    bars = get_raw_bars(symbol="SQau9001", freq="1分钟", sdt="20210903", edt="20210904", fq="后复权")
    dft = pd.DataFrame(bars)
    dft['time'] = dft['dt'].dt.strftime('%H:%M')
    dft[['time']].to_excel('test.xlsx')


# df = pd.read_excel(r"C:\Users\zengb\Desktop\time_split_conf_V2.xlsx")
# df['time_t'] = pd.to_datetime(df['time'], format='%H:%M')

# # for i in (3, 5, 10, 15, 20, 30, 60):
# #     df[f"{i}分钟A"] = df['time_t'].apply(lambda x: x + pd.Timedelta(minutes=i - x.minute % i))
# #     df[f"{i}分钟A"] = df[f"{i}分钟A"].dt.strftime('%H:%M').shift(1)

# # df['20分钟A'] = df['20分钟'].fillna(method='bfill')
# # for i in (2, 4, 6, 12):
# #     df[f"{i}分钟A"] = df['time_t'].apply(lambda x: x + pd.Timedelta(minutes=i - x.minute % i))
# #     df[f"{i}分钟A"] = df[f"{i}分钟A"].dt.strftime('%H:%M').shift(1)

# # df.to_excel(r"C:\Users\zengb\Desktop\time_split_conf_V2.xlsx", index=False)


# df['60分钟'] = df['60分钟'].fillna(method='bfill')
# df['120分钟'] = df['120分钟'].fillna(method='bfill')
# df.to_excel(r"C:\Users\zengb\Desktop\time_split_conf_V3.xlsx", index=False)

# df = pd.read_excel(r"C:\Users\zengb\Desktop\time_split_conf_V3.xlsx")
# df.to_feather("minites_split.feather")

# 默认分割规则

def split_time(freq="60分钟"):
    sdt = pd.to_datetime("2021-09-03 00:00")
    res = [sdt]
    for i in range(2000):
        sdt += pd.Timedelta(minutes=1)
        res.append(sdt)
    df = pd.DataFrame(res, columns=['time'])
    df['t1'] = df['time'].dt.strftime('%H:%M')
    df1 = df.resample(freq.replace("分钟", "T"), on='time').last().reset_index()
    df1['t2'] = df1['time'].dt.strftime('%H:%M')
    dfx = pd.merge_asof(df, df1, on='time', direction='forward')
    dfx = dfx.dropna().copy()
    dfx['time'] = dfx['t1_x']
    dfx['edt'] = dfx['t2']
    dfx['freq'] = freq
    dfx = dfx[['time', 'edt', 'freq']].drop_duplicates().sort_values('time')
    return dfx

rows = []
for freq in ("1分钟", "2分钟", "3分钟", "4分钟", "5分钟", "6分钟", "10分钟", "12分钟", "15分钟", "20分钟", "30分钟", "60分钟", '120分钟'):
    rows.append(split_time(freq))

df = pd.concat(rows, ignore_index=True)
df = pd.pivot_table(df, index='time', columns='freq', values='edt', aggfunc='first').reset_index()
df['market'] = "默认"
df = df[['market', 'time', '1分钟', '2分钟', '3分钟', '4分钟', '5分钟', '6分钟', '10分钟', '12分钟', '15分钟', '20分钟', '30分钟', '60分钟', '120分钟']]
df.to_excel(r"C:\Users\zengb\Desktop\time_split_conf_V4.xlsx", index=False)

df = pd.read_excel(r"C:\Users\zengb\Desktop\time_split_conf_V4.xlsx")
df.to_feather(r"D:\ZB\git_repo\waditu\czsc\czsc\utils\minites_split.feather")