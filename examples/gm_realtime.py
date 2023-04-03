# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: A股股票实盘仿真

环境变量设置说明：
strategy_id                 掘金研究策略ID
account_id                  账户ID
wx_key                      企业微信群聊机器人Key
max_sym_pos                 单仓位限制
path_gm_logs                gm_logs的路径，默认值：C:/gm_logs

环境变量设置样例：
# 使用 os 模块设置
os.environ['strategy_id'] = 'c7991760-****-11eb-b66a-00163e0c87d1'
os.environ['account_id'] = 'c7991760-****-11eb-b66a-00163e0c87d1'
os.environ['max_sym_pos'] = '0.5'
os.environ['path_gm_logs'] = 'C:/gm_logs'
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from czsc.connectors.gm_connector import *
from czsc.strategies import CzscStrategyExample2


os.environ['strategy_id'] = '43b099b8-*****-11ed-99a6-988fe0675a5b'
os.environ['account_id'] = '613019f5-****-11ed-bdad-00163e18a8b3'
os.environ['max_sym_pos'] = '0.5'
os.environ['path_gm_logs'] = 'C:/gm_logs'


def init(context):
    # 股票池配置
    symbols = [
        'SZSE.300014',
        'SHSE.600143',
        'SZSE.002216',
        'SZSE.300033',
        'SZSE.000795',
        'SZSE.002739',
        'SHSE.600000',
        'SHSE.600008',
        'SHSE.600006',
        'SHSE.600009',
        'SHSE.600010',
        'SHSE.600011'
    ]

    # 配置消息推送服务，支持飞书、企业微信通道
    context.push_msg_conf = {
        "wx_key": os.environ.get('wx_key', None),
        "fs_app": {
            # 飞书消息推送
            'feishu_app_id': 'cli_*****015cc39500e',
            'feishu_app_secret': 'jV******688Gbw20fkR2HhoVbZ7fiTkTkgg',
            'feishu_members': ['ou_6fa*****d853e9fdc87d267e8f2a270'],
        }
    }
    strategy = CzscStrategyExample2
    init_context_universal(context, strategy.__name__)
    init_context_env(context)
    init_context_traders(context, symbols, strategy)
    init_context_schedule(context)


if __name__ == '__main__':
    run(filename=os.path.basename(__file__), token=gm_token, mode=MODE_LIVE, strategy_id=os.environ['strategy_id'])

