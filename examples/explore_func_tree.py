import inspect
import czsc
import pandas as pd
import pkgutil


def process_functions():
    functions = inspect.getmembers(czsc, inspect.isfunction)
    functions = [f"{f[1].__module__}.{f[1].__name__}" for f in functions]
    df = pd.DataFrame({"代码块": functions})
    df['负责人'] = None
    df['进展'] = None
    df['合并入库'] = None
    df = df.sort_values(by="代码块", ascending=False)
    df.to_excel("czsc功能清单.xlsx", index=False)
