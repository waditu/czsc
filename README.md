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
* 备份网址1：http://www.fxgan.com
* 备份网址2：https://chzhshch.blog

* 已经开始用czsc库进行量化研究的朋友，欢迎[加入飞书群](https://applink.feishu.cn/client/chat/chatter/add_by_link?link_token=0bak668e-7617-452c-b935-94d2c209e6cf)，快点击加入吧！
* [B站视频教程合集（持续更新...）](https://space.bilibili.com/243682308/channel/series)

> 最近在考虑使用 vue + rust + tauri 为 CZSC 开发一个桌面应用，欢迎有兴趣的朋友一起参与。
> 如果你碰巧熟悉 vue、tauri、rust 的使用，或者擅长 **UI/UX 设计**，欢迎加入我们的开发组，一起为 CZSC 开发一个更好的桌面应用。
> 有意愿的朋友请联系我，微信号：**zengbin93**，备注：**桌面应用开发**。我们将为你提供一个更好的量化交易学习和交流平台。

## 缠论精华

>学了本ID的理论，去再看其他的理论，就可以更清楚地看到其缺陷与毛病，因此，广泛地去看不同的理论，不仅不影响本ID理论的学习，更能明白本ID理论之所以与其他理论不同的根本之处。

>为什么要去了解其他理论，就是这些理论操作者的行为模式，将构成以后我们猎杀的对象，他们操作模式的缺陷，就是以后猎杀他们的最好武器，这就如同学独孤九剑，必须学会发现所有派别招数的缺陷，这也是本ID理论学习中一个极为关键的步骤。

>真正的预测，就是不测而测。所有预测的基础，就是分类，把所有可能的情况进行完全分类。有人可能说，分类以后，把不可能的排除，最后一个结果就是精确的。
>这是脑子锈了的想法，任何的排除，等价于一次预测，每排除一个分类，按概率的乘法原则，就使得最后的所谓精确变得越不精确，最后还是逃不掉概率的套子。
>对于预测分类的唯一正确原则就是不进行任何排除，而是要严格分清每种情况的边界条件。任何的分类，其实都等价于一个分段函数，就是要把这分段函数的边界条件确定清楚。 
>边界条件分段后，就要确定一旦发生哪种情况就如何操作，也就是把操作也同样给分段化了。然后，把所有情况交给市场本身，让市场自己去当下选择。
>所有的操作，其实都是根据不同分段边界的一个结果，只是每个人的分段边界不同而已。因此，问题不是去预测什么，而是确定分段边界。

## 项目贡献

* **[择时策略研究框架](https://s0cqcxuy3p.feishu.cn/wiki/wikcnhizrtIOQakwVcZLMKJNaib)**
* 缠论的 `分型、笔` 的自动识别，详见 `czsc/analyze.py`
* 定义并实现 `信号-因子-事件-交易` 量化交易逻辑体系，因子是信号的线性组合，事件是因子的同类合并，详见 `czsc/objects.py`
* 定义并实现了若干信号函数，详见 `czsc/signals`
* 缠论多级别联立决策分析交易，详见 `CzscTrader`
* **[Streamlit 量化研究组件库](https://s0cqcxuy3p.feishu.cn/wiki/AATuw5vN7iN9XbkVPuwcE186n9f)**


## 安装使用

**注意:** python 版本必须大于等于 3.8

直接从github安装：
```
pip install git@github.com:waditu/czsc.git -U
```

直接从github指定分支安装最新版：
```
pip install git+https://github.com/waditu/czsc.git@V0.9.46 -U
```

从`pypi`安装：
```
pip install czsc -U -i https://pypi.python.org/simple
```

## 使用案例

1. [使用 tqsdk 进行期货交易](https://s0cqcxuy3p.feishu.cn/wiki/wikcn41lQIAJ1f8v41Dj5eAmrub)
2. [CTA择时：缠论30分钟笔非多即空](https://s0cqcxuy3p.feishu.cn/wiki/YPlewoj70ikwxakPnOucTP8lnYg)
3. [使用CTA研究UI页面进行策略研究](https://s0cqcxuy3p.feishu.cn/wiki/JWe3wo1VNiglO9kE999cGy8innh)


## 使用前必看

* 目前的开发还在高频次的迭代中，对于已经在使用某个版本的用户，请谨慎更新，版本兼容性实在是太差，主要是因为当前还有太多考虑不完善的地方，我为此感到抱歉；
* 这是个人开发的项目，虽然我已经尽可能避坑，但可以很直接的说，这里面一定还有坑，使用前请仔细校验分析结果，发现新坑请告诉我，我来填；
* 目前开发完成度不高，**API会有比较大的变动，谨慎升级版本**，暂时不准备写文档，没有能力看懂源码的，不建议现在使用。
* 免责声明：项目开源仅用于技术交流！
* 如果你发现了项目中的 Bug，可以先读一下《[如何有效地报告 Bug](https://www.chiark.greenend.org.uk/~sgtatham/bugs-cn.html)》，然后在 [issues](https://github.com/waditu/czsc/issues) 中报告 Bug


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
