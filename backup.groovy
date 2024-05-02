def DKX(close: np.array, low: np.array, open: np.array,high: np.array):
    '''
    多空线指标计算函数，输入close,low,open,high,输出多空线相关三个指标,DKX MADKX DEX
    '''
    mid = (3 * close + low + open + high) / 6
    dkx = [np.nan] * 20
    for n in range(20, len(mid)):
        dkx_value = (20*mid[n]+19*mid[n-1]+18*mid[n-2]+17*mid[n-3]+16*mid[n-4]+15*mid[n-5]
                +14*mid[n-6]+13*mid[n-7]+12*mid[n-8]+11*mid[n-9]+10*mid[n-10]+9*mid[n-11]
                +8*mid[n-12]+7*mid[n-13]+6*mid[n-14]+5*mid[n-15]+4*mid[n-16]
                +3*mid[n-17]+2*mid[n-18]+mid[n-20])/210
        dkx.append(dkx_value)
    # 计算MADKX和DEX值
    madkx = np.convolve(dkx, np.ones(10), 'valid') / 10
    madkx = np.append(np.full(9, np.nan), madkx)  # 为了和dkx的长度一致，前面填充nan
    dex = dkx - madkx
    return dkx, madkx, dex



cd c:\users\liujian\appdata\local\programs\python\python39\scripts
streamlit run d:\stock\czsc\JSONreplayV230911.py
