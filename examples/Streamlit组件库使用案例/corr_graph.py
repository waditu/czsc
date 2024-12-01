import sys

sys.path.insert(0, ".")

import czsc
import pandas as pd
import numpy as np


def main():
    # 设置随机数种子以获得可重复的结果
    np.random.seed(42)

    # 生成样例数据
    data = {
        "V01": np.random.normal(0, 1, 100),
        "V02": np.random.normal(0, 1, 100),
        "V03": np.random.normal(0, 1, 100),
        "V04": np.random.normal(0, 1, 100),
        "V05": np.random.normal(0, 1, 100),
        "V06": np.random.normal(0, 1, 100),
        "V07": np.random.normal(0, 1, 100),
        "V08": np.random.normal(0, 1, 100),
        "V09": np.random.normal(0, 1, 100),
        "V10": np.random.normal(0, 1, 100),
    }

    # 创建 DataFrame
    df = pd.DataFrame(data)
    czsc.show_correlation(df)
    czsc.show_corr_graph(df, threshold=0.1)


if __name__ == "__main__":
    main()
