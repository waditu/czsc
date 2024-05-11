import pandas as pd

df = pd.read_feather(r"D:\ZB\git_repo\waditu\czsc\czsc\utils\minites_split.feather")
df.to_csv(r"C:\Users\zengb\Desktop\minites_split.csv", index=False, encoding="gbk")

# df = pd.read_feather(r"C:\Users\zengb\Desktop\minites_split_240317.feather")

df = pd.read_csv(r"C:\Users\zengb\Desktop\minites_split.csv", encoding="gbk")
# df.to_excel(r"C:\Users\zengb\Desktop\minites_split.xlsx", index=False)
cols = [x for x in df.columns if x not in ["market"]]
for col in cols:
    df[col] = pd.to_datetime(df[col]).dt.strftime("%H:%M")

df.to_feather(r"D:\ZB\git_repo\waditu\czsc\czsc\utils\minites_split.feather")
