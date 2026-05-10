# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本
"""

import pandas as pd
import numpy as np
import sys

def process_ld_data(df, bin1=10, bin2=100):
    print(f"Data columns: {list(df.columns)}")
    
    # 确保必要的列存在
    if '#Dist' not in df.columns:
        print("Error: '#Dist' column not found in data")
        return pd.DataFrame()
    if 'Mean_r^2' not in df.columns:
        print("Error: 'Mean_r^2' column not found in data")
        return pd.DataFrame()
    
    df['#Dist'] = pd.to_numeric(df['#Dist'], errors='coerce')
    df = df.dropna(subset=['#Dist', 'Mean_r^2'])
    
    if len(df) == 0:
        print("Error: No valid data after cleaning")
        return pd.DataFrame()
    
    bins = np.arange(bin1, df['#Dist'].max() + bin2, bin2)
    df['bin'] = pd.cut(df['#Dist'], bins=bins)
    grouped = df.groupby('bin', observed=True).agg({
        'Mean_r^2': 'mean',
        '#Dist': 'mean'
    }).reset_index()
    return grouped

# 测试
file = "C:/Users/19940/PopLDdecayGUI/build/Desktop_Qt_6_9_0_MinGW_64_bit-Debug/src/LDdecay.stat.gz"
print(f"Processing: {file}")

if file.endswith('.gz'):
    df = pd.read_csv(file, sep=r'\s+', compression='gzip')
else:
    df = pd.read_csv(file, sep=r'\s+')

print(f"Data shape: {df.shape}")
print(f"First 5 rows:\n{df.head()}")

processed_data = process_ld_data(df, 100, 500)
print(f"Processed data shape: {processed_data.shape}")

if not processed_data.empty:
    print("maxX截断前:", processed_data.shape)
    processed_data = processed_data[processed_data['#Dist'] <= 500 * 1000]
    print("maxX截断后:", processed_data.shape)
    
    print("break分段前:", processed_data.shape)
    if 100 > 0 and len(processed_data) > 100:
        idx = np.linspace(0, len(processed_data)-1, 100, dtype=int)
        print("idx:", idx[:10])
        processed_data = processed_data.iloc[idx]
    print("break分段后:", processed_data.shape)
    
    print("Success!")
else:
    print("Failed!")