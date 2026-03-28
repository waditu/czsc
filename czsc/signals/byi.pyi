from collections import OrderedDict

from czsc import CZSC as CZSC
from czsc.core import BI as BI
from czsc.core import Direction as Direction
from czsc.core import Mark as Mark
from czsc.signals.tas import (
    update_boll_cache_V230228 as update_boll_cache_V230228,
)
from czsc.signals.tas import (
    update_ma_cache as update_ma_cache,
)
from czsc.signals.tas import (
    update_macd_cache as update_macd_cache,
)
from czsc.utils.sig import (
    create_single_signal as create_single_signal,
)
from czsc.utils.sig import (
    get_sub_elements as get_sub_elements,
)
from czsc.utils.sig import (
    is_symmetry_zs as is_symmetry_zs,
)

def byi_symmetry_zs_V221107(c: CZSC, **kwargs): ...
def byi_bi_end_V230106(c: CZSC, **kwargs) -> OrderedDict: ...
def byi_bi_end_V230107(c: CZSC, **kwargs) -> OrderedDict: ...
def byi_second_bs_V230324(c: CZSC, **kwargs) -> OrderedDict: ...
def byi_fx_num_V230628(c: CZSC, **kwargs) -> OrderedDict: ...
