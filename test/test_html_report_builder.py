"""测试 html_report_builder 模块的功能"""
import sys
sys.path.append("..")
sys.path.insert(0, ".")
import czsc
from czsc.utils.html_report_builder import HtmlReportBuilder
import pandas as pd
import os


def test_html_report_builder_basic():
    """测试 HtmlReportBuilder 基本功能"""
    print("测试 HtmlReportBuilder 基本功能...")
    
    # 创建构建器
    builder = HtmlReportBuilder(title="测试报告")
    
    # 测试添加头部
    params = {
        "日期": "2024-01-01",
        "版本": "v1.0",
        "作者": "测试用户"
    }
    builder.add_header(params, subtitle="这是一个测试报告")
    
    # 测试添加绩效指标
    metrics = [
        {"label": "收益率", "value": "15.3%", "is_positive": True},
        {"label": "最大回撤", "value": "-8.2%", "is_positive": False},
        {"label": "夏普比率", "value": "1.85", "is_positive": True}
    ]
    builder.add_metrics(metrics)
    
    # 测试添加自定义章节
    custom_content = """
    <div class="alert alert-info">
        <h4>策略说明</h4>
        <p>这是一个基于缠论技术分析的量化交易策略测试。</p>
    </div>
    """
    builder.add_section("策略说明", custom_content, icon="bi-info-circle")
    
    # 测试添加数据表格
    test_data = pd.DataFrame({
        "日期": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "收益": ["1.2%", "-0.5%", "2.1%"],
        "持仓": ["100%", "80%", "120%"]
    })
    builder.add_table(test_data, title="交易记录", max_rows=10)
    
    # 测试添加页脚
    builder.add_footer("自定义页脚信息 - 2024年测试")
    
    # 生成HTML
    html_content = builder.render()
    
    # 验证HTML包含基本元素
    assert "<!DOCTYPE html>" in html_content, "HTML应该包含DOCTYPE声明"
    assert "测试报告" in html_content, "HTML应该包含标题"
    assert "2024-01-01" in html_content, "HTML应该包含日期参数"
    assert "15.3%" in html_content, "HTML应该包含收益率指标"
    assert "策略说明" in html_content, "HTML应该包含自定义章节"
    assert "交易记录" in html_content, "HTML应该包含表格标题"
    assert "自定义页脚信息" in html_content, "HTML应该包含自定义页脚"
    
    print("✓ HTML内容验证通过")
    
    # 测试保存文件
    output_path = "test_html_report_builder.html"
    builder.save(output_path)
    
    # 验证文件存在
    assert os.path.exists(output_path), f"文件 {output_path} 应该存在"
    
    # 验证文件大小合理（至少包含基本HTML结构）
    file_size = os.path.getsize(output_path)
    assert file_size > 1000, f"文件大小应该大于1KB，实际为 {file_size} 字节"
    
    print(f"✓ 报告已生成: {output_path} ({file_size} 字节)")
    
    # 清理测试文件
    try:
        os.remove(output_path)
        print("✓ 测试文件已清理")
    except:
        pass
    
    return True


def test_html_report_builder_chain_calls():
    """测试链式调用功能"""
    print("\n测试链式调用功能...")
    
    # 测试链式调用
    builder = (HtmlReportBuilder(title="链式调用测试")
              .add_header({"测试": "值"}, subtitle="链式调用")
              .add_metrics([{"label": "测试指标", "value": "100%", "is_positive": True}])
              .add_section("测试章节", "<p>测试内容</p>")
              .add_footer())
    
    # 验证链式调用正常工作
    html_content = builder.render()
    assert "链式调用测试" in html_content
    assert "测试指标" in html_content
    assert "测试章节" in html_content
    
    print("✓ 链式调用功能正常")
    
    return True


def test_html_report_builder_empty_charts():
    """测试空图表处理"""
    print("\n测试空图表处理...")
    
    builder = HtmlReportBuilder(title="空图表测试")
    builder.add_header({"测试": "值"})
    
    # 直接调用 add_charts_section，没有添加任何图表
    builder.add_charts_section()
    builder.add_footer()
    
    html_content = builder.render()
    # 应该不包含图表相关内容，但不报错
    assert "空图表测试" in html_content
    
    print("✓ 空图表处理正常")
    
    return True


def test_html_report_builder_custom_styles():
    """测试自定义样式功能"""
    print("\n测试自定义样式功能...")
    
    builder = HtmlReportBuilder(title="自定义样式测试")
    
    # 添加自定义CSS
    custom_css = """
    .custom-highlight {
        background-color: #ffff00;
        font-weight: bold;
    }
    """
    builder.add_custom_css(custom_css)
    
    # 添加自定义JavaScript
    custom_script = """
    console.log("自定义脚本执行");
    """
    builder.add_custom_script(custom_script)
    
    builder.add_header({"测试": "值"}).add_footer()
    
    html_content = builder.render()
    
    # 验证自定义样式和脚本被包含
    assert "custom-highlight" in html_content, "应该包含自定义CSS"
    assert "自定义脚本执行" in html_content, "应该包含自定义JavaScript"
    
    print("✓ 自定义样式功能正常")
    
    return True


def test_html_report_builder_chart_tabs():
    """测试图表标签页功能"""
    print("\n测试图表标签页功能...")
    
    builder = HtmlReportBuilder(title="图表标签页测试")
    
    # 模拟图表HTML
    mock_chart1 = '<div class="plotly-graph-div">图表1内容</div>'
    mock_chart2 = '<div class="plotly-graph-div">图表2内容</div>'
    mock_chart3 = '<div class="plotly-graph-div">图表3内容</div>'
    
    # 添加多个图表标签页
    builder.add_chart_tab("图表1", mock_chart1, "bi-bar-chart", active=True)
    builder.add_chart_tab("图表2", mock_chart2, "bi-line-chart")
    builder.add_chart_tab("图表3", mock_chart3, "bi-pie-chart")
    
    # 添加图表区域
    builder.add_charts_section()
    builder.add_footer()
    
    html_content = builder.render()
    
    # 验证图表标签页
    assert "图表1" in html_content
    assert "图表2" in html_content
    assert "图表3" in html_content
    assert "图表1内容" in html_content
    assert "图表2内容" in html_content
    assert "图表3内容" in html_content
    
    print("✓ 图表标签页功能正常")
    
    return True


def test_html_report_builder_integration():
    """测试与现有回测报告功能的集成"""
    print("\n测试与现有回测报告功能的集成...")
    
    try:
        from czsc.utils.backtest_report import generate_backtest_report
        
        # 生成测试数据
        dfw = czsc.mock.generate_klines_with_weights()
        
        # 生成报告
        output_path = "test_integration_report.html"
        result_path = generate_backtest_report(
            df=dfw,
            output_path=output_path,
            title="集成测试报告",
            fee_rate=0.00,
            digits=2,
            weight_type="ts",
            yearly_days=252
        )
        
        # 验证文件生成
        assert os.path.exists(result_path), f"集成测试报告文件应该存在: {result_path}"
        
        file_size = os.path.getsize(result_path)
        assert file_size > 5000, f"集成测试报告文件应该包含完整内容，实际大小: {file_size} 字节"
        
        print(f"✓ 集成测试报告生成成功: {result_path} ({file_size} 字节)")
        
        # 清理测试文件
        try:
            os.remove(result_path)
            print("✓ 集成测试文件已清理")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试 HtmlReportBuilder 功能")
    print("=" * 60)
    
    tests = [
        ("基本功能测试", test_html_report_builder_basic),
        ("链式调用测试", test_html_report_builder_chain_calls),
        ("空图表处理测试", test_html_report_builder_empty_charts),
        ("自定义样式测试", test_html_report_builder_custom_styles),
        ("图表标签页测试", test_html_report_builder_chart_tabs),
        ("集成测试", test_html_report_builder_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 60}")
            print(f"运行测试: {test_name}")
            print(f"{'=' * 60}")
            
            if test_func():
                print(f"✓ {test_name} 通过")
                passed += 1
            else:
                print(f"✗ {test_name} 失败")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} 异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"{'=' * 60}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n✓ 所有测试通过！")
        exit(0)
    else:
        print("\n✗ 部分测试失败！")
        exit(1)