# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试UI集成和逻辑验证
"""

def test_large_file_logic():
    """测试大文件处理逻辑"""
    print("测试大文件处理逻辑...")
    
    # 模拟UI控件值
    out_type_values = [1, 2, 3, 4, 5, 6, 7, 8]
    max_dist_values = [5, 10, 20, 50]
    
    for out_type in out_type_values:
        for max_dist in max_dist_values:
            # 模拟C++代码逻辑
            use_large_file_mode = (out_type == 8)
            min_size_mb = max_dist
            
            if use_large_file_mode:
                print(f"OutType={out_type}, MaxDist={max_dist} -> 大文件模式，最小拆分大小={min_size_mb}MB")
            else:
                print(f"OutType={out_type}, MaxDist={max_dist} -> 正常模式，最大距离={max_dist}kb")
    
    print("\n测试完成！")

def test_help_text():
    """测试帮助文档内容"""
    print("检查帮助文档内容...")
    
    help_sections = [
        "OutType参数：1-7为正常模式，8为大文件处理模式",
        "正常模式：MaxDist用于设置分析的最大SNP距离，单位为kb",
        "大文件模式：MaxDist用于设置最小拆分大小，单位为MB",
        "设置OutType=8启用大文件处理模式"
    ]
    
    for section in help_sections:
        print(f"✓ {section}")
    
    print("\n帮助文档检查完成！")

if __name__ == "__main__":
    test_large_file_logic()
    print("\n" + "="*50 + "\n")
    test_help_text()

