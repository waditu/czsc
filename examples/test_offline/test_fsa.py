# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/16 19:51
describe: 
"""
import os
import pandas as pd
from loguru import logger

logger.enable('fsa.base')


def test_fsa_base():
    from czsc.fsa.base import FeishuApiBase

    app = FeishuApiBase(app_id=os.environ['app_id'], app_secret=os.environ['app_secret'])
    print(app.get_access_token())

    # res = app.upload_file(file_path=r"D:\ZB\git_repo\zengbin93\fsa\fsa\spreed_sheets.py", parent_node='fldcnRHcnV1d1UDs7EWRk1PpcIh')

    # app.copy(token='shtcnLpzhhsKwbmlJXHlrWCp4mf', payload={
    #     "name": "共享文件策略",
    #     "type": "sheet",
    #     "folder_token": "fldcnBD3C3F9ZePfEwdykzIXRtp"
    # })

    # app.move(token='shtcn9fZEefDeGAclDTNc4v6J8e',
    #          payload={"type": "sheet", "folder_token": "fldcnRHcnV1d1UDs7EWRk1PpcIh"})


def test_spread_sheets():
    from czsc.fsa.spreed_sheets import SpreadSheets

    app = SpreadSheets(app_id=os.environ['app_id'], app_secret=os.environ['app_secret'])

    folder_token = app.get_root_folder_token()
    token = app.create(folder_token, title="电子表格API测试")
    token = token['data']['spreadsheet']['spreadsheet_token']
    res = app.get_sheets(token)
    sheet_id = res['data']['sheets'][0]['sheet_id']
    app.delete_values(token, sheet_id)
    meta = app.get_sheet_meta(token, sheet_id)
    assert meta['data']['sheet']['grid_properties']['row_count'] == 1
    assert meta['data']['sheet']['grid_properties']['column_count'] == 1

    df = pd.DataFrame({'x': list(range(100)), 'y': list(range(100)), 'z': list(range(100))})
    app.append(token, sheet_id, df)
    meta = app.get_sheet_meta(token, sheet_id)
    assert meta['data']['sheet']['grid_properties']['row_count'] == 101
    assert meta['data']['sheet']['grid_properties']['column_count'] == 3

    dfr = app.read_table(token, sheet_id)
    assert dfr.shape == df.shape

    app.delete_values(token, sheet_id)
    meta = app.get_sheet_meta(token, sheet_id)
    assert meta['data']['sheet']['grid_properties']['row_count'] == 1
    assert meta['data']['sheet']['grid_properties']['column_count'] == 1

    app.remove(token, kind='sheet')


