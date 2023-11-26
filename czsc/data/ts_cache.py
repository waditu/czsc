# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/24 16:12
describe:
Tushare 数据缓存，这是用pickle缓存数据，是临时性的缓存。
单次缓存，多次使用，但是不做增量更新，适用于研究场景。
数据缓存是一种用空间换时间的方法，需要有较大磁盘空间，跑全市场至少需要50GB以上。
"""
import time
import os.path
import shutil
import pandas as pd
from tqdm import tqdm
from typing import List
from deprecated import deprecated
from datetime import timedelta, datetime
from czsc import envs
from czsc.enum import Freq
from czsc.utils import io
from czsc.data.ts import ts, pro, format_kline, dt_fmt, date_fmt


def update_bars_return(kline: pd.DataFrame, bar_numbers=None):
    """给K线加上未来收益和过去收益的计算

    :param kline:
    :param bar_numbers:
    :return:
    """
    # 统一处理数据精度
    for col in ['open', 'close', 'high', 'low']:
        kline[col] = kline[col].round(4)

    assert kline['dt'][0] < kline['dt'][1], "kline 必须是时间升序"
    if not bar_numbers:
        bar_numbers = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377)
    for bar_number in bar_numbers:
        # 向后看（今天的 n1b 等于后天的开盘价相对明天开盘价的收益，单位：BP）
        n_col = 'n' + str(bar_number) + 'b'
        kline[n_col] = (kline['open'].shift(-bar_number-1) / kline['open'].shift(-1) - 1) * 10000
        kline[n_col] = kline[n_col].round(4)

        # 向前看（今天的 b1b 等于今天的收盘价相对昨天收盘价的收益，单位：BP）
        b_col = 'b' + str(bar_number) + 'b'
        kline[b_col] = (kline['close'] / kline['close'].shift(bar_number) - 1) * 10000
        kline[b_col] = kline[b_col].round(4)


class TsDataCache:
    """Tushare 数据缓存"""
    def __init__(self, data_path, refresh=False, sdt="20120101", edt=datetime.now()):
        """

        :param data_path: 数据路径
        :param refresh: 是否刷新缓存
        :param sdt: 缓存开始时间
        :param edt: 缓存结束时间
        """
        self.date_fmt = "%Y%m%d"
        self.verbose = envs.get_verbose()
        self.refresh = refresh
        self.sdt = pd.to_datetime(sdt).strftime(self.date_fmt)
        self.edt = pd.to_datetime(edt).strftime(self.date_fmt)
        self.data_path = data_path
        self.prefix = "TS_CACHE"
        self.cache_path = os.path.join(self.data_path, self.prefix)
        os.makedirs(self.cache_path, exist_ok=True)
        self.pro = pro
        self.__prepare_api_path()

        self.freq_map = {
            "1min": Freq.F1,
            "5min": Freq.F5,
            "15min": Freq.F15,
            "30min": Freq.F30,
            "60min": Freq.F60,
            "D": Freq.D,
            "W": Freq.W,
            "M": Freq.M,
        }

    def __prepare_api_path(self):
        """给每个tushare数据接口创建一个缓存路径"""
        cache_path = self.cache_path
        self.api_names = [
            'ths_daily', 'ths_index', 'ths_member', 'pro_bar',
            'hk_hold', 'cctv_news', 'daily_basic', 'index_weight',
            'pro_bar_minutes', 'limit_list', 'bak_basic',

            # CZSC加工缓存
            "stocks_daily_bars", "stocks_daily_basic", "stocks_daily_bak",
            "daily_basic_new", "stocks_daily_basic_new"
        ]
        self.api_path_map = {k: os.path.join(cache_path, k) for k in self.api_names}

        for k, path in self.api_path_map.items():
            os.makedirs(path, exist_ok=True)

    def clear(self):
        """清空缓存"""
        for path in os.listdir(self.data_path):
            if path.startswith(self.prefix):
                path = os.path.join(self.data_path, path)
                shutil.rmtree(path)
                if self.verbose:
                    print(f"clear: remove {path}")
                if os.path.exists(path):
                    print(f"Tushare 数据缓存清理失败，请手动删除缓存文件夹：{self.cache_path}")

    # ------------------------------------Tushare 原生接口----------------------------------------------
    def ths_daily(self, ts_code, start_date=None, end_date=None, raw_bar=True):
        """获取同花顺概念板块的日线行情"""
        cache_path = self.api_path_map['ths_daily']
        file_cache = os.path.join(cache_path, f"ths_daily_{ts_code}_sdt{self.sdt}.feather")

        if not self.refresh and os.path.exists(file_cache):
            kline = pd.read_feather(file_cache)
            if self.verbose:
                print(f"ths_daily: read cache {file_cache}")
        else:
            if self.verbose:
                print(f"ths_daily: refresh {file_cache}")
            kline = pro.ths_daily(ts_code=ts_code, start_date=self.sdt, end_date=self.edt,
                                  fields='ts_code,trade_date,open,close,high,low,vol')
            kline = kline.sort_values('trade_date', ignore_index=True)
            kline['trade_date'] = pd.to_datetime(kline['trade_date'], format=self.date_fmt)
            kline['dt'] = kline['trade_date']
            update_bars_return(kline)
            kline.to_feather(file_cache)

        kline['trade_date'] = pd.to_datetime(kline['trade_date'], format=self.date_fmt)
        if start_date:
            kline = kline[kline['trade_date'] >= pd.to_datetime(start_date)]
        if end_date:
            kline = kline[kline['trade_date'] <= pd.to_datetime(end_date)]

        kline.reset_index(drop=True, inplace=True)
        if raw_bar:
            kline = format_kline(kline, freq=Freq.D)
        return kline

    def ths_index(self, exchange="A", type_="N"):
        """获取同花顺概念

        https://tushare.pro/document/2?doc_id=259
        """
        cache_path = self.api_path_map['ths_index']
        file_cache = os.path.join(cache_path, f"ths_index_{exchange}_{type_}.feather")
        if not self.refresh and os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
            if self.verbose:
                print(f"ths_index: read cache {file_cache}")
        else:
            df = pro.ths_index(exchange=exchange, type=type_)
            df.to_feather(file_cache)
        return df

    def ths_member(self, ts_code):
        """获取同花顺概念成分股

        https://tushare.pro/document/2?doc_id=261
        :param ts_code:
        :return:
        """
        cache_path = self.api_path_map['ths_member']
        file_cache = os.path.join(cache_path, f"ths_member_{ts_code}.feather")
        if not self.refresh and os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
            if self.verbose:
                print(f"ths_index: read cache {file_cache}")
        else:
            df = pro.ths_member(ts_code=ts_code, fields="ts_code,code,name,weight,in_date,out_date,is_new")
            df = df.reset_index(drop=True, inplace=False)
            df.to_feather(file_cache)
        return df

    def pro_bar(self, ts_code, start_date=None, end_date=None, freq='D', asset="E", adj='qfq', raw_bar=True):
        """获取日线以上数据

        https://tushare.pro/document/2?doc_id=109

        :param ts_code:
        :param start_date:
        :param end_date:
        :param freq:
        :param asset: 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
        :param adj: 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
        :param raw_bar:
        :return:
        """
        cache_path = self.api_path_map['pro_bar']
        file_cache = os.path.join(cache_path, f"pro_bar_{ts_code}#{asset}_{self.sdt}_{freq}_{adj}.feather")

        if not self.refresh and os.path.exists(file_cache):
            kline = pd.read_feather(file_cache)
            if self.verbose:
                print(f"pro_bar: read cache {file_cache}")
        else:
            start_date_ = (pd.to_datetime(self.sdt) - timedelta(days=1000)).strftime('%Y%m%d')
            kline = ts.pro_bar(ts_code=ts_code, asset=asset, adj=adj, freq=freq,
                               start_date=start_date_, end_date=self.edt)
            kline = kline.sort_values('trade_date', ignore_index=True)
            kline['trade_date'] = pd.to_datetime(kline['trade_date'], format=self.date_fmt)
            kline['dt'] = kline['trade_date']
            kline['avg_price'] = kline['amount'] / kline['vol']
            update_bars_return(kline)
            kline.to_feather(file_cache)

        if start_date:
            kline = kline[kline['trade_date'] >= pd.to_datetime(start_date)]
        if end_date:
            kline = kline[kline['trade_date'] <= pd.to_datetime(end_date)]

        kline.reset_index(drop=True, inplace=True)
        if raw_bar:
            kline = format_kline(kline, freq=self.freq_map[freq])
        return kline

    def pro_bar_minutes(self, ts_code, sdt=None, edt=None, freq='60min', asset="E", adj=None, raw_bar=True):
        """获取分钟线

        https://tushare.pro/document/2?doc_id=109

        :param ts_code: 标的代码
        :param sdt: 开始时间，精确到分钟
        :param edt: 结束时间，精确到分钟
        :param freq: 分钟周期，可选值 1min, 5min, 15min, 30min, 60min
        :param asset: 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
        :param adj: 复权类型，None不复权，qfq:前复权，hfq:后复权
        :param raw_bar: 是否返回 RawBar 对象列表
        :return:
        """
        cache_path = self.api_path_map['pro_bar_minutes']
        file_cache = os.path.join(cache_path, f"pro_bar_minutes_{ts_code}#{asset}_{self.sdt}_{freq}_{adj}.feather")
        edt = self.edt if not edt else edt

        if not self.refresh and os.path.exists(file_cache):
            kline = pd.read_feather(file_cache)
            if self.verbose:
                print(f"pro_bar_minutes: read cache {file_cache}")
        else:
            klines = []
            end_dt = pd.to_datetime(self.edt)
            dt1 = pd.to_datetime(self.sdt)
            delta = timedelta(days=20*int(freq.replace("min", "")))
            dt2 = dt1 + delta
            while dt1 < end_dt:
                df = ts.pro_bar(ts_code=ts_code, asset=asset, freq=freq,
                                start_date=dt1.strftime(dt_fmt), end_date=dt2.strftime(dt_fmt))
                klines.append(df)
                dt1 = dt2
                dt2 = dt1 + delta
                if self.verbose:
                    print(f"pro_bar_minutes: {ts_code} - {asset} - {freq} - {dt1} - {dt2} - {len(df)}")

            df_klines = pd.concat(klines, ignore_index=True)
            kline = df_klines.drop_duplicates('trade_time')\
                .sort_values('trade_time', ascending=True, ignore_index=True)
            kline['trade_time'] = pd.to_datetime(kline['trade_time'], format=dt_fmt)
            kline['dt'] = kline['trade_time']
            float_cols = ['open', 'close', 'high', 'low', 'vol', 'amount']
            kline[float_cols] = kline[float_cols].astype('float32')
            kline['avg_price'] = kline['amount'] / kline['vol']

            # 删除9:30的K线
            kline['keep'] = kline['trade_time'].apply(lambda x: 0 if x.hour == 9 and x.minute == 30 else 1)
            kline = kline[kline['keep'] == 1]
            # 删除没有成交量的K线
            kline = kline[kline['vol'] > 0]
            kline.drop(['keep'], axis=1, inplace=True)

            start_date = pd.to_datetime(self.sdt)
            end_date = pd.to_datetime(self.edt)
            kline = kline[(kline['trade_time'] >= start_date) & (kline['trade_time'] <= end_date)]
            kline = kline.reset_index(drop=True)
            kline['trade_date'] = kline.trade_time.apply(lambda x: x.strftime(date_fmt))

            if asset == 'E':
                # https://tushare.pro/document/2?doc_id=28
                factor = pro.adj_factor(ts_code=ts_code, start_date=self.sdt, end_date=self.edt)
            elif asset == 'FD':
                # https://tushare.pro/document/2?doc_id=199
                factor = pro.fund_adj(ts_code=ts_code, start_date=self.sdt, end_date=self.edt)
            else:
                factor = pd.DataFrame()

            if len(factor) > 0:
                # 处理复权因子缺失的情况：前值填充
                df1 = pd.DataFrame({'trade_date': kline['trade_date'].unique().tolist()})
                factor = df1.merge(factor, on=['trade_date'], how='left').fillna(method='ffill')
                factor = factor.sort_values('trade_date', ignore_index=True)

            if self.verbose:
                print(f"pro_bar_minutes: {ts_code} - {asset} - 复权因子长度 = {len(factor)}")

            # 复权行情说明：https://tushare.pro/document/2?doc_id=146
            if len(factor) > 0 and adj and adj == 'qfq':
                # 前复权	= 当日收盘价 × 当日复权因子 / 最新复权因子
                latest_factor = factor.iloc[-1]['adj_factor']
                adj_map = {row['trade_date']: row['adj_factor'] for _, row in factor.iterrows()}
                for col in ['open', 'close', 'high', 'low']:
                    kline[col] = kline.apply(lambda x: x[col] * adj_map[x['trade_date']] / latest_factor, axis=1)

            if len(factor) > 0 and adj and adj == 'hfq':
                # 后复权	= 当日收盘价 × 当日复权因子
                adj_map = {row['trade_date']: row['adj_factor'] for _, row in factor.iterrows()}
                for col in ['open', 'close', 'high', 'low']:
                    kline[col] = kline.apply(lambda x: x[col] * adj_map[x['trade_date']], axis=1)

            update_bars_return(kline)
            kline.to_feather(file_cache)

        if sdt:
            kline = kline[kline['trade_time'] >= pd.to_datetime(sdt)]
        if edt:
            kline = kline[kline['trade_time'] <= pd.to_datetime(edt)]

        bars = kline.reset_index(drop=True)
        if raw_bar:
            bars = format_kline(bars, freq=self.freq_map[freq])
        return bars

    def stock_basic(self):
        """获取基础信息数据，包括股票代码、名称、上市日期、退市日期等

        https://tushare.pro/document/2?doc_id=25

        :return:
        """
        file_cache = os.path.join(self.cache_path, f"stock_basic.feather")
        if not self.refresh and os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
        else:
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
            df.to_feather(file_cache)
        return df

    def trade_cal(self):
        """https://tushare.pro/document/2?doc_id=26"""
        file_cache = os.path.join(self.cache_path, f"trade_cal.feather")
        if os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
        else:
            df = pro.trade_cal(exchange='', start_date='19900101', end_date="20300101")
            df = df.sort_values('cal_date', ascending=True).reset_index(drop=True)
            df.to_feather(file_cache)
        return df

    def hk_hold(self, trade_date='20190625'):
        """沪深港股通持股明细

        https://tushare.pro/document/2?doc_id=188
        """
        cache_path = self.api_path_map['hk_hold']
        trade_date = pd.to_datetime(trade_date).strftime("%Y%m%d")
        file_cache = os.path.join(cache_path, f"hk_hold_{trade_date}.feather")
        if os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
        else:
            df = pro.hk_hold(trade_date=trade_date)
            if df.empty:
                return df
            df.to_feather(file_cache)
        return df

    def cctv_news(self, date='20190625'):
        """新闻联播

        https://tushare.pro/document/2?doc_id=154
        """
        cache_path = self.api_path_map['cctv_news']
        date = pd.to_datetime(date).strftime("%Y%m%d")
        file_cache = os.path.join(cache_path, f"cctv_news_{date}.feather")
        if os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
        else:
            df = pro.cctv_news(date=date)
            if df.empty:
                return df
            df.to_feather(file_cache)
        return df

    def index_weight(self, index_code: str, trade_date: str):
        """指数成分和权重

        https://tushare.pro/document/2?doc_id=96
        """
        trade_date = pd.to_datetime(trade_date)
        cache_path = self.api_path_map['index_weight']
        file_cache = os.path.join(cache_path, f"index_weight_{index_code}_{trade_date.strftime('%Y%m')}.feather")

        if os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
        else:
            start_date = (trade_date.replace(day=1) - timedelta(days=31)).strftime('%Y%m%d')
            end_date = (trade_date.replace(day=1) + timedelta(days=31)).strftime('%Y%m%d')
            df = pro.index_weight(index_code=index_code, start_date=start_date, end_date=end_date)
            df = df.drop_duplicates('con_code', ignore_index=True)
            if df.empty:
                return df

            df.to_feather(file_cache)
        return df

    def limit_list(self, trade_date: str):
        """https://tushare.pro/document/2?doc_id=198

        :param trade_date: 交易日期
        :return: 每日涨跌停统计
        """
        trade_date = pd.to_datetime(trade_date).strftime("%Y%m%d")
        cache_path = self.api_path_map['limit_list']
        file_cache = os.path.join(cache_path, f"limit_list_{trade_date}.pkl")

        if os.path.exists(file_cache):
            df = pd.read_pickle(file_cache)
            if not df.empty:
                return df

        df = pro.limit_list(trade_date=trade_date)
        df.to_pickle(file_cache)
        return df

    @deprecated(reason='推荐使用 daily_basic_new 替代', version='0.9.0')
    def daily_basic(self, ts_code: str, start_date: str, end_date: str):
        """每日指标

        https://tushare.pro/document/2?doc_id=32
        """
        cache_path = self.api_path_map['daily_basic']
        file_cache = os.path.join(cache_path, f"daily_basic_{ts_code}.pkl")

        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            start_date_ = (pd.to_datetime(self.sdt) - timedelta(days=1000)).strftime('%Y%m%d')
            df = pro.daily_basic(ts_code=ts_code, start_date=start_date_, end_date="20300101")
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            io.save_pkl(df, file_cache)

        df = df[(df.trade_date >= pd.to_datetime(start_date)) & (df.trade_date <= pd.to_datetime(end_date))]
        return df

    # ------------------------------------以下是 CZSC 加工接口----------------------------------------------

    def daily_basic_new(self, trade_date: str):
        """股票每日指标接口整合

        每日指标：https://tushare.pro/document/2?doc_id=32
        备用列表：https://tushare.pro/document/2?doc_id=262

        :param trade_date: 交易日期
        :return:
        """
        trade_date = pd.to_datetime(trade_date).strftime("%Y%m%d")
        cache_path = self.api_path_map['daily_basic_new']
        file_cache = os.path.join(cache_path, f"bak_basic_new_{trade_date}.pkl")
        if os.path.exists(file_cache):
            df = pd.read_pickle(file_cache)
            if not df.empty:
                return df

        df1 = pro.bak_basic(trade_date=trade_date)
        df2 = pro.daily_basic(trade_date=trade_date)
        df1 = df1[['trade_date', 'ts_code', 'name', 'industry', 'area',
                   'total_assets', 'liquid_assets',
                   'fixed_assets', 'reserved', 'reserved_pershare', 'eps', 'bvps',
                   'list_date', 'undp', 'per_undp', 'rev_yoy', 'profit_yoy', 'gpr', 'npr',
                   'holder_num']]
        df = df2.merge(df1, on=['ts_code', 'trade_date'], how='left')
        df['is_st'] = df['name'].str.contains('ST')
        df.to_pickle(file_cache)
        return df

    def get_all_ths_members(self, exchange="A", type_="N"):
        """获取同花顺A股全部概念列表"""
        file_cache = os.path.join(self.cache_path, f"{exchange}_{type_}_ths_members.feather")
        if not self.refresh and os.path.exists(file_cache):
            df = pd.read_feather(file_cache)
        else:
            concepts = self.ths_index(exchange, type_)
            concepts = concepts.to_dict('records')

            res = []
            for concept in tqdm(concepts, desc='get_all_ths_members'):
                _df = self.ths_member(ts_code=concept['ts_code'])
                _df['概念名称'] = concept['name']
                _df['概念代码'] = concept['ts_code']
                _df['概念类别'] = concept['type']
                res.append(_df)
                time.sleep(0.3)

            df = pd.concat(res, ignore_index=True)
            df.to_feather(file_cache)
        return df

    def get_next_trade_dates(self, date, n: int = 1, m: int = None):
        """获取将来的交易日期

        如果 m = None，返回基准日期后第 n 个交易日；否则返回基准日期后第 n ~ m 个交易日

        :param date: 基准日期
        :param n:
        :param m:
        :return:
        """
        date = pd.to_datetime(date).strftime("%Y%m%d")
        trade_cal = self.trade_cal()
        trade_cal = trade_cal[trade_cal.is_open == 1]
        trade_dates = trade_cal.cal_date.to_list()
        assert date in trade_dates, "基准日期 date 必须是开市交易日期"

        i = trade_dates.index(date)
        if not m:
            ntd = trade_dates[i + n]
            return ntd
        else:
            assert m > n > 0 or m < n < 0, "abs(m) 必须大于 abs(n)"
            if m > n > 0:
                ntd_list = trade_dates[i+n: i+m]
            else:
                ntd_list = trade_dates[i+m: i+n]
            return ntd_list

    def get_dates_span(self, sdt: str, edt: str, is_open: bool = True) -> List[str]:
        """获取日期区间列表

        :param sdt: 开始日期
        :param edt: 结束日期
        :param is_open: 是否是交易日
        :return: 日期区间列表
        """
        sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
        edt = pd.to_datetime(edt).strftime("%Y%m%d")

        trade_cal = self.trade_cal()
        if is_open:
            trade_cal = trade_cal[trade_cal['is_open'] == 1]

        trade_dates = [x for x in trade_cal['cal_date'] if edt >= x >= sdt]
        return trade_dates

    def stocks_daily_bars(self, sdt="20190101", edt="20220218", adj='hfq'):
        """读取A股全部历史日线

        :param sdt: 开始日期
        :param edt: 结束日期
        :param adj: 复权类型
        :return:
        """
        cache_path = self.api_path_map['stocks_daily_bars']
        file_cache = os.path.join(cache_path, f"stocks_daily_bars_{sdt}_{edt}_{adj}.feather")
        if os.path.exists(file_cache):
            print(f"stocks_daily_bars :: read cache from {file_cache}")
            df = pd.read_feather(file_cache)
            return df

        stocks = self.stock_basic()

        def __is_one_line(row_):
            """判断 row_ 是否是一字板"""
            if row_['open'] == row_['close'] == \
                    row_['high'] == row_['low'] and row_['b1b']:
                if row_['b1b'] > 500:
                    return 1
                if row_['b1b'] < -500:
                    return -1
            return 0

        results = []
        for row in tqdm(stocks.to_dict('records'), desc="stocks_daily_bars"):
            ts_code = row['ts_code']
            try:
                n_bars: pd.DataFrame = self.pro_bar(ts_code, sdt, edt, freq='D', asset='E', adj=adj, raw_bar=False)
                # 计算下期一字板
                n_bars['当期一字板'] = n_bars.apply(__is_one_line, axis=1)
                n_bars['下期一字板'] = n_bars['当期一字板'].shift(-1)
                results.append(n_bars)
            except:
                continue
        df = pd.concat(results, ignore_index=True)

        # 涨跌停判断
        def __is_zdt(row_):
            # 涨停描述：收盘价等于最高价，且当日收益 b1b 大于700BP
            if row_['close'] == row_['high'] and row_['b1b'] > 700:
                return 1
            elif row_['close'] == row_['low']:
                return -1
            else:
                return 0

        df['zdt'] = df.apply(__is_zdt, axis=1)
        float_cols = [k for k, v in df.dtypes.to_dict().items() if v.name.startswith('float')]
        df[float_cols] = df[float_cols].astype('float32')

        df.to_feather(file_cache)
        return df

    def stocks_daily_basic_new(self, sdt: str, edt: str):
        """读取A股 sdt ~ edt 时间区间的全部历史 daily_basic_new

        :param sdt: 开始日期
        :param edt: 结束日期
        :return:
        """
        cache_path = self.api_path_map['stocks_daily_basic_new']
        file_cache = os.path.join(cache_path, f"stocks_daily_basic_new_{sdt}_{edt}.feather")
        if os.path.exists(file_cache):
            print(f"stocks_daily_basic_new :: read cache from {file_cache}")
            df = pd.read_feather(file_cache)
            return df

        dates = self.get_dates_span(sdt, edt, is_open=True)
        results = [self.daily_basic_new(d) for d in tqdm(dates, desc='stocks_daily_basic_new')]
        dfb = pd.concat(results, ignore_index=True)
        dfb['trade_date'] = pd.to_datetime(dfb['trade_date'])
        dfb['上市天数'] = (dfb['trade_date'] - pd.to_datetime(dfb['list_date'], errors='coerce')).apply(lambda x: x.days)
        dfb.to_feather(file_cache)
        return dfb
