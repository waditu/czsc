# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/7/26 15:46
describe: 资产组合研究相关的工具函数
"""
import loguru


def max_sharp(df, weight_bounds=(0, 1), **kwargs):
    """最大夏普比例组合

    依赖 PyPortfolioOpt 库，需要安装 pip install PyPortfolioOpt

    :param df: pd.DataFrame, 包含多个资产的日收益率数据，index 为日期
    :param weight_bounds: tuple, 权重范围, 默认 (0, 1), 参考 EfficientFrontier 的 weight_bounds 参数
        如果需要设置不同的权重范围，可以传入 dict，如 {"asset1": (0, 0.5), "asset2": (0.1, 0.5)}
    :param kwargs: 其他参数

        - logger: loguru.logger, 默认 None, 日志记录器
        - rounding: int, 默认 4, 权重四舍五入的小数位数

    :return: dict, 资产权重
    """
    from pypfopt import EfficientFrontier
    from pypfopt import expected_returns
    from pypfopt import risk_models
    from czsc.utils.stats import daily_performance

    logger = kwargs.get("logger", loguru.logger)
    df = df.copy()
    if "dt" in df.columns:
        df = df.set_index("dt")

    mu = expected_returns.mean_historical_return(df, returns_data=True)
    S = risk_models.risk_matrix(df, returns_data=True, method="sample_cov")

    if isinstance(weight_bounds, dict):
        weight_bounds = [
            [weight_bounds.get(asset, (0, 1))[0] for asset in df.columns],
            [weight_bounds.get(asset, (0, 1))[1] for asset in df.columns],
        ]

    # Optimize for maximal Sharpe ratio
    ef = EfficientFrontier(mu, S, weight_bounds=weight_bounds)
    _ = ef.max_sharpe()
    weights = ef.clean_weights(cutoff=1e-4, rounding=kwargs.get("rounding", 4))

    logger.info(f"资产权重：{weights}")

    portfolio = df.apply(lambda x: x * weights[x.name], axis=0)
    stats = daily_performance(portfolio.sum(axis=1).to_list())
    logger.info(f"组合表现：{stats}")

    return weights
