# czsc - 缠中说禅技术分析工具
>源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)，欢迎加群探讨，
>QQ群：`1125818657`，加群请备注自己对缠论的了解程度，谢谢。

>**[官方文档（0.6.8）（未更新到0.7.3）](https://blog.csdn.net/baidu_25764509/article/details/110389764)**

## 使用前必看

* 这是个人开发的项目，虽然我已经尽可能的避坑，但可以很直接的说，这里面一定还有坑，使用前请仔细校验分析结果，发现新坑请告诉我，我来填；
* 目前开发完成度不高，API可能会有比较大的变动，暂时不准备写文档，没有能力看懂源码的，不建议现在使用。
* 免责声明：项目开源仅用于技术交流！

## 项目贡献

* 缠论的 `分型、笔` 的自动识别，详见 `czsc/analyze.py`
* 定义并实现 `信号-因子-事件-交易` 量化交易逻辑体系，详见 `czsc/objects.py`
* 定义并实现了若干种基于笔的信号，详见 `czsc/signals.py`

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

使用聚宽数据的快速入门请查看 `examples\czsc_quick_start.py`

## 捐赠支持

>如果这个项目对你的交易有些许帮助，可以扫码捐赠，让我知道一下，感谢！另外，**可以顺便提一个问题或需求。**

<img src="https://github.com/zengbin93/czsc/blob/master/docs/donate.png" height="220" width="400">

