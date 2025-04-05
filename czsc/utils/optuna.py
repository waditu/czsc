# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/3/21 13:56
describe: optuna 工具函数
"""
import hashlib
import inspect
import pandas as pd


def optuna_study(objective, direction="maximize", n_trials=100, **kwargs):
    """使用optuna进行参数优化"""
    import optuna
    objective_code = inspect.getsource(objective)
    study_name = hashlib.md5(f"{objective_code}_{direction}".encode("utf-8")).hexdigest().upper()[:12]
    study = optuna.create_study(direction=direction, study_name=study_name)

    timeout = kwargs.pop("timeout", None)
    n_jobs = kwargs.pop("n_jobs", 1)
    study.optimize(objective, n_trials=n_trials, timeout=timeout, n_jobs=n_jobs, **kwargs)
    return study


def optuna_good_params(study, keep=0.2) -> pd.DataFrame:
    """获取optuna优化结果中的最优参数

    :param study: optuna.study.Study
    :param keep: float, 保留最优参数的比例, 默认0.2
        如果keep小于0，则按比例保留；如果keep大于0，则保留keep个参数组
    :return: pd.DataFrame, 最优参数组列表
    """
    import optuna
    assert isinstance(study, optuna.Study), "study必须是optuna.Study类型"
    
    assert keep > 0, "keep必须大于0"
    params = []
    for trail in study.trials:
        if trail.state != optuna.trial.TrialState.COMPLETE:
            continue
        if trail.value is None:
            continue

        p = {"params": trail.params, "objective": trail.value}
        params.append(p)

    n = int(len(params) * keep) if keep < 1 else int(keep)
    reverse = study.direction == 2
    params = sorted(params, key=lambda x: x['objective'], reverse=reverse)
    dfp = pd.DataFrame(params[:n])
    dfp = dfp.drop_duplicates(subset=['params'], keep='first').reset_index(drop=True)
    return dfp
