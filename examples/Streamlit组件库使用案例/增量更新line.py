import streamlit as st
import pandas as pd
import numpy as np
import time
st.set_page_config(layout="wide")
df1 = pd.DataFrame(
    np.random.randn(50, 20), columns=("col %d" % i for i in range(20))
)

# my_table = st.table(df1)

df2 = pd.DataFrame(
    np.random.randn(50, 20), columns=("col %d" % i for i in range(20))
)

# my_table.add_rows(df2)
# Now the table shown in the Streamlit app contains the data for
# df1 followed by the data for df2.

# Assuming df1 and df2 from the example above still exist...
my_chart = st.line_chart(df1)
# time.sleep(5)
for i in range(len(df2)):
    dfr = df2.iloc[i-1:i]
    my_chart.add_rows(dfr)
    time.sleep(1)
# Now the chart shown in the Streamlit app contains the data for
# df1 followed by the data for df2.