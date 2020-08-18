# coding: utf-8
import sys
from .analyze import KlineAnalyze, find_zs


class KlineSignals(KlineAnalyze):
    """单级别信号计算"""
    def __init__(self, kline, name="本级别", min_bi_k=5, bi_mode="old",
                 max_raw_len=10000, ma_params=(5, 20, 120)):
        super().__init__(kline, name, min_bi_k, bi_mode,
                         max_raw_len, ma_params, verbose=False)

    def get_signals(self):
        """获取单级别信号"""
        methods = [x for x in dir(self) if x.startswith("S")]
        signals = dict()
        for method in methods:
            s = getattr(self, method)()
            signals.update(s)
        return signals

    # 技术分析信号
    # ------------------------------------------------------------------------------------------------------------------
    def STA01(self):
        """收于MA5上方"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        last_k = self.kline_raw[-1]
        last_ma = self.ma[-1]
        assert last_k['dt'] == last_ma['dt'], "{}：计算均线错误".format(self.name)
        v = True if last_k['close'] >= last_ma['ma5'] > 0 else False
        return {k: v}

    def STA02(self):
        """收于MA20上方"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        last_k = self.kline_raw[-1]
        last_ma = self.ma[-1]
        assert last_k['dt'] == last_ma['dt'], "{}：计算均线错误".format(self.name)
        v = True if last_k['close'] >= last_ma['ma20'] > 0 else False
        return {k: v}

    def STA03(self):
        """收于MA120上方"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        last_k = self.kline_raw[-1]
        last_ma = self.ma[-1]
        assert last_k['dt'] == last_ma['dt'], "{}：计算均线错误".format(self.name)
        v = True if last_k['close'] >= last_ma['ma120'] > 0 else False
        return {k: v}

    # 分型信号
    # ------------------------------------------------------------------------------------------------------------------
    def SFX01(self):
        """最近一个分型类型"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        v = self.fx_list[-1]['fx_mark']
        return {k: v}

    def SFX02(self):
        """最近两个顶分型形态"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        fx_g = [x for x in self.fx_list[-6:] if x['fx_mark'] == 'g']
        if len(fx_g) >= 2:
            v = "up" if fx_g[-1]['fx'] >= fx_g[-2]['fx'] else "down"
        else:
            v = None
        return {k: v}

    def SFX03(self):
        """最近两个底分型形态"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        fx_d = [x for x in self.fx_list[-6:] if x['fx_mark'] == 'd']
        if len(fx_d) >= 2:
            v = "up" if fx_d[-1]['fx'] >= fx_d[-2]['fx'] else "down"
        else:
            v = None
        return {k: v}

    def SFX04(self):
        """最近三个顶分型形态"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        fx_g = [x for x in self.fx_list[-12:] if x['fx_mark'] == 'g']
        if len(fx_g) >= 3:
            if fx_g[-3]['fx'] < fx_g[-2]['fx'] > fx_g[-1]['fx']:
                v = "g"
            elif fx_g[-3]['fx'] > fx_g[-2]['fx'] < fx_g[-1]['fx']:
                v = "d"
            elif fx_g[-3]['fx'] > fx_g[-2]['fx'] > fx_g[-1]['fx']:
                v = "down"
            elif fx_g[-3]['fx'] < fx_g[-2]['fx'] < fx_g[-1]['fx']:
                v = "up"
            else:
                v = None
        else:
            v = None
        return {k: v}

    def SFX05(self):
        """最近三个底分型形态"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        fx_d = [x for x in self.fx_list[-12:] if x['fx_mark'] == 'd']
        if len(fx_d) >= 3:
            if fx_d[-3]['fx'] < fx_d[-2]['fx'] > fx_d[-1]['fx']:
                v = "g"
            elif fx_d[-3]['fx'] > fx_d[-2]['fx'] < fx_d[-1]['fx']:
                v = "d"
            elif fx_d[-3]['fx'] > fx_d[-2]['fx'] > fx_d[-1]['fx']:
                v = "down"
            elif fx_d[-3]['fx'] < fx_d[-2]['fx'] < fx_d[-1]['fx']:
                v = "up"
            else:
                v = None
        else:
            v = None
        return {k: v}

    def SFX06(self):
        """最近三K线形态"""
        method_name = sys._getframe().f_code.co_name
        k = "{}_{}_{}".format(self.name, method_name, getattr(self, method_name).__doc__)

        last_tri = self.kline_new[-3:]
        if len(last_tri) == 3:
            if last_tri[-3]['high'] < last_tri[-2]['high'] > last_tri[-1]['high']:
                v = "g"
            elif last_tri[-3]['low'] > last_tri[-2]['low'] < last_tri[-1]['low']:
                v = "d"
            elif last_tri[-3]['low'] > last_tri[-2]['low'] > last_tri[-1]['low']:
                v = "down"
            elif last_tri[-3]['high'] < last_tri[-2]['high'] < last_tri[-1]['high']:
                v = "up"
            else:
                v = None
        else:
            v = None
        return {k: v}

    # # 笔信号
    # # ------------------------------------------------------------------------------------------------------------------
    # def SBI01(self):
    #     pass
    #
    # # 线段信号
    # # ------------------------------------------------------------------------------------------------------------------
    # def SXD01(self):
    #     pass

