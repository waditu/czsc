# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 19:07
describe: ZB实盘

环境变量设置样例：
strategy_id=c7e84d1c-d1c6-11eb-bb47-38f3abf8ed06
wx_key=909731bd-****-46ad-****-24b9830873a4
path_gm_logs=C:/gm_logs
stoploss=0.05
timeout=600
share_id=2c632491-d8a4-11eb-b1cd-00163e0a4100
file_zx=C:/gm_logs/ZB.xlsx
max_total_position=0.8
max_share_position=0.5

"""
from src.utils import read_ths_zx
from src.utils.rt import *
from src.tactics.share import TacticShareA as Tactic


def init(context):
    file_zx = os.environ.get('file_zx', None)
    symbols = read_ths_zx(file_zx)['掘金代码'].unique().tolist()

    tactic = Tactic()
    op_freq, freqs, get_signals, get_events = tactic.like_bs_rt_v1()
    name = f"{tactic.name.lower()}_{tactic.like_bs_rt_v1.__name__}"
    init_context_rt(context, name, symbols, op_freq, freqs, get_signals, get_events)

    push_text("实盘仿真开始，以下是程序股票池：", context.wx_key)
    push_file(file_zx, context.wx_key)

    # 设置定时任务
    # ------------------------------------------------------------------------------------------------------------------
    # schedule(schedule_func=stocks_dwm_selector_rt, date_rule='1d', time_rule='17:05:00')
    # schedule(schedule_func=stocks_monitor_rt, date_rule='1d', time_rule='11:40:00')

    schedule(schedule_func=push_operate_status, date_rule='1d', time_rule='09:46:00')
    schedule(schedule_func=push_operate_status, date_rule='1d', time_rule='10:35:00')
    schedule(schedule_func=push_operate_status, date_rule='1d', time_rule='11:35:00')
    schedule(schedule_func=push_operate_status, date_rule='1d', time_rule='13:35:00')
    schedule(schedule_func=push_operate_status, date_rule='1d', time_rule='14:35:00')


if __name__ == '__main__':
    run(filename=os.path.basename(__file__), token=gm_token, mode=MODE_LIVE, strategy_id=os.environ['strategy_id'])



