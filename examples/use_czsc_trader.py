# coding: utf-8

# 首次使用需要设置聚宽账户
# from czsc.data.jq import set_token
# set_token("phone number", 'password') # 第一个参数是JQData的手机号，第二个参数是登录密码

from datetime import datetime
import czsc
from czsc.trader import CzscTrader

assert czsc.__version__ >= '0.6.9'

# 在默认浏览器中打开最新分析结果，
ct = CzscTrader(symbol="000001.XSHG", end_date=datetime.now())
ct.open_in_browser(width="1400px", height="580px")
# open_in_browser 方法可以在windows系统中使用，如果无法使用，可以直接保存结果到 html 文件
# ct.take_snapshot(file_html="czsc_results.html", width="1400px", height="580px")


# 在默认浏览器中打开指定结束日期的分析结果）
ct = CzscTrader(symbol="000001.XSHG", end_date="2021-03-04")
ct.open_in_browser(width="1400px", height="580px")

# 推演分析：从某一天开始，逐步推进
ct = CzscTrader(symbol="000001.XSHG", end_date="2008-01-01")
ct.open_in_browser()
ct.forward(n=10)    # 行情向前推进十天
ct.open_in_browser()


