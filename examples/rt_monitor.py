# coding: utf-8
"""
基于聚宽数据的实时日线因子监控
"""

# 首次使用需要设置聚宽账户
# from czsc.data.jq import set_token
# set_token("phone number", 'password') # 第一个参数是JQData的手机号，第二个参数是登录密码
import traceback
import time
import shutil
import os
import pickle
from datetime import datetime
from czsc.trader import CzscTrader, Factors
from czsc.utils.qywx import push_text, push_file

# =======================================================================================================
# 基础参数配置
ct_path = os.path.join(".", "czsc_traders")
os.makedirs(ct_path, exist_ok=True)
# 关于企业微信群聊机器人的使用文档，参考：https://work.weixin.qq.com/api/doc/90000/90136/91770
# 企业微信群聊机器人的key
qywx_key = "4ad2e226-2519-4893-8670-*****"

# 定义需要监控的股票列表
symbols = ["300033.XSHE", "300803.XSHE", "002739.XSHE"]
# =======================================================================================================


def save_pkl(data, file):
    with open(file, "wb") as f:
        pickle.dump(data, f)

def read_pkl(file):
    with open(file, "rb") as f:
        data = pickle.load(f)
    return data

def monitor(use_cache=True):
    push_text("自选股CZSC笔因子监控启动 @ {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), qywx_key)
    moni_path = os.path.join(ct_path, "monitor")
    # 首先清空历史快照
    if os.path.exists(moni_path):
        shutil.rmtree(moni_path)
    os.makedirs(moni_path, exist_ok=True)

    for s in symbols:
        print(s)
        try:
            file_ct = os.path.join(ct_path, "{}.ct".format(s))
            if os.path.exists(file_ct) and use_cache:
                ct: CzscTrader = read_pkl(file_ct)
                ct.update_factors()
            else:
                ct = CzscTrader(s, max_count=1000)
            save_pkl(ct, file_ct)

            # 每次执行，会在moni_path下面保存一份快照
            file_html_ = os.path.join(moni_path, f"{ct.symbol}_{ct.kf.end_dt.strftime('%Y%m%d%H%M')}.html")
            ct.take_snapshot(file_html_, width="1400px", height="580px")

            if ct.s['日线笔因子'] != Factors.Other.value:
                msg = "{} - {}\n".format(s, ct.s['日线笔因子'])
                msg += "同花顺F10：http://basic.10jqka.com.cn/{}".format(s[:6])
                push_text(msg, key=qywx_key)
                file_html_new = os.path.join(moni_path, f"{ct.symbol}_{ct.kf.end_dt.strftime('%Y%m%d%H%M')}.html")
                shutil.copyfile(file_html_, file_html_new)
                push_file(file_html_new, key=qywx_key)

        except Exception as e:
            traceback.print_exc()
            print("{} 执行失败 - {}".format(s, e))

    push_text("自选股CZSC笔因子监控结束 @ {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), qywx_key)

def run_monitor():
    mdt = ["09:30", "10:00", "10:30", "11:00", "11:20", "13:00", "13:30", "14:00", "14:30", "14:50"]
    monitor()
    while 1:
        print(datetime.now().strftime("%H:%M"))
        if datetime.now().strftime("%H:%M") in mdt:
            monitor()
        time.sleep(3)


if __name__ == '__main__':
    run_monitor()

