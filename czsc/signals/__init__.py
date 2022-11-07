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


from czsc.signals.cxt import (
    cxt_fx_power_V221107,
)


from czsc.signals.byi import (
    byi_symmetry_zs_V2211007,
)


from czsc.signals.jcc import (
    jcc_san_xing_xian_V221023,
    jcc_ten_mo_V221028,
    jcc_bai_san_bing_V221030,
)


from czsc.signals.tas import (
    update_macd_cache,
    tas_macd_base_V221028,
    tas_macd_change_V221105,
    tas_macd_direct_V221106,

    update_ma_cache,
    tas_ma_base_V221101,
)


