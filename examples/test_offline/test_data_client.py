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


if __name__ == '__main__':
    test_tushare_pro()
