# czsc - 缠中说禅技术分析工具
>源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)，欢迎加群探讨，
>QQ群：`1125818657`，加群请备注自己对缠论的了解程度，谢谢。


## 问题讨论

>在 [issues](https://github.com/zengbin93/czsc/issues) 中提出了一些值得探讨的实战问题，欢迎积极参与讨论，我可以负责实现一些好的想法，代码开源。

* [如何分析选股策略的历史表现？](https://github.com/zengbin93/czsc/issues/17)

## 原文整理

* [缠中说禅重新编排版《论语》（整理版）](https://blog.csdn.net/baidu_25764509/article/details/109517775)
* [缠中说禅交易指南](https://blog.csdn.net/baidu_25764509/article/details/109598229)
* [缠中说禅技术原理](https://blog.csdn.net/baidu_25764509/article/details/109597255)
* [缠中说禅图解分析示范](https://blog.csdn.net/baidu_25764509/article/details/110195063)

**注意：** 如果CSDN的连接打不开，可以直接在 `czsc/docs` 目录下查看 html 文件

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

目前已经实现了缠论的 笔、线段、中枢 的自动识别，核心代码在 `czsc.analyze` 中；

使用聚宽数据的快速入门请查看 `examples\czsc 快速入门教程.ipynb`

## 捐赠支持

>如果这个项目对你的交易有些许帮助，可以扫码捐赠，让我知道一下，感谢！另外，**可以顺便提一个问题或需求。**

<img src="https://github.com/zengbin93/czsc/blob/master/docs/donate.png" height="220" width="400">
