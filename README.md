# czsc - 缠中说禅技术分析工具

[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=total&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Total)](https://pepy.tech/project/czsc)
[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=month&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Month)](https://pepy.tech/project/czsc)
[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=week&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Week)](https://pepy.tech/project/czsc)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![PyPI](https://img.shields.io/pypi/v/czsc.svg)](https://pypi.org/project/czsc/)

>源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)

>**[官方文档（0.6.8）（暂未更新到最新版）](https://blog.csdn.net/baidu_25764509/article/details/110389764)**


```
主题: CZSC0.8.26 版本介绍 
日期: 2022-05-22 19:53:55
录制文件：https://meeting.tencent.com/v2/cloud-record/share?id=a361ce70-45e7-4499-b577-681e1dc01401&from=3
访问密码：xy4a
```

## 使用前必看

* 目前的开发还在高频次的迭代中，对于已经在使用某个版本的用户，请谨慎更新，版本兼容性实在是太差，主要是因为当前还有太多考虑不完善的地方，我为此感到抱歉；
* 这是个人开发的项目，虽然我已经尽可能避坑，但可以很直接的说，这里面一定还有坑，使用前请仔细校验分析结果，发现新坑请告诉我，我来填；
* 目前开发完成度不高，**API会有比较大的变动，谨慎升级版本**，暂时不准备写文档，没有能力看懂源码的，不建议现在使用。
* 免责声明：项目开源仅用于技术交流！
* 如果你发现了项目中的 Bug，可以先读一下《[如何有效地报告 Bug](https://www.chiark.greenend.org.uk/~sgtatham/bugs-cn.html)》，然后在 [issues](https://github.com/waditu/czsc/issues) 中报告 Bug

## 项目贡献

* 缠论的 `分型、笔` 的自动识别，详见 `czsc/analyze.py`
* 定义并实现 `信号-因子-事件-交易` 量化交易逻辑体系，因子是信号的线性组合，事件是因子的同类合并，详见 `czsc/objects.py`
* 定义并实现了若干种基于笔的信号，详见 `czsc/signals.py`
* 缠论多级别联立决策分析交易，详见 `czsc/traders/advanced.py`
* 基于 Tushare 数据的择时、选股策略回测研究流程

## 使用案例

>案例中主要使用了 Tushare 的数据，开通相应的数据权限可以[点击联系](https://tushare.pro/document/2?doc_id=244)，说明是CZSC用户，1500元可以开通CZSC项目目前用到的全部数据权限。
>掘金终端主要用于交易策略的实盘跟踪，[点击了解](https://www.myquant.cn/)。

* `examples/ts_fast_backtest.py` 股票市场择时策略快速回测
* `examples/ts_plates_sensor.py` 同花顺概念板块轮动策略回测
* `examples/ts_check_signal_acc.py` 验证信号计算的准确性，信号是否符合定义
* `examples/ts_stocks_sensors.py` 日线选股策略回测
* `examples/gm_backtest.py` 使用掘金终端进行缠论策略回测
* `examples/gm_realtime.py` 使用掘金终端进行策略实盘、仿真
* `examples/gm_check_point.py` 使用掘金终端的数据进行买卖点验证

## 问题讨论

>在 [discussions](https://github.com/zengbin93/czsc/discussions) 中提出了一些值得探讨的实战问题，欢迎积极参与讨论，我可以负责实现一些好的想法，代码开源。

* [如何分析选股策略的历史表现？](https://github.com/zengbin93/czsc/discussions/34)
* [常见问题（FAQ）](https://github.com/zengbin93/czsc/discussions/32)

## 原文整理

* [缠中说禅重新编排版《论语》（整理版）](https://blog.csdn.net/baidu_25764509/article/details/109517775)
* [缠中说禅交易指南](https://blog.csdn.net/baidu_25764509/article/details/109598229)
* [缠中说禅技术原理](https://blog.csdn.net/baidu_25764509/article/details/109597255)
* [缠中说禅图解分析示范](https://blog.csdn.net/baidu_25764509/article/details/110195063)
* [缠中说禅：缠非缠、禅非禅，枯木龙吟照大千（整理版）](https://blog.csdn.net/baidu_25764509/article/details/110775662)
* [缠中说禅教你打坐（整理版）](https://blog.csdn.net/baidu_25764509/article/details/113735170)

**注意：** 如果CSDN的连接打不开，可以直接在 `czsc/docs` 目录下查看 html 文件


## 形态挖掘

* [缠中说禅形态挖掘之五笔形态](https://blog.csdn.net/baidu_25764509/article/details/113639353)
* [缠中说禅形态挖掘之七笔形态](https://blog.csdn.net/baidu_25764509/article/details/113649988)
* [缠中说禅形态挖掘之九笔形态](https://blog.csdn.net/baidu_25764509/article/details/113688926)
* [本级别笔对应的小级别形态](https://blog.csdn.net/baidu_25764509/article/details/113563530)

## 安装

**注意:** python 版本必须大于等于 3.7 

直接从github安装：
```
pip install git+git://github.com/zengbin93/czsc.git -U
```

从`pypi`安装：
```
pip install czsc -U -i https://pypi.python.org/simple
```

## 使用方法

目前已经实现了缠论的 `分型、笔` 的自动识别，核心代码在 `czsc.analyze` 中；

## 资料分享

* 链接：https://pan.baidu.com/s/1RXkP3188F0qu8Yk6CjbxRQ
* 提取码：vhue

## 捐赠支持

>如果这个项目对你的交易有些许帮助，可以加微信 `zengbin93` 进行捐赠，感谢！

