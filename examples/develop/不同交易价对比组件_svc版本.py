"""
使用 CZSC SVC 模块的价格敏感性分析示例

该示例展示了如何使用新的模块化 svc 组件进行价格敏感性分析。
与原版本相比，新版本具有更好的模块化结构和错误处理。

"""
import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import czsc
import pandas as pd
import numpy as np
import streamlit as st

# 使用新的 svc 模块导入
from czsc.svc import show_price_sensitive

st.set_page_config(page_title="SVC版本 - 价格敏感性分析", layout="wide")

def user_input_form():
    """用户输入表单"""
    with st.form(key="user_input_form"):
        c1, c2, c3 = st.columns([2, 1, 1])
        
        file = c1.file_uploader("上传文件", type=["csv", "feather"], accept_multiple_files=False)
        fee = c2.number_input("单边费率（BP）", value=2.0, step=0.1, min_value=-100.0, max_value=100.0)
        digits = c2.number_input("小数位数", value=2, step=1, min_value=0, max_value=10)
        
        weight_type = c3.selectbox("权重类型", ["ts", "cs"], index=0)
        n_jobs = c3.number_input("并行数", value=1, step=1, min_value=1, max_value=10)
        
        submit_button = st.form_submit_button(label="开始测试")

    if not submit_button or file is None:
        st.stop()

    # 文件读取
    df = _read_uploaded_file(file)
    return df, fee, digits, weight_type, n_jobs


def _read_uploaded_file(file) -> pd.DataFrame:
    """读取上传的文件"""
    if file.name.endswith(".csv"):
        # 尝试多种编码
        for encoding in ["utf-8", "gbk", "gb2312"]:
            try:
                df = pd.read_csv(file, encoding=encoding)
                st.success(f"文件读取成功，使用编码: {encoding}")
                return df
            except Exception as e:
                continue
        raise ValueError(f"文件读取失败，请检查文件编码")
    
    elif file.name.endswith(".feather"):
        df = pd.read_feather(file)
        st.success("Feather文件读取成功")
        return df
    
    else:
        raise ValueError(f"不支持的文件类型: {file.name}")


def main():
    """主函数"""
    st.title("🔍 价格敏感性分析 - SVC模块版本")
    st.markdown("---")
    
    # 显示模块信息
    with st.expander("ℹ️ 关于 SVC 模块", expanded=False):
        st.markdown("""
        **SVC (Streamlit Visualize Components)** 是 CZSC 的新一代可视化组件库：
        
        ✅ **模块化设计**: 按功能分为多个子模块，便于维护和扩展  
        ✅ **向后兼容**: 保持所有原有接口不变  
        ✅ **统一错误处理**: 更友好的错误提示和容错机制  
        ✅ **性能优化**: 统一的导入处理和样式配置  
        ✅ **类型注解**: 更好的代码提示和文档
        
        **价格敏感性分析模块特性**:
        - 支持多种交易价格对比（TP_开头的列）
        - 自动化回测指标计算
        - 可视化累计收益对比  
        - 敏感性评估和排名
        - 结果导出功能
        """)
    
    try:
        # 获取用户输入
        df, fee, digits, weight_type, n_jobs = user_input_form()
        
        # 数据验证
        _validate_dataframe(df)
        
        # 显示数据信息
        with st.expander("📊 数据概览", expanded=False):
            st.markdown(f"**数据形状**: {df.shape}")
            st.markdown(f"**列名**: {list(df.columns)}")
            
            # 查找交易价格列
            tp_cols = [col for col in df.columns if col.startswith("TP")]
            if tp_cols:
                st.markdown(f"**发现交易价格列**: {tp_cols}")
            else:
                st.warning("未发现交易价格列（以TP开头），请检查数据格式")
                return
        
        st.markdown("---")
        
        # 使用新的 SVC 模块进行价格敏感性分析
        st.markdown("### 🎯 价格敏感性分析结果")
        
        results = show_price_sensitive(
            df=df, 
            fee=fee, 
            digits=digits, 
            weight_type=weight_type, 
            n_jobs=n_jobs,
            title_prefix="SVC模块 - ",
            show_detailed_stats=True,  # 显示详细统计
            export_results=True        # 启用导出功能
        )
        
    except Exception as e:
        st.error(f"分析过程中发生错误: {e}")
        st.exception(e)


def _validate_dataframe(df: pd.DataFrame):
    """验证数据框格式"""
    required_cols = ["symbol", "dt", "weight", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(f"数据验证失败，缺少必要的列: {missing_cols}")
        st.stop()
    
    # 检查数据类型
    if not pd.api.types.is_datetime64_any_dtype(df['dt']):
        try:
            df['dt'] = pd.to_datetime(df['dt'])
            st.info("已自动转换 dt 列为datetime格式")
        except:
            st.error("dt 列无法转换为datetime格式")
            st.stop()

if __name__ == "__main__":
    main() 