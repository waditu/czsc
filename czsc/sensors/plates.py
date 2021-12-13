# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 21:43
describe: 概念、行业、指数等股票聚类板块感应器

三个问题：
1）如何找出引领大盘的概念、行业、指数
2）板块内股票相比于板块走势，划分强中弱
3）根据指数强弱进行账户总仓位控制
"""
import os
import traceback
import inspect
from datetime import timedelta, datetime
import pandas as pd
from tqdm import tqdm
from typing import Callable
from czsc.utils import WordWriter
from czsc.utils import io
from czsc.data.ts_cache import TsDataCache, Freq
from czsc.sensors.utils import get_index_beta, generate_signals, turn_over_rate, max_draw_down


class ThsConceptsSensor:
    """
    输入：同花顺概念列表；同花顺概念日线行情
    输出：每一个交易日的同花顺强势概念
    """
    def __init__(self,
                 results_path: str,
                 sdt: str,
                 edt: str,
                 dc: TsDataCache,
                 get_signals: Callable,
                 get_event: Callable,
                 ths_index_type='N',
                 verbose: bool = False):
        """

        :param results_path: 结果保存路径
        :param sdt: 开始日期
        :param edt: 结束日期
        :param dc: 数据缓存对象
        :param get_signals: 信号获取函数
        :param get_event: 事件定义函数
        :param ths_index_type: 同花顺指数类型 N-板块指数 I-行业指数 S-同花顺特色指数
        :param verbose: 是否返回更详细的执行过程
        """
        self.name = self.__class__.__name__
        self.dc = dc
        self.get_signals = get_signals
        self.get_event = get_event
        self.event = get_event()
        self.base_freq = Freq.D.value
        self.freqs = [Freq.W.value, Freq.M.value]
        self.dc = dc
        self.ths_index_type = ths_index_type
        self.verbose = verbose
        self.cache = dict()
        self.results_path = results_path
        os.makedirs(self.results_path, exist_ok=True)

        self.sdt = sdt
        self.edt = edt
        self.file_docx = os.path.join(results_path, f'{self.event.name}_{self.ths_index_type}_{sdt}_{edt}.docx')
        writer = WordWriter(self.file_docx)
        if not os.path.exists(self.file_docx):
            writer.add_title(f"同花顺指数（{self.ths_index_type}）感应器报告")
            writer.add_page_break()
            writer.add_heading(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {self.event.name}", level=1)

            writer.add_heading("参数配置", level=2)
            writer.add_paragraph(f"测试方法描述：{self.event.name}")
            writer.add_paragraph(f"测试起止日期：{sdt} ~ {edt}")
            writer.add_paragraph(f"信号计算函数：\n{inspect.getsource(self.get_signals)}")
            writer.add_paragraph(f"事件具体描述：\n{inspect.getsource(self.get_event)}")
            writer.save()
        self.writer = writer
        self.file_ssd = os.path.join(results_path, f'ths_all_strong_days_{self.ths_index_type}.pkl')
        if os.path.exists(self.file_ssd):
            self.ssd, self.cache = io.read_pkl(self.file_ssd)
        else:
            self.ssd = self.get_all_strong_days()
            io.save_pkl([self.ssd, self.cache], self.file_ssd)

        self.betas = get_index_beta(dc, sdt, edt, freq='D',
                                    indices=['000001.SH', '000016.SH', '000905.SH',
                                             '000300.SH', '399001.SZ', '399006.SZ'])

    def get_strong_days(self, ts_code, name):
        """获取单个概念的强势日期

        :param ts_code: 同花顺概念代码
        :param name: 同花顺概念名称
        :return:
        """
        dc = self.dc
        event = self.event
        sdt = self.sdt
        edt = self.edt
        start_date = pd.to_datetime(sdt) - timedelta(days=3000)
        bars = dc.ths_daily(ts_code=ts_code, start_date=start_date, end_date=edt, raw_bar=True)
        n_bars = dc.ths_daily(ts_code=ts_code, start_date=start_date, end_date=edt, raw_bar=False)
        nb_dicts = {row['trade_date'].strftime("%Y%m%d"): row for row in n_bars.to_dict("records")}

        signals = generate_signals(bars, sdt, base_freq='日线', freqs=['周线', '月线'], get_signals=self.get_signals)
        results = []
        for s in signals:
            m, f = event.is_match(s)
            if m:
                res = {'ts_code': ts_code, 'name': name, 'reason': f}
                nb_info = nb_dicts.get(s['dt'].strftime("%Y%m%d"), None)
                if not nb_info:
                    print(f"not match nb info: {nb_info}")

                res.update(nb_info)
                results.append(res)

        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res = df_res[pd.to_datetime(sdt) <= df_res['trade_date']]
            df_res = df_res[df_res['trade_date'] <= pd.to_datetime(edt)]

            n_bars = n_bars[pd.to_datetime(sdt) <= n_bars['trade_date']]
            n_bars = n_bars[n_bars['trade_date'] <= pd.to_datetime(edt)]

            print(f"{ts_code} - {name} 强势: {len(df_res)}, mean={df_res.n1b.mean()}, sum={df_res.n1b.sum()}")
            print(f"{ts_code} - {name} 基准: {len(n_bars)}, mean={n_bars.n1b.mean()}, sum={n_bars.n1b.sum()}")

        self.cache[ts_code] = {"signals": signals, "n_bars": n_bars, 'df_res': df_res}

    def get_all_strong_days(self):
        """获取所有指数的强势日期"""
        dc = self.dc
        concepts = dc.ths_index(exchange='A', type_=self.ths_index_type)
        concepts = concepts.to_dict('records')
        results = []
        for row in tqdm(concepts, desc="validate"):
            ts_code = row['ts_code']
            name = row['name']
            try:
                self.get_strong_days(ts_code, name)
                results.append(self.cache[ts_code]['df_res'])
            except:
                print(f"get_strong_days error: {ts_code}, {name}")
                traceback.print_exc()

        df = pd.concat(results, ignore_index=True)
        return df

    def create_next_positions(self, dfg):
        """构建某天选股结果对应的下一交易日持仓明细

        :param dfg: 单个交易日的强势股选股结果
        :return: 下一交易日持仓明细
        """
        if dfg.empty:
            return dfg

        trade_cal = self.dc.trade_cal()
        trade_cal = trade_cal[trade_cal.is_open == 1]
        trade_dates = trade_cal.cal_date.to_list()
        trade_date = dfg['trade_date'].iloc[0]

        hold = dfg.copy()
        hold['成分日期'] = trade_dates[trade_dates.index(trade_date.strftime("%Y%m%d")) + 1]
        hold['持仓权重'] = 0.98 / len(dfg)
        hold.rename({'ts_code': "证券代码", "close": "交易价格"}, inplace=True, axis=1)
        hold = hold[['证券代码', '持仓权重', '交易价格', '成分日期']]
        hold['成分日期'] = pd.to_datetime(hold['成分日期']).apply(lambda x: x.strftime("%Y/%m/%d"))
        return hold

    def validate(self):
        """验证传感器在一段时间内的表现"""
        dc = self.dc
        daily = []
        detail = []
        trade_cal = dc.trade_cal()
        trade_cal = trade_cal[trade_cal.is_open == 1]
        trade_dates = trade_cal[(trade_cal['cal_date'] >= self.sdt)
                                & (trade_cal['cal_date'] <= self.edt)].cal_date.to_list()

        holds = []
        dfg_map = {trade_date.strftime("%Y%m%d"): dfg for trade_date, dfg in self.ssd.groupby('trade_date')}
        for trade_date in trade_dates:
            dfg = dfg_map.get(trade_date, pd.DataFrame())
            if dfg.empty:
                if self.verbose:
                    print(f"{trade_date} 结果为空")
                row = {'trade_date': trade_date, 'number': 0}
                row.update({k: 0 for k in ['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']})
            else:
                detail.append(dfg)
                row = {'trade_date': trade_date, 'number': len(dfg)}
                row.update(dfg[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']].mean().to_dict())
            daily.append(row)
            holds.append(self.create_next_positions(dfg))

        df_daily = pd.DataFrame(daily)
        df_detail = pd.concat(detail, ignore_index=True)
        df_holds = pd.concat(holds, ignore_index=True)
        df_turns, tor = turn_over_rate(df_holds)
        j, i, mdd = max_draw_down(df_daily['n1b'])
        p = {"名称": "板块轮动", '最大回撤': mdd,
             "回撤开始": df_daily.iloc[j]['trade_date'],
             "回撤结束": df_daily.iloc[i]['trade_date'],
             "组合换手": tor,
             "平均数量": df_daily['number'].mean(),
             }
        p.update(df_daily[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']].mean().to_dict())

        f = pd.ExcelWriter(os.path.join(self.results_path, "selected.xlsx"))
        df_detail.to_excel(f, index=False, sheet_name="强势板块")
        df_turns.to_excel(f, index=False, sheet_name="每日换手")
        pd.DataFrame([p]).to_excel(f, index=False, sheet_name="组合表现")
        df_daily.to_excel(f, index=False, sheet_name="每日统计")
        f.close()
        return df_daily, df_detail


