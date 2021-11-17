# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:18
describe: A股市场感应器若干，主要作为编写感应器的示例
"""
import os.path
import traceback
import inspect
from datetime import timedelta, datetime
from collections import OrderedDict, Counter
import pandas as pd
from tqdm import tqdm
from typing import Callable
from czsc.objects import Event
from czsc.data.ts_cache import TsDataCache, Freq
from czsc.sensors.utils import get_index_beta, generate_signals, max_draw_down
from czsc.utils import WordWriter


class StocksDaySensor:
    """以日线为基础周期的强势股票感应器

    输入：市场个股全部行情、概念板块成分信息
    输出：强势个股列表以及概念板块分布
    """

    def __init__(self,
                 dc: TsDataCache,
                 get_signals: Callable,
                 get_event: Callable,
                 params: dict = None):

        self.name = self.__class__.__name__
        self.version = "V20211117"
        self.data = OrderedDict()
        self.get_signals = get_signals
        self.get_event = get_event
        self.event: Event = get_event()
        self.base_freq = Freq.D.value
        self.freqs = [Freq.W.value, Freq.M.value]

        if params:
            self.params = params
        else:
            self.params = {
                "validate_sdt": "20210101",
                "validate_edt": "20211112",
                "min_total_mv": 1e6,    # 最小总市值，单位为万元，1e6万元 = 100亿
                "fc_top_n": 40,         # 板块效应 - 选择出现数量最多的 top_n 概念
                'fc_min_n': 4           # 单股票至少有 min_n 概念在 top_n 中
            }

        self.dc = dc
        self.betas = ['000001.SH', '000016.SH', '000905.SH', '000300.SH', '399001.SZ', '399006.SZ']
        self.all_cache = dict()
        self.res_cache = dict()

        self.sdt = self.params['validate_sdt']
        self.edt = self.params['validate_edt']

    def get_share_strong_days(self, ts_code: str, name: str):
        """获取单个标的全部强势信号日期"""
        dc = self.dc
        event = self.event
        sdt = self.sdt
        edt = self.edt

        start_date = pd.to_datetime(self.sdt) - timedelta(days=3000)
        bars = dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=edt, freq='D', asset="E", raw_bar=True)
        df = dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=edt, freq='D', asset="E", raw_bar=False)
        nb_dicts = {row['trade_date'].strftime("%Y%m%d"): row for row in df.to_dict("records")}

        signals = generate_signals(bars, sdt, self.base_freq, self.freqs, self.get_signals)

        results = []
        for s in signals:
            m, f = event.is_match(s)
            if m:
                res = {
                    'ts_code': ts_code,
                    'name': name,
                    'reason': f,
                }
                nb_info = nb_dicts.get(s['dt'].strftime("%Y%m%d"), None)
                if not nb_info:
                    print(f"not match nb info: {nb_info}")

                res.update(nb_info)
                results.append(res)

        df_res = pd.DataFrame(results)

        if df_res.empty:
            print(f"{ts_code} | {name} | empty")
        else:
            df_ = dc.daily_basic(ts_code, sdt, dc.edt)
            df_['trade_date'] = pd.to_datetime(df_['trade_date'])
            df_res = df_res.merge(df_[['trade_date', 'total_mv']], on='trade_date', how='left')
            df_res = df_res[df_res['total_mv'] >= self.params['min_total_mv']]
            print(f"\n{ts_code} | {name} | {len(df_res)} | {df_res.n1b.mean()} | {int(df_res.n1b.sum())}")

        self.all_cache[ts_code] = df_res

    def filter_shares_by_concepts(self, dfg, top_n=20, min_n=3):
        """使用板块效应过滤某天的选股结果

        :param dfg: 某一天的选股结果
        :param top_n: 选取前 n 个密集概念
        :param min_n: 单股票至少要有 n 个概念在 top_n 中
        :return:
        """
        dc = self.dc
        ths_members = dc.get_all_ths_members()
        ths_members = ths_members[ths_members['概念类别'] == 'N']
        ths_members = ths_members[~ths_members['概念名称'].isin([
            'MSCI概念', '沪股通', '深股通', '融资融券', '上证180成份股', '央企国资改革',
            '标普道琼斯A股', '中证500成份股', '上证380成份股', '沪深300样本股',
        ])]

        ths_concepts = ths_members[ths_members.code.isin(dfg.ts_code)]
        all_concepts = ths_concepts['概念名称'].to_list()
        key_concepts = [k for k, v in Counter(all_concepts).most_common(top_n)]

        sel = ths_concepts[ths_concepts['概念名称'].isin(key_concepts)]
        ts_codes = [k for k, v in Counter(sel.code).most_common() if v >= min_n]
        dfg = dfg[dfg.ts_code.isin(ts_codes)]
        dfg['概念板块'] = dfg.ts_code.apply(lambda x: ths_concepts[ths_concepts.code == x]['概念名称'].to_list())
        dfg['概念数量'] = dfg['概念板块'].apply(len)

        return dfg, key_concepts

    def validate(self):
        """验证传感器在一段时间内的表现"""
        dc = self.dc
        stocks = dc.stock_basic()
        sdt = self.params['validate_sdt']
        edt = self.params['validate_edt']

        for row in tqdm(stocks.to_dict('records'), desc="validate"):
            ts_code = row['ts_code']
            name = row['name']
            try:
                self.get_share_strong_days(ts_code, name)
            except:
                print(f"get_share_strong_days error: {ts_code}, {name}")
                traceback.print_exc()

        res = []
        for ts_code, x in self.all_cache.items():
            if x.empty:
                continue
            x = x[pd.to_datetime(sdt) <= x['trade_date']]
            x = x[x['trade_date'] <= pd.to_datetime(edt)]
            if not x.empty:
                res.append(x)

        df = pd.concat(res, ignore_index=True)

        trade_cal = dc.trade_cal()
        trade_cal = trade_cal[trade_cal.is_open == 1]
        trade_dates = trade_cal.cal_date.to_list()

        results = []
        detail = []
        holds = []

        for trade_date, dfg in df.groupby('trade_date'):
            if dfg.empty:
                print(f"{trade_date} 选股结果为空")
                continue

            if self.params['fc_top_n'] > 0:
                top_n = self.params['fc_top_n']
                min_n = self.params['fc_min_n']
                dfg, key_concepts = self.filter_shares_by_concepts(dfg, top_n=top_n, min_n=min_n)
            else:
                key_concepts = ""

            res = {'trade_date': trade_date, "key_concepts": key_concepts, 'number': len(dfg)}
            res.update(dfg[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']].mean().to_dict())
            results.append(res)
            detail.append(dfg)

            # 构建持仓明显
            try:
                hold = dfg.copy()
                hold['成分日期'] = trade_dates[trade_dates.index(trade_date.strftime("%Y%m%d")) + 1]
                hold['持仓权重'] = 0.98 / len(dfg)
                hold.rename({'ts_code': "证券代码", "close": "交易价格"}, inplace=True, axis=1)
                hold = hold[['证券代码', '持仓权重', '交易价格', '成分日期']]
                hold['成分日期'] = pd.to_datetime(hold['成分日期']).apply(lambda x: x.strftime("%Y/%m/%d"))
                holds.append(hold)
            except:
                print(f"fail on {trade_date}, {dfg}")
                traceback.print_exc()

        df_detail = pd.concat(detail)
        df_holds = pd.concat(holds, ignore_index=True)
        df_merged = pd.DataFrame(results)
        df_merged['trade_date'] = pd.to_datetime(df_merged['trade_date'])
        return df_detail, df_merged, df_holds

    def get_index_beta(self):
        """获取基准指数的Beta"""
        dc = self.dc
        sdt = self.params['validate_sdt']
        edt = self.params['validate_edt']

        beta = {}
        for ts_code in self.betas:
            df = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt,
                            freq='D', asset="I", raw_bar=False)
            beta[ts_code] = df
        return beta

    def report_performance(self, results_path, file_docx='股票选股强度验证.docx'):
        """撰写报告"""
        dc = self.dc
        sdt = self.sdt
        edt = self.edt

        writer = WordWriter(file_docx)
        if not os.path.exists(file_docx):
            writer.add_title("股票选股强度验证")

        writer.add_page_break()
        writer.add_heading(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {self.event.name}", level=1)

        writer.add_heading("参数配置", level=2)
        writer.add_df_table(pd.DataFrame({"参数名称": list(self.params.keys()), '参数值': list(self.params.values())}))
        writer.add_paragraph(f"测试方法描述：{self.event.name}")
        writer.add_paragraph(f"信号计算函数：\n{inspect.getsource(self.get_signals)}")
        writer.add_paragraph(f"事件具体描述：\n{inspect.getsource(self.get_event)}")
        writer.save()

        writer.add_heading("测试结果", level=2)

        df_detail, df_merged, df_holds = self.validate()
        beta = get_index_beta(dc, sdt, edt, self.betas)

        df_n1b = pd.DataFrame()
        for name, df_ in beta.items():
            df_n1b['trade_date'] = pd.to_datetime(df_.trade_date.to_list())
            df_n1b[name] = df_.n1b.to_list()

        df_ = df_merged[['trade_date', 'number', 'n1b']]
        df_.rename({'n1b': 'selector'}, axis=1, inplace=True)
        df_.reset_index(drop=True, inplace=True)
        df_n1b = df_n1b.merge(df_, on='trade_date', how='left')
        df_n1b.fillna(0, inplace=True)

        os.makedirs(results_path, exist_ok=True)
        df_detail.to_excel(os.path.join(results_path, f"选股结果_{sdt}_{edt}.xlsx"), index=False)
        df_holds.to_excel(os.path.join(results_path, f"持仓明细_{sdt}_{edt}.xlsx"), index=False)
        df_merged.to_excel(os.path.join(results_path, f"每日统计_{sdt}_{edt}.xlsx"), index=False)
        df_n1b.to_excel(os.path.join(results_path, f"资金曲线_{sdt}_{edt}.xlsx"), index=False)

        f = pd.ExcelWriter(os.path.join(results_path, f"基准曲线_{sdt}_{edt}.xlsx"))
        for name, df_ in beta.items():
            df_.to_excel(f, index=False, sheet_name=name)
        f.close()

        mdd_info = {}
        for col in self.betas + ['selector']:
            df_n1b[f"{col}_curve"] = df_n1b[col].cumsum()
            df_n1b[f"{col}_curve"] += 10000
            start_i, end_i, mdd = max_draw_down(df_n1b[col].to_list())

            start_dt = df_n1b.iloc[start_i]['trade_date']
            end_dt = df_n1b.iloc[end_i]['trade_date']
            msg = f"{col} mdd: {start_dt.strftime('%Y%m%d')} - {end_dt.strftime('%Y%m%d')} - {mdd}；nv = {int(df_n1b[col].sum())}"
            print(msg)
            writer.add_paragraph(msg)
            mdd_info[col] = {
                "start_date": start_dt,
                "end_date": end_dt,
                "mdd": mdd,
            }

        df_n1b.to_excel(os.path.join(results_path, f"资金曲线_{sdt}_{edt}.xlsx"), index=False)
        writer.save()

        self.res_cache = {
            "detail": df_detail,
            "holds": df_holds,
            "merged": df_merged,
            "curve": df_n1b,
            "beta": beta
        }
        return df_holds


