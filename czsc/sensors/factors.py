# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:39
describe: 事件性能分析
"""
import os
import os.path
import traceback
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
from tqdm import tqdm
from typing import Callable, List
from czsc.objects import Factor
from czsc.data.ts_cache import TsDataCache
from czsc.sensors.utils import generate_signals
from czsc.utils import io
from czsc.utils import WordWriter


plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class FactorsSensor:
    """因子（Factor）感应器：分析各种信号和因子的表现"""

    def __init__(self,
                 results_path: str,
                 sdt: str,
                 edt: str,
                 dc: TsDataCache,
                 base_freq: str,
                 freqs: List[str],
                 get_signals: Callable,
                 get_factors: Callable):

        self.name = self.__class__.__name__
        self.version = "V20211213"
        os.makedirs(results_path, exist_ok=True)
        self.results_path = results_path
        self.sdt = sdt
        self.edt = edt

        self.get_signals = get_signals
        self.get_factors = get_factors
        self.factors: List[Factor] = get_factors()
        self.base_freq = base_freq
        self.freqs = freqs
        self.file_docx = os.path.join(results_path, f'factors_sensor_{sdt}_{edt}.docx')
        self.writer = WordWriter(self.file_docx)

        self.dc = dc
        self.betas = ['000001.SH', '000016.SH', '000905.SH', '000300.SH', '399001.SZ', '399006.SZ']

        self.file_sf = os.path.join(results_path, f'factors_{sdt}_{edt}.pkl')
        self.signals_path = os.path.join(results_path, 'signals')
        os.makedirs(self.signals_path, exist_ok=True)
        if os.path.exists(self.file_sf):
            self.sf = io.read_pkl(self.file_sf)
        else:
            self.sf = self.get_stock_factors()
            io.save_pkl(self.sf, self.file_sf)

    def get_share_factors(self, ts_code: str, name: str):
        """获取单个标的因子信息"""
        dc = self.dc
        sdt = self.sdt
        edt = self.edt
        factors = self.factors

        start_date = pd.to_datetime(self.sdt) - timedelta(days=3000)
        bars = dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=edt, freq='D', asset="E", raw_bar=True)
        n_bars = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq='D', asset="E", raw_bar=False)
        nb_dicts = {row['trade_date'].strftime("%Y%m%d"): row for row in n_bars.to_dict("records")}
        signals = generate_signals(bars, sdt, self.base_freq, self.freqs, self.get_signals)

        results = []
        for s in signals:
            row = {'name': name, 'ts_code': ts_code}
            for factor in factors:
                row[factor.name] = factor.is_match(s)

            nb_info = nb_dicts.get(s['dt'].strftime("%Y%m%d"), None)
            row.update(nb_info)
            results.append(row)

        df_res = pd.DataFrame(results)
        if df_res.empty:
            return df_res

        df_res = df_res[pd.to_datetime(sdt) <= df_res['trade_date']]
        df_res = df_res[df_res['trade_date'] <= pd.to_datetime(edt)]

        # 加入总市值
        df_ = dc.daily_basic(ts_code, sdt, dc.edt)
        df_['trade_date'] = pd.to_datetime(df_['trade_date'])
        df_res = df_res.merge(df_[['trade_date', 'total_mv']], on='trade_date', how='left')
        return signals, df_res

    def get_stock_factors(self):
        """获取全部股票的因子信息"""
        stocks = self.dc.stock_basic()

        all_factors = []
        for row in tqdm(stocks.to_dict('records'), desc="get_stock_factors"):
            ts_code = row['ts_code']
            name = row['name']
            try:
                signals, factors = self.get_share_factors(ts_code, name)
                all_factors.append(factors)
                file_signals = os.path.join(self.signals_path, f'{ts_code}.pkl')
                io.save_pkl(signals, file_signals)
            except:
                print(f"get_share_factors error: {ts_code}, {name}")
                traceback.print_exc()

        df_factors = pd.concat(all_factors, ignore_index=True)
        return df_factors

    def validate_performance(self):
        factors = self.factors
        sf = self.sf
        results = [{
            "name": "全市场", "count": len(sf), 'n1b': sf.n1b.mean(), 'n2b': sf.n2b.mean(),
            'n3b': sf.n3b.mean(), 'n5b': sf.n5b.mean(), 'n10b': sf.n10b.mean(), 'n20b': sf.n20b.mean()
        }]

        for factor in factors:
            df = sf[sf[factor.name]]
            row = {"name": factor.name, "count": len(df)}
            row.update(df[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']].mean().to_dict())
            results.append(row)
        df_nb_info = pd.DataFrame(results)
        df_nb_info.to_excel(os.path.join(self.results_path, f"factors_nb_info.xlsx"), index=False)
