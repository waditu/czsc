# 编写策略样例：https://s0cqcxuy3p.feishu.cn/wiki/D3VEwHnpjiA8cokFTWEcuqDunZc

from typing import List
from czsc.objects import Event, Position
from czsc import CzscStrategyBase, Position


class Strategy(CzscStrategyBase):

    def create_pos_a(self, symbol, **kwargs):
        """_summary_

        https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_third_buy_V230228.html
        https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_first_sell_V221126.html

        :param symbol: _description_
        :return: _description_
        """
        base_freq = kwargs.get("base_freq", "30分钟")

        opens = [
            {
                "operate": "开多",
                "signals_not": [],
                "signals_all": [],
                "factors": [{"name": "三买多头", "signals_all": ["日线_D1_三买辅助V230228_三买_任意_任意_0"]}],
            }
        ]

        exits = [
            {
                "operate": "平多",
                "signals_all": [],
                "signals_not": [],
                "factors": [
                    {
                        "name": "平多",
                        "signals_all": ["30分钟_D1B_SELL1_一卖_任意_任意_0"],
                        "signals_any": [
                            "30分钟_D1B_SELL1_一卖_9笔_任意_0",
                            "30分钟_D1B_SELL1_一卖_11笔_任意_0",
                            "30分钟_D1B_SELL1_一卖_13笔_任意_0",
                        ],
                    }
                ],
            }
        ]
        opens[0]["signals_all"].append(f"{base_freq}_D1_涨跌停V230331_任意_任意_任意_0")
        pos_name = "日线三买多头A"

        T0 = kwargs.get("T0", False)
        pos_name = f"{pos_name}T0" if T0 else f"{pos_name}"

        pos = Position(
            name=pos_name,
            symbol=symbol,
            opens=[Event.load(x) for x in opens],
            exits=[Event.load(x) for x in exits],
            interval=kwargs.get("interval", 3600 * 2),
            timeout=kwargs.get("timeout", 16 * 30),
            stop_loss=kwargs.get("stop_loss", 300),
            T0=T0,
        )
        return pos

    def create_pos_b(self, symbol, **kwargs):
        """_summary_

        https://czsc.readthedocs.io/en/latest/api/czsc.signals.pos_status_V230808.html
        https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230102.html

        :param symbol: _description_
        :return: _description_
        """
        base_freq = kwargs.get("base_freq", "30分钟")
        last_pos_name = "日线三买多头A"

        opens = [
            {
                "operate": "开空",
                "signals_not": [],
                "signals_all": [],
                "factors": [
                    {
                        "name": "第一次平多",
                        "signals_all": [
                            "30分钟_D1_表里关系V230102_向上_顶分_任意_0",
                            f"{last_pos_name}_持仓状态_BS辅助V230808_持多_任意_任意_0",
                        ],
                    }
                ],
            }
        ]

        exits = [
            {
                "operate": "平空",
                "signals_all": [],
                "signals_not": [],
                "factors": [
                    {
                        "name": "平多",
                        "signals_all": [f"{last_pos_name}_持仓状态_BS辅助V230808_任意_任意_任意_0"],
                        "signals_any": [
                            f"{last_pos_name}_持仓状态_BS辅助V230808_持空_任意_任意_0",
                            f"{last_pos_name}_持仓状态_BS辅助V230808_持币_任意_任意_0",
                        ],
                    }
                ],
            }
        ]
        opens[0]["signals_all"].append(f"{base_freq}_D1_涨跌停V230331_任意_任意_任意_0")
        pos_name = "日线三买第一次平仓"

        T0 = kwargs.get("T0", False)
        pos_name = f"{pos_name}T0" if T0 else f"{pos_name}"

        pos = Position(
            name=pos_name,
            symbol=symbol,
            opens=[Event.load(x) for x in opens],
            exits=[Event.load(x) for x in exits],
            interval=kwargs.get("interval", 3600 * 2),
            timeout=kwargs.get("timeout", 16 * 30),
            stop_loss=kwargs.get("stop_loss", 1000),
            T0=T0,
        )
        return pos

    def create_pos_c(self, symbol, **kwargs):
        """_summary_

        https://czsc.readthedocs.io/en/latest/api/czsc.signals.pos_status_V230808.html
        https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230102.html

        :param symbol: _description_
        :return: _description_
        """
        base_freq = kwargs.get("base_freq", "30分钟")
        last_pos_a = "日线三买多头A"
        last_pos_b = "日线三买第一次平仓"

        opens = [
            {
                "operate": "开空",
                "signals_not": [],
                "signals_all": [],
                "factors": [
                    {
                        "name": "第二次平多",
                        "signals_all": [
                            "日线_D1_表里关系V230102_向上_顶分_任意_0",
                            f"{last_pos_a}_持仓状态_BS辅助V230808_持多_任意_任意_0",
                            f"{last_pos_b}_持仓状态_BS辅助V230808_持空_任意_任意_0",
                        ],
                    }
                ],
            }
        ]

        exits = [
            {
                "operate": "平空",
                "signals_all": [],
                "signals_not": [],
                "factors": [
                    {
                        "name": "平多",
                        "signals_all": [f"{last_pos_a}_持仓状态_BS辅助V230808_任意_任意_任意_0"],
                        "signals_any": [
                            f"{last_pos_a}_持仓状态_BS辅助V230808_持空_任意_任意_0",
                            f"{last_pos_a}_持仓状态_BS辅助V230808_持币_任意_任意_0",
                        ],
                    }
                ],
            }
        ]
        opens[0]["signals_all"].append(f"{base_freq}_D1_涨跌停V230331_任意_任意_任意_0")
        pos_name = "日线三买第二次平仓"

        T0 = kwargs.get("T0", False)
        pos_name = f"{pos_name}T0" if T0 else f"{pos_name}"

        pos = Position(
            name=pos_name,
            symbol=symbol,
            opens=[Event.load(x) for x in opens],
            exits=[Event.load(x) for x in exits],
            interval=kwargs.get("interval", 3600 * 2),
            timeout=kwargs.get("timeout", 16 * 30),
            stop_loss=kwargs.get("stop_loss", 1000),
            T0=T0,
        )
        return pos

    @property
    def positions(self) -> List[Position]:
        _pos = [
            self.create_pos_a(symbol=self.symbol, base_freq="30分钟", T0=False),
            self.create_pos_b(symbol=self.symbol, base_freq="30分钟", T0=False),
            self.create_pos_c(symbol=self.symbol, base_freq="30分钟", T0=False),
        ]
        return _pos


if __name__ == "__main__":
    from czsc.connectors.research import get_raw_bars

    tactic = Strategy(symbol="000001.SH")
    bars = get_raw_bars("000001.SH", freq="30分钟", sdt="2015-01-01", edt="2022-07-01")
    tactic.replay(bars, res_path=r"C:\Users\zengb\Desktop\230814\一开多平")
