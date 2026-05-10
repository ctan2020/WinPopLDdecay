# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试VCF拆分逻辑的简单脚本
"""

import os
import tempfile
import gzip
from split_large_vcf import analyze_chromosome_sizes, get_file_size_mb

def create_test_vcf():
    """创建一个测试VCF文件"""
    test_data = """##fileformat=VCFv4.2
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	Sample1	Sample2
chr1	1000	.	A	T	60	PASS	DP=100	GT	0/0	0/1
chr1	2000	.	G	C	60	PASS	DP=100	GT	0/1	1/1
chr1	3000	.	T	A	60	PASS	DP=100	GT	1/1	0/0
chr2	1000	.	A	T	60	PASS	DP=100	GT	0/0	0/1
chr2	2000	.	G	C	60	PASS	DP=100	GT	0/1	1/1
chr3	1000	.	A	T	60	PASS	DP=100	GT	0/0	0/1
chr3	2000	.	G	C	60	PASS	DP=100	GT	0/1	1/1
chr3	3000	.	T	A	60	PASS	DP=100	GT	1/1	0/0
chr3	4000	.	C	G	60	PASS	DP=100	GT	0/0	0/1
chr3	5000	.	A	T	60	PASS	DP=100	GT	0/1	1/1
"""
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False)
    temp_file.write(test_data)
    temp_file.close()
    
    return temp_file.name

def test_analysis():
    """测试VCF分析功能"""
    print("创建测试VCF文件...")
    test_vcf = create_test_vcf()
    
    try:
        print(f"测试文件: {test_vcf}")
        print(f"文件大小: {get_file_size_mb(test_vcf):.4f} MB")
        
        print("\n分析染色体大小...")
        chr_lines, chr_sizes, large_chroms = analyze_chromosome_sizes(test_vcf, 0.001)  # 使用很小的阈值
        
        print(f"发现的染色体: {list(chr_sizes.keys())}")
        for chrom, size in chr_sizes.items():
            print(f"  {chrom}: {size:.4f} MB")
        
        print(f"大染色体: {list(large_chroms.keys())}")
        
        print("\n测试完成!")
        
    finally:
        # 清理测试文件
        os.unlink(test_vcf)
        print(f"已删除测试文件: {test_vcf}")

if __name__ == "__main__":
    test_analysis()

