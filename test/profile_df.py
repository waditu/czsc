from cobra.data.kline import get_kline


def convert_to_list_v1(df):
    rows = [x.to_dict() for _, x in df.iterrows()]
    return rows


def convert_to_list_v2(df):
    rows = df.to_dict("records")
    return rows


def convert_to_list_v3(df):
    columns = df.columns.to_list()
    rows = [{k: v for k, v in zip(columns, row)} for row in df.values]
    return rows


if __name__ == '__main__':
    df = get_kline(ts_code="000001.SH", end_dt="2020-04-28 15:00:00", freq='D', asset='I')
    # convert_to_list_v1(df)
    convert_to_list_v2(df)


