import czsc


class SMA5Dist(czsc.FeatureAnalyzeBase):

    @property
    def new_features(self):
        """list，新增的特征列表"""
        return ["sma5_dist"]

    def add_features(self, df):
        """向df中添加特征

        df 包含以下列：

        - dt: 日期
        - open: 开盘价
        - close: 收盘价
        - high: 最高价
        - low: 最低价
        - vol: 成交量
        - amount: 成交额
        """
        df["sma5"] = df["close"].rolling(5).mean()
        df["sma5_dist"] = -(df["close"] / df["sma5"] - 1)
        df.drop(columns=["sma5"], inplace=True)
        return df


if __name__ == '__main__':
    from czsc.connectors.research import get_raw_bars, get_symbols

    sd = SMA5Dist(symbols=get_symbols('中证500成分股'), read_bars=get_raw_bars, freq='日线', sdt='20210101', edt='20230101',
                  max_workers=10, results_path=r"C:\sma5dist")
