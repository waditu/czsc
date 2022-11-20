# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/21 17:48
describe: 信号系统，注意：这里仅仅只是提供一些写信号的例子，用来做策略是不太行的
"""

from . import bxt
from . import ta
from . import other
from . import vol
from . import cat
from . import pos
from . import example


# ======================================================================================================================
# 以下是 0.9.1 开始的新标准下实现的信号函数，规范定义：
# 1. 前缀3个字符区分信号类别
# 2. 后缀 V221107 之类的标识同一个信号函数的版本
# ======================================================================================================================

from czsc.signals.cxt import (
    cxt_fx_power_V221107,
)


from czsc.signals.byi import (
    byi_symmetry_zs_V2211007,
)

from czsc.signals.coo import (
    coo_td_V221110,
)

from czsc.signals.bar import (
    bar_end_V221111,
    bar_operate_span_V221111,
    bar_zdt_V221110,
    bar_zdt_V221111,
    bar_cross_ps_V221112,
    bar_section_momentum_V221112,
    bar_vol_grow_V221112,
    bar_mean_amount_V221112,
)

from czsc.signals.jcc import (
    jcc_san_xing_xian_V221023,
    jcc_ten_mo_V221028,
    jcc_bai_san_bin_V221030,
    jcc_san_fa_20221115,
    jcc_san_fa_20221118,
    jcc_wu_yun_gai_ding_V221101,
    jcc_ci_tou_V221101,
    jcc_xing_xian_v221118,
    jcc_fen_shou_xian_V20221113,
    jcc_yun_xian_V221118,
    jcc_zhu_huo_xian_V221027,
    jcc_ping_tou_v221113,
    jcc_zhuo_yao_dai_xian_v221113,
    jcc_two_crow_V221108,
    jcc_three_crow_V221108,
    jcc_three_soldiers_V221030,
    jcc_szx_V221111,
)


from czsc.signals.tas import (
    update_macd_cache,
    tas_macd_base_V221028,
    tas_macd_change_V221105,
    tas_macd_direct_V221106,

    update_ma_cache,
    tas_ma_base_V221101,

    update_boll_cache,
    tas_boll_power_V221112,
)


