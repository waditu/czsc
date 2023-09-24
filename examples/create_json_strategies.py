from typing import List
from czsc.strategies import (
    create_macd_long,
    create_macd_short,
    create_single_ma_long,
    create_single_ma_short,
    create_cci_long,
    create_cci_short,
)
from czsc import CzscStrategyBase, Position


class BetaStrategy(CzscStrategyBase):

    @property
    def positions(self) -> List[Position]:
        _pos = [
            create_single_ma_long(symbol=self.symbol, freq='5分钟', ma_name='SMA#40',
                                  base_freq='1分钟', max_overlap=10, timeout=80, is_stocks=False, T0=True),
            create_single_ma_short(symbol=self.symbol, freq='5分钟', ma_name='SMA#40',
                                   base_freq='1分钟', max_overlap=10, timeout=80, is_stocks=False, T0=True),

            # 日线基础策略构建
            create_single_ma_long(
                symbol=self.symbol,
                freq="日线",
                ma_name="SMA#5",
                max_overlap=3,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),
            create_single_ma_short(
                symbol=self.symbol,
                freq="日线",
                ma_name="SMA#5",
                max_overlap=3,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),
            create_single_ma_long(
                symbol=self.symbol,
                freq="日线",
                ma_name="SMA#20",
                max_overlap=5,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),
            create_single_ma_short(
                symbol=self.symbol,
                freq="日线",
                ma_name="SMA#20",
                max_overlap=5,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),

            create_macd_long(
                symbol=self.symbol,
                freq="日线",
                max_overlap=5,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),
            create_macd_short(
                symbol=self.symbol,
                freq="日线",
                max_overlap=5,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),

            create_cci_long(
                symbol=self.symbol,
                freq="日线",
                cci_timeperiod=14,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),
            create_cci_short(
                symbol=self.symbol,
                freq="日线",
                cci_timeperiod=14,
                timeout=20,
                is_stocks=True,
                stop_loss=300,
                T0=False,
            ),
        ]
        return _pos


if __name__ == "__main__":
    tactic = BetaStrategy(symbol="000001.XSHG", signals_module_name='czsc.signals')
    tactic.save_positions(r"D:\QMT投研\基础策略V230707")
