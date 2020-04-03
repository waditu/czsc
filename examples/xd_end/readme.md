# 线段当下结束的判断


基本思路：
* 1）仿真交易，获取判断线段结束需要的特征，并构建线段方向的分类数据集；
* 2）训练分类器，得到模型，实盘中，输入特征，得到线段方向。


**Note:** 仿真依赖 `cobra`，执行 `pip install git+git://github.com/zengbin93/cobra.git -U` 进行安装

