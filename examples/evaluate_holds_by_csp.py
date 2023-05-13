# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/5/11 18:11
describe: 使用 CrossSectionalPerformance 进行截面持仓表现分析
"""
import pandas as pd
from czsc import CrossSectionalPerformance

dfh = pd.read_feather(r"C:\截面分析样例数据.feather")

# 不使用杠杆进行截面分析
csp = CrossSectionalPerformance(dfh, max_total_weight=1)
csp.report('不使用杠杆的表现.docx')

# 使用一倍杠杆进行截面分析
csp = CrossSectionalPerformance(dfh, max_total_weight=2)
csp.report('使用1倍杠杆的表现.docx')

