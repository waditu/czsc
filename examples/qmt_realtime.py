# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/5 10:08
describe: QMT实时交易
"""
from czsc.connectors import qmt_connector as qmc
from czsc.strategies import CzscStrategyExample2


def get_index_members(index_code='000852.SH', trade_date='20230131'):
    """获取指数成分股"""
    import tushare as ts
    pro = ts.pro_api()
    df = pro.index_weight(index_code=index_code, start_date=trade_date, end_date=trade_date)

    return [x for x in df['con_code'] if 'BJ' not in x]


gjm = {
        # trader 缓存目录
        'cache_path': "D:\\国金QMT交易端模拟\\userdata_mini\\czsc_stocks_beta_cache",
        # mini qmt 目录
        'mini_qmt_dir': "D:\\国金QMT交易端模拟\\userdata_mini",
        # 账户id
        'account_id': '55002763',
        # 设定实盘交易的股票池
        'symbols': get_index_members('000016.SH', trade_date='20230131'),
        # 单个股票的最大持仓比例
        'symbol_max_pos': 0.1,
        # CzscTrader初始交易开始的时间，这个时间之后的交易都会被缓存在对象中
        'trade_sdt': "20230101",
        # update trader时，K线获取的天数
        'delta_days': 1,
        # 交易策略
        'strategy': CzscStrategyExample2,
        # TraderCallback 回调类的参数
        'callback_params': {
            # 飞书推送配置【不配置也没有影响】
            'feishu_push_mode': 'detail',
            'feishu_app_id': 'cli_a307*****9500e',
            'feishu_app_secret': 'jVoMf688Gbw2******hoVbZ7fiTkTkgg',
            'feishu_members': ['ou_****0'],
            'log_file': 'D:\\国金QMT交易端模拟\\userdata_mini\\czsc_stocks_beta_cache\\czsc_stocks_beta.log',
        },
}

if __name__ == '__main__':
    manager = qmc.QmtTradeManager(**gjm)
    manager.run()



