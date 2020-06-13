# czsc - 缠中说禅技术分析工具
>源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)，欢迎加微信探讨，我的微信号是 `zengbin93`

* [在线体验](http://103.235.232.152:8005/?ts_code=000001.SH&asset=I&trade_date=20200228&freqs=5min,30min)
* 参数说明：1）ts_code 是 tushare 的代码；2）asset 现在有两个值，E 表示股票，I 表示指数

## 安装

直接从github安装：
```
pip install git+git://github.com/zengbin93/czsc.git -U
```

从`pypi`安装：
```
pip install czsc -U -i https://pypi.python.org/simple
```

## K线数据样例

`dt` 的格式统一为 `%Y-%m-%d %H:%M:%S`，如 `2020-02-27 00:00:00`

```markdown
         symbol                   dt   open  close   high    low     vol
0     300803.SZ  2020-01-17 09:31:00  44.08  44.19  44.30  44.01  170160
1     300803.SZ  2020-01-17 09:32:00  44.06  44.24  44.24  43.93   91100
2     300803.SZ  2020-01-17 09:33:00  44.10  43.91  44.17  43.91   90251
3     300803.SZ  2020-01-17 09:34:00  43.90  43.86  43.90  43.81   61100
4     300803.SZ  2020-01-17 09:35:00  43.86  43.66  43.86  43.61   75900
5     300803.SZ  2020-01-17 09:36:00  43.66  43.80  43.86  43.66   56600
6     300803.SZ  2020-01-17 09:37:00  43.81  43.67  43.82  43.67   68600
7     300803.SZ  2020-01-17 09:38:00  43.67  43.60  43.67  43.53   97554
8     300803.SZ  2020-01-17 09:39:00  43.60  43.62  43.70  43.57  118861
```

* dt 表示 该周期的交易结束时间


## 使用方法

目前已经实现了缠论的 笔、线段、中枢 的自动识别，核心代码在 `chan.analyze` 中；

使用 Tushare Pro / 聚宽 / 掘金 / 天勤 的数据进行缠中说禅技术分析结果展示: https://github.com/zengbin93/czsc_web_ui

## 结合 tushare.pro 的数据使用

py 文件地址： examples/combine_with_tushare.py

没有 token，到 https://tushare.pro/register?reg=7 注册下

## 结合掘金的数据使用

py 文件地址： examples/combine_with_goldminer.py


