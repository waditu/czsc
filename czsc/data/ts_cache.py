# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/24 16:12
describe: Tushare 数据缓存
"""
import shutil
import pandas as pd

from .ts import *
from ..utils import io


class TsDataCache:
    """Tushare 数据缓存"""
    def __init__(self, data_path, sdt, edt, verbose=False):
        """

        :param data_path: 数据路径
        :param sdt: 缓存开始时间
        :param edt: 缓存结束时间
        :param verbose: 是否显示详细信息
        """
        self.date_fmt = "%Y%m%d"
        self.verbose = verbose
        self.sdt = pd.to_datetime(sdt).strftime(self.date_fmt)
        self.edt = pd.to_datetime(edt).strftime(self.date_fmt)
        self.data_path = data_path
        self.prefix = "TS_CACHE"
        self.name = f"{self.prefix}_{self.sdt}_{self.edt}"
        self.cache_path = os.path.join(self.data_path, self.name)
        os.makedirs(self.cache_path, exist_ok=True)
        self.pro = pro

        self.freq_map = {
            "D": Freq.D,
            "W": Freq.W,
            "M": Freq.M,
        }

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
    def ths_daily(self, ts_code, start_date, end_date, raw_bar=True):
        """获取同花顺概念板块的日线行情"""
        file_cache = os.path.join(self.cache_path, f"{ts_code}.pkl")
        if os.path.exists(file_cache):
            kline = io.read_pkl(file_cache)
            if self.verbose:
                print(f"ths_daily: read cache {file_cache}")
        else:
            kline = pro.ths_daily(ts_code=ts_code, start_date=self.sdt, end_date=self.edt,
                                  fields='ts_code,trade_date,open,close,high,low,vol')
            kline = kline.sort_values('trade_date', ignore_index=True)

            for bar_number in (1, 2, 3, 5, 10, 20):
                n_col_name = 'n' + str(bar_number) + 'b'
                kline[n_col_name] = (kline['close'].shift(-bar_number) / kline['close'] - 1) * 10000

            io.save_pkl(kline, file_cache)

        kline['trade_date'] = pd.to_datetime(kline['trade_date'], format=self.date_fmt)
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        bars = kline[(kline['trade_date'] >= start_date) & (kline['trade_date'] <= end_date)]
        bars.reset_index(drop=True, inplace=True)
        if raw_bar:
            bars = format_kline(bars, freq=Freq.D)
        return bars

    def ths_index(self, exchange="A"):
        """获取同花顺概念

        https://tushare.pro/document/2?doc_id=259
        :param exchange:
        :return:
        """
        file_cache = os.path.join(self.cache_path, f"ths_index_{exchange}.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
            if self.verbose:
                print(f"ths_index: read cache {file_cache}")
        else:
            df = pro.ths_index(exchange=exchange)
            io.save_pkl(df, file_cache)
        return df

    def ths_member(self, ts_code):
        """获取同花顺概念成分股

        https://tushare.pro/document/2?doc_id=261
        :param ts_code:
        :return:
        """
        file_cache = os.path.join(self.cache_path, f"ths_members_{ts_code}.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.ths_member(ts_code=ts_code,
                                fields="ts_code,code,name,weight,in_date,out_date,is_new")
            io.save_pkl(df, file_cache)
        return df

    def pro_bar(self, ts_code, start_date, end_date, freq='D', asset="E", raw_bar=True):
        """获取日线以上数据

        https://tushare.pro/document/2?doc_id=109

        :param ts_code:
        :param start_date:
        :param end_date:
        :param freq:
        :param asset: 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
        :param raw_bar:
        :return:
        """
        file_cache = os.path.join(self.cache_path, f"{ts_code}_{asset}_{freq}.pkl")
        if os.path.exists(file_cache):
            kline = io.read_pkl(file_cache)
            if self.verbose:
                print(f"pro_bar: read cache {file_cache}")
        else:
            start_date = (pd.to_datetime(self.sdt) - timedelta(days=1000)).strftime('%Y%m%d')
            kline = ts.pro_bar(ts_code=ts_code, asset=asset, adj='qfq', freq=freq,
                               start_date=start_date, end_date=self.edt)
            kline = kline.sort_values('trade_date', ignore_index=True)

            for bar_number in (1, 2, 3, 5, 10, 20):
                n_col_name = 'n' + str(bar_number) + 'b'
                kline[n_col_name] = (kline['close'].shift(-bar_number) / kline['close'] - 1) * 10000
                kline[n_col_name] = kline[n_col_name].round(4)

            io.save_pkl(kline, file_cache)

        kline['trade_date'] = pd.to_datetime(kline['trade_date'], format=self.date_fmt)
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        bars = kline[(kline['trade_date'] >= start_date) & (kline['trade_date'] <= end_date)]
        bars.reset_index(drop=True, inplace=True)
        if raw_bar:
            bars = format_kline(bars, freq=self.freq_map[freq])
        return bars

    def index_classify(self, level="L1"):
        """
        https://tushare.pro/document/2?doc_id=181

        :param level:
        :return:
        """
        file_cache = os.path.join(self.cache_path, f"sw_index_{level}.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.index_classify(level=level, src='SW')
            io.save_pkl(df, file_cache)
        return df

    def index_member(self, index_code):
        """
        https://tushare.pro/document/2?doc_id=182

        :param index_code:
        :return:
        """
        file_cache = os.path.join(self.cache_path, f"sw_members_{index_code}.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.index_member(index_code=index_code)
            io.save_pkl(df, file_cache)
        return df

    def stock_basic(self):
        """
        https://tushare.pro/document/2?doc_id=25

        :return:
        """
        file_cache = os.path.join(self.cache_path, f"stock_basic.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.stock_basic(exchange='', list_status='L',
                                 fields='ts_code,symbol,name,area,industry,list_date')
            io.save_pkl(df, file_cache)
        return df

    def trade_cal(self):
        """https://tushare.pro/document/2?doc_id=26"""
        file_cache = os.path.join(self.cache_path, f"trade_cal.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.trade_cal(exchange='', start_date='19900101', end_date=datetime.now().strftime("%Y%m%d"))
            io.save_pkl(df, file_cache)
        return df

    def hk_hold(self, trade_date='20190625'):
        """沪深港股通持股明细

        https://tushare.pro/document/2?doc_id=188
        """
        trade_date = pd.to_datetime(trade_date).strftime("%Y%m%d")
        file_cache = os.path.join(self.cache_path, f"hk_hold_{trade_date}.pkl")

        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.hk_hold(trade_date=trade_date)
            io.save_pkl(df, file_cache)
        return df

    def cctv_news(self, date='20190625'):
        """新闻联播

        https://tushare.pro/document/2?doc_id=154
        """
        date = pd.to_datetime(date).strftime("%Y%m%d")
        file_cache = os.path.join(self.cache_path, f"cctv_news_{date}.pkl")

        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            df = pro.cctv_news(date=date)
            io.save_pkl(df, file_cache)
        return df

    # ------------------------------------CZSC 加工接口----------------------------------------------

    def get_all_ths_members(self):
        """获取同花顺A股全部概念列表"""
        file_cache = os.path.join(self.cache_path, "all_ths_members.pkl")
        if os.path.exists(file_cache):
            df = io.read_pkl(file_cache)
        else:
            concepts = self.ths_index(exchange='A')
            concepts = concepts.to_dict('records')

            res = []
            for concept in tqdm(concepts, desc='get_all_ths_members'):
                _df = self.ths_member(ts_code=concept['ts_code'])
                _df['概念名称'] = concept['name']
                _df['概念代码'] = concept['ts_code']
                res.append(_df)
                time.sleep(0.3)

            df = pd.concat(res, ignore_index=True)
            io.save_pkl(df, file_cache)
        return df

