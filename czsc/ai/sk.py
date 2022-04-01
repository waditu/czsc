# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/28 17:48
describe: 基于 Scikit-Learn, Xgboost, LightGBM 三个机器学习库的分类、回归模型
"""
import pandas as pd
from sklearn import metrics
from sklearn.pipeline import Pipeline
from typing import List, AnyStr

from .utils import get_datetime_spans


def evaluate_estimator(estimator: Pipeline, df: pd.DataFrame, x_cols: List[AnyStr], y_col: AnyStr = None):
    """评估模型表现

    :param estimator: 使用 Pipeline 组合成模型
    :param df: 输入数据
    :param x_cols: 特征名序列
    :param y_col: 真实值列
    :return:
    """
    y_pred = estimator.predict(df[x_cols])
    df['y_pred'] = y_pred

    if not y_col:
        return df

    model_type = estimator.steps[-1][0]
    sdt = df['dt'].min().strftime("%Y%m%d")
    edt = df['dt'].max().strftime("%Y%m%d")
    y_ture = df[y_col]

    if model_type.lower() == 'regressor':
        print(f"{sdt} - {edt} 回归模型评估: \nr2_score = %.3f; MSE = %.3f; MAE = %.3f" %
              (metrics.r2_score(y_ture, y_pred),
               metrics.mean_squared_error(y_ture, y_pred),
               metrics.mean_absolute_error(y_ture, y_pred)))
    elif model_type.lower() == 'classifier':
        print(f"{sdt} - {edt} 分类模型评估: \n{metrics.classification_report(y_ture, y_pred)}")
    else:
        raise ValueError
    return df


def train_estimator(estimator: Pipeline,
                    df: pd.DataFrame,
                    x_cols: List[AnyStr],
                    y_col: AnyStr,
                    train_days: int,
                    valid_days: int,
                    method="rolling"):
    """训练模型

    :param estimator: 使用 Pipeline 组合成模型
    :param df: 数据对象
    :param x_cols: 特征名序列
    :param y_col: 真实值列
    :param train_days: 训练集时间跨度
    :param valid_days: 验证集时间跨度
    :param method: 时间窗口滚动方法，rolling 滑动窗口，expanding 扩张窗口
    :return:
    """
    sdt = df['dt'].min()
    edt = df['dt'].max()
    spans = get_datetime_spans(sdt, edt, train_days, valid_days, method)

    predicts = []
    for train_sdt, train_edt, valid_sdt, valid_edt in spans:
        train = df[(df['dt'] >= train_sdt) & (df['dt'] <= train_edt)].copy()
        # 注意：由于时间窗口滚动过程，train_edt == valid_sdt，所以，划分验证集时，必须要大于 valid_sdt
        valid = df[(df['dt'] > valid_sdt) & (df['dt'] <= valid_edt)].copy()
        if valid.empty:
            continue

        print("=" * 100)
        print("测试区间：{} ~ {}\n".format(valid_sdt, valid_edt))
        print('样本比例 = 训练集：测试集 = {}: {} \n'.format(len(train), len(valid)))

        estimator.fit(train[x_cols], train[y_col])
        valid['y_pred'] = estimator.predict(valid[x_cols])
        predicts.append(valid)
        evaluate_estimator(estimator, train, x_cols, y_col)
        evaluate_estimator(estimator, valid, x_cols, y_col)

    dfr = pd.concat(predicts)
    return dfr, estimator

