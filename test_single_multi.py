# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证单群体和多群体标题设置
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 模拟单群体情况
print("=== 测试单群体情况 ===")
sys.argv = ['plot_lddecay_multi.py', 'test_prefix', '10', '100', '100', '500', 'single_file.stat']
exec(open('src/plot_lddecay_multi.py').read())

print("\n=== 测试多群体情况 ===")
# 模拟多群体情况
sys.argv = ['plot_lddecay_multi.py', 'test_prefix', '10', '100', '100', '500', 'file1.stat', 'file2.stat', 'file3.stat']
exec(open('src/plot_lddecay_multi.py').read())
