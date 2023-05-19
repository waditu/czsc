# czsc - 缠中说禅技术分析工具

[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=total&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Total)](https://pepy.tech/project/czsc)
[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=month&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Month)](https://pepy.tech/project/czsc)
[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=week&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Week)](https://pepy.tech/project/czsc)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![PyPI](https://img.shields.io/pypi/v/czsc.svg)](https://pypi.org/project/czsc/)
[![Documentation Status](https://readthedocs.org/projects/czsc/badge/?version=latest)](https://czsc.readthedocs.io/en/latest/?badge=latest)

**[API文档](https://czsc.readthedocs.io/en/latest/modules.html)** | 
**[项目文档](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf)** | 
**[投研数据共享](https://s0cqcxuy3p.feishu.cn/wiki/wikcnzuPawXtBB7Cj7mqlYZxpDh)** | 
**[信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)**

>源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)，原始博客中的内容不太完整，且没有评论，以下是网友整理的原文备份
* 备份网址1：https://chzhshch.blog
* 备份网址2：http://www.fxgan.com

>**假如没有了分型、笔、线段，缠论还是缠论吗？如果你的答案是“是”，这个项目是为你准备的。本项目旨在提供一个符合缠中说禅思维方式的程序化交易工具。**


## 项目贡献

* [择时策略研究框架](https://s0cqcxuy3p.feishu.cn/wiki/wikcnhizrtIOQakwVcZLMKJNaib)
* 缠论的 `分型、笔` 的自动识别，详见 `czsc/analyze.py`
* 定义并实现 `信号-因子-事件-交易` 量化交易逻辑体系，因子是信号的线性组合，事件是因子的同类合并，详见 `czsc/objects.py`
* 定义并实现了若干信号函数，详见 `czsc/signals`
* 缠论多级别联立决策分析交易，详见 `CzscTrader`
* 基于 Tushare 数据的择时、选股策略回测研究流程



## 安装使用

**注意:** python 版本必须大于等于 3.7 

直接从github安装：
```
pip install git@github.com:waditu/czsc.git -U
```

从`pypi`安装：
```
pip install czsc -U -i https://pypi.python.org/simple
```


## 信号开源计划

>学了本ID的理论，去再看其他的理论，就可以更清楚地看到其缺陷与毛病，因此，广泛地去看不同的理论，不仅不影响本ID理论的学习，更能明白本ID理论之所以与其他理论不同的根本之处。

>为什么要去了解其他理论，就是这些理论操作者的行为模式，将构成以后我们猎杀的对象，他们操作模式的缺陷，就是以后猎杀他们的最好武器，这就如同学独孤九剑，必须学会发现所有派别招数的缺陷，这也是本ID理论学习中一个极为关键的步骤。

信号开源计划旨在为缠论学习者提供一批其他理论对应的信号计算函数，供各位以量化的方式研究其他理论的缺陷和价值。这个计划的工作量极大，需要各位的参与。有意愿加入的朋友，请点击查看详情：**[CZSC信号开源计划介绍](https://s0cqcxuy3p.feishu.cn/wiki/wikcnx7707hlakYMi4HmxdAIHJg)**


## 使用前必看

* 目前的开发还在高频次的迭代中，对于已经在使用某个版本的用户，请谨慎更新，版本兼容性实在是太差，主要是因为当前还有太多考虑不完善的地方，我为此感到抱歉；
* 这是个人开发的项目，虽然我已经尽可能避坑，但可以很直接的说，这里面一定还有坑，使用前请仔细校验分析结果，发现新坑请告诉我，我来填；
* 目前开发完成度不高，**API会有比较大的变动，谨慎升级版本**，暂时不准备写文档，没有能力看懂源码的，不建议现在使用。
* 免责声明：项目开源仅用于技术交流！
* 如果你发现了项目中的 Bug，可以先读一下《[如何有效地报告 Bug](https://www.chiark.greenend.org.uk/~sgtatham/bugs-cn.html)》，然后在 [issues](https://github.com/waditu/czsc/issues) 中报告 Bug


## 使用案例

>案例中主要使用了 Tushare 的数据，开通相应的数据权限可以[点击联系](https://tushare.pro/document/2?doc_id=244)，备注：**CZSC用户**，1500元可以开通CZSC项目目前用到的全部数据权限。
>掘金终端主要用于交易策略的实盘跟踪，[点击了解](https://www.myquant.cn/)。

* `examples/ts_plates_sensor.py` 同花顺概念板块轮动策略回测
* `examples/ts_check_signal_acc.py` 验证信号计算的准确性，信号是否符合定义
* `examples/ts_stocks_sensors.py` 日线选股策略回测


## 原文整理

* [缠中说禅重新编排版《论语》（整理版）](https://blog.csdn.net/baidu_25764509/article/details/109517775)
* [缠中说禅交易指南](https://blog.csdn.net/baidu_25764509/article/details/109598229)
* [缠中说禅技术原理](https://blog.csdn.net/baidu_25764509/article/details/109597255)
* [缠中说禅图解分析示范](https://blog.csdn.net/baidu_25764509/article/details/110195063)
* [缠中说禅：缠非缠、禅非禅，枯木龙吟照大千（整理版）](https://blog.csdn.net/baidu_25764509/article/details/110775662)
* [缠中说禅教你打坐（整理版）](https://blog.csdn.net/baidu_25764509/article/details/113735170)

**注意：** 如果CSDN的连接打不开，可以直接在 `czsc/docs` 目录下查看 html 文件


## 资料分享

* 链接：https://pan.baidu.com/s/1RXkP3188F0qu8Yk6CjbxRQ
* 提取码：vhue


## [知识星球【CZSC小圈子】](https://t.zsxq.com/04B2jmUN7)费用：100元

**知识星球【CZSC小圈子】的定位是什么？**
  - 为仔细研读过禅师原文并且愿意使用 CZSC 库进行量化投研的朋友提供一个交流平台。
  - 寻找一群有能力的朋友共同进行量化策略研究。
  - 促成策略逻辑互补的实盘组合构建。
  - 对于刚接触缠论和量化交易的新朋友，给出一些力所能及的帮助。
> 详情点击：https://s0cqcxuy3p.feishu.cn/wiki/wikcnwXSk9mWnki1b6URPhLA2Hc
> 
> **加入知识星球后**，请加微信 `zengbin93`，备注【CZSC小圈子】
