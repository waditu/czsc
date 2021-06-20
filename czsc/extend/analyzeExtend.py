from czsc import CZSC
from czsc.objects import *


class CZSCExtend(CZSC):
    def __init__(self, bars: List[RawBar], freq: str, max_bi_count=30):
        super(CZSCExtend, self).__init__(bars, freq, max_bi_count)
        self.center = []
