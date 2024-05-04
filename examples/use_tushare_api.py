import czsc

# czsc.set_url_token(token="xxxxx", url="http://api.tushare.pro")

pro = czsc.DataClient(url="http://api.tushare.pro", cache_path="~/.quant_data_cache")
df = pro.income(
    ts_code="600000.SH",
    fields="ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,basic_eps,diluted_eps",
)
