from collections import OrderedDict

from czsc.core import CZSC as CZSC
from czsc.signals.tas import (
    update_cci_cache as update_cci_cache,
)
from czsc.signals.tas import (
    update_kdj_cache as update_kdj_cache,
)
from czsc.signals.tas import (
    update_ma_cache as update_ma_cache,
)
from czsc.signals.tas import (
    update_sar_cache as update_sar_cache,
)
from czsc.utils.sig import create_single_signal as create_single_signal
from czsc.utils.sig import get_sub_elements as get_sub_elements

def coo_td_V221110(c: CZSC, **kwargs) -> OrderedDict: ...
def coo_td_V221111(c: CZSC, **kwargs) -> OrderedDict: ...
def coo_cci_V230323(c: CZSC, **kwargs) -> OrderedDict: ...
def coo_kdj_V230322(c: CZSC, **kwargs) -> OrderedDict: ...
def coo_sar_V230325(c: CZSC, **kwargs) -> OrderedDict: ...
