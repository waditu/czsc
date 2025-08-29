from czsc.connectors.research import get_symbols, get_raw_bars
from czsc.traders.optimize import OpensOptimize, ExitsOptimize


def run_opens_optim():
    symbols = get_symbols('期货主力')[:10]
    results_path = r"D:\QMT投研\CCI入场优化结果B"
    files_position = [
        r"D:\QMT投研\基础策略V230707\A股日线CCI空头基准.json",
        r"D:\QMT投研\基础策略V230707\A股日线CCI多头基准.json",
    ]
    task_name = 'CCI入场优化'

    candidate_signals = """
日线_D2单K趋势N5_BS辅助V230506_第1层_任意_任意_0
日线_D2单K趋势N5_BS辅助V230506_第2层_任意_任意_0
日线_D2单K趋势N5_BS辅助V230506_第3层_任意_任意_0
日线_D2单K趋势N5_BS辅助V230506_第4层_任意_任意_0
日线_D2单K趋势N10_BS辅助V230506_第1层_任意_任意_0
日线_D2单K趋势N10_BS辅助V230506_第2层_任意_任意_0
日线_D2单K趋势N10_BS辅助V230506_第4层_任意_任意_0
日线_D2单K趋势N10_BS辅助V230506_第6层_任意_任意_0
日线_D2单K趋势N10_BS辅助V230506_第7层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第11层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第12层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第13层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第14层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第15层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第16层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第18层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第1层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第2层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第3层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第4层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第5层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第6层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第7层_任意_任意_0
日线_D2单K趋势N20_BS辅助V230506_第8层_任意_任意_0
    """.strip().replace(' ', '').split('\n')
    candidate_signals = list(set(candidate_signals))
    oop = OpensOptimize(symbols=symbols, files_position=files_position, task_name=task_name,
                        candidate_signals=candidate_signals, read_bars=get_raw_bars,
                        results_path=results_path, signals_module_name='czsc.signals',
                        bar_sdt='20160101', bar_edt='20230101', sdt='20170101')
    oop.execute(n_jobs=10)


def run_exits_optim():
    symbols = get_symbols('期货主力')[:10]
    results_path = r"D:\QMT投研\CCI出场优化结果B"
    files_position = [
        r"D:\QMT投研\基础策略V230707\A股日线CCI空头基准.json",
        r"D:\QMT投研\基础策略V230707\A股日线CCI多头基准.json",
    ]
    task_name = '加速上涨优化多头'

    candidate_events = [
        {'operate': '平多',
         'factors': [
             {'name': '加速上涨',
              'signals_all': [
                  "日线_D2N5T500_绝对动量V230227_超强_任意_任意_0",
              ]}
         ]},
        {'operate': '平多',
         'factors': [
             {'name': '加速上涨',
              'signals_all': [
                  "日线_D2N8T600_绝对动量V230227_超强_任意_任意_0",
              ]}
         ]},
        {'operate': '平多',
         'factors': [
             {'name': '加速上涨',
              'signals_all': [
                  "日线_D2N10T800_绝对动量V230227_超强_任意_任意_0",
              ]}
         ]},

        {'operate': '平空',
         'factors': [
             {'name': '加速下跌',
              'signals_all': [
                  "日线_D2N5T300_绝对动量V230227_超弱_任意_任意_0",
              ]}
         ]},
        {'operate': '平空',
         'factors': [
             {'name': '加速下跌',
              'signals_all': [
                  "日线_D2N8T500_绝对动量V230227_超弱_任意_任意_0",
              ]}
         ]},
        {'operate': '平空',
         'factors': [
             {'name': '加速下跌',
              'signals_all': [
                  "日线_D2N10T800_绝对动量V230227_超弱_任意_任意_0",
              ]}
         ]},
    ]

    eop = ExitsOptimize(symbols=symbols, files_position=files_position, task_name=task_name,
                        candidate_events=candidate_events, read_bars=get_raw_bars,
                        results_path=results_path, signals_module_name='czsc.signals',
                        bar_sdt='20160101', bar_edt='20230101', sdt='20170101')
    eop.execute(n_jobs=10)


if __name__ == '__main__':
    run_opens_optim()
    run_exits_optim()
