# coding: utf-8
import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import AdaBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import classification_report
import xgboost as xgb


data = []
for file in os.listdir("./data"):
    if file.endswith("xlsx") and "30min" in file:
        file_data = f"./data/{file}"
        df_ = pd.read_excel(file_data)
        data.append(df_)
        print(f"load {file_data} success.")

df = pd.concat(data)
print("data shape(before drop duplicates): ", df.shape)
x_cols = ['1分钟分型标记', '1分钟笔标记', '1分钟线段标记', '1分钟MACD金叉',
          '1分钟MACD死叉', '5分钟分型标记', '5分钟笔标记', '5分钟线段标记', '5分钟MACD金叉', '5分钟MACD死叉',
          '30分钟分型标记', '30分钟笔标记', '30分钟线段标记', '30分钟MACD金叉', '30分钟MACD死叉', '日线分型标记',
          '日线笔标记', '日线线段标记', '日线MACD金叉', '日线MACD死叉']

y_col = '30min线段状态'
df.drop_duplicates(subset=x_cols + [y_col], inplace=True)
print("data shape(after drop duplicates): ", df.shape)
df0 = df[df[y_col] == '向上段']
df1 = df[df[y_col] == '向下段']

# 降采样获取均衡数据集
n_sample = min(len(df0), len(df1))
df = pd.concat([df0.sample(n_sample, random_state=42), df1.sample(n_sample, random_state=42)])


X = df[x_cols].values
y = df[y_col].apply(lambda x: 1 if x == '向上段' else 0).values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

k_fold = KFold(n_splits=5, shuffle=True, random_state=42)


def run_logistic_regression():
    model = LogisticRegression(penalty='l1', random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    for k, (train, test) in enumerate(k_fold.split(X, y)):
        model.fit(X[train], y[train])
        y_pred = model.predict(X[test])
        print(k, "=" * 100)
        print(classification_report(y[test], y_pred), '\n\n')


def run_svc():
    model = LinearSVC(penalty='l2', tol=1e-8, max_iter=10000, random_state=42, verbose=True)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    for k, (train, test) in enumerate(k_fold.split(X, y)):
        model.fit(X[train], y[train])
        y_pred = model.predict(X[test])
        print(k, "=" * 100)
        print(classification_report(y[test], y_pred), '\n\n')


def run_ada_boost():
    model = AdaBoostClassifier(n_estimators=100, random_state=0)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    for k, (train, test) in enumerate(k_fold.split(X, y)):
        model.fit(X[train], y[train])
        y_pred = model.predict(X[test])
        print(k, "=" * 100)
        print(classification_report(y[test], y_pred), '\n\n')


def run_random_forest():
    model = RandomForestClassifier(n_estimators=100, max_depth=2, random_state=0)

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    for k, (train, test) in enumerate(k_fold.split(X, y)):
        model.fit(X[train], y[train])
        y_pred = model.predict(X[test])
        print(k, "=" * 100)
        print(classification_report(y[test], y_pred), '\n\n')


def run_xgboost():
    model = xgb.XGBClassifier()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    for k, (train, test) in enumerate(k_fold.split(X, y)):
        model = model.fit(X[train], y[train])
        y_pred = model.predict(X[test])
        print(k, "=" * 100)
        print(classification_report(y[test], y_pred), '\n\n')


if __name__ == '__main__':
    # run_ada_boost()
    # run_random_forest()
    run_xgboost()
