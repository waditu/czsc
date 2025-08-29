import sys
sys.path.insert(0, r"D:\ZB\git_repo\waditu\czsc")
import czsc


def test_tushare_pro():
    # czsc.set_url_token("******", url="http://api.tushare.pro")
    dc = czsc.DataClient(url="http://api.tushare.pro")
    df = dc.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date', ttl=5)
    try:
        df = dc.stock_basic_1(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    except Exception as e:
        print(e)


def test_cooperation():
    from czsc.connectors import cooperation as coo
    symbols = coo.get_symbols(name='股票')
    assert len(symbols) > 1000
    futures = coo.get_symbols(name='期货主力')
    assert len(futures) > 50
    bars = coo.get_raw_bars(symbol='000001.SZ', freq='日线', sdt='20200101', edt='20231118', fq='后复权')
    bars = coo.get_raw_bars(symbol='000001.SZ', freq='60分钟', sdt='20230101', edt='20231118', fq='后复权')
    bars = coo.get_raw_bars(symbol='SFIC9001', freq='60分钟', sdt='20230101', edt='20231118', fq='后复权')


if __name__ == '__main__':
    test_tushare_pro()
