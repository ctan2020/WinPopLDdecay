# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

import pandas as pd
import numpy as np
import os
import sys

# 尝试导入matplotlib，如果失败则只生成数据文件
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告：未检测到matplotlib，将只生成数据文件供Excel作图使用")

# 自动判断数据文件名和压缩格式
# 支持命令行参数，否则默认当前目录下的LDdecay.stat.gz或LDdecay.stat
if len(sys.argv) > 1:
    data_file = sys.argv[1]
else:
    if os.path.exists('LDdecay.stat.gz'):
        data_file = 'LDdecay.stat.gz'
    elif os.path.exists('LDdecay.stat'):
        data_file = 'LDdecay.stat'
    else:
        print('未找到LDdecay.stat.gz或LDdecay.stat')
        sys.exit(1)

# 判断是否为.gz文件
if data_file.endswith('.gz'):
    df = pd.read_csv(data_file, delim_whitespace=True, compression='gzip')
else:
    df = pd.read_csv(data_file, delim_whitespace=True)

print("数据形状:", df.shape)
print("数据列名:", list(df.columns))
print("前5行数据:")
print(df.head())

output_dir = os.path.dirname(data_file)  # 输出图片到数据文件所在目录

def process_ld_data(df, bin_size=100):
    # 确保 #Dist 列是数值类型
    df['#Dist'] = pd.to_numeric(df['#Dist'])
    
    # 创建分箱
    df['bin'] = pd.cut(df['#Dist'], 
                       bins=np.arange(0, df['#Dist'].max() + bin_size, bin_size))
    
    # 对每个分箱计算均值
    grouped = df.groupby('bin', observed=True).agg({
        'Mean_r^2': 'mean',
        '#Dist': 'mean'  # 使用距离的平均值作为 x 轴
    }).reset_index()
    
    return grouped

# 处理数据
processed_data = process_ld_data(df)

# 保存数据文件供Excel作图
prefix = os.path.splitext(os.path.splitext(os.path.basename(data_file))[0])[0]
data_output_file = os.path.join(os.path.dirname(data_file), f"{prefix}_LD_decay_data.txt")
processed_data[['#Dist', 'Mean_r^2']].to_csv(data_output_file, sep='\t', index=False)
print(f"数据文件已保存为: {data_output_file}")

# 只有在matplotlib可用时才创建图形
if MATPLOTLIB_AVAILABLE:
    # 创建正方形图形
    plt.figure(figsize=(8, 8))

    # 绘制 r² 曲线
    plt.plot(processed_data['#Dist']/1000, processed_data['Mean_r^2'], 
             color='blue', linewidth=1, label='r²')

    # 设置图形属性
    plt.xlabel('Distance (kb)')
    plt.ylabel('r²')
    plt.title('LD Decay (Single Population)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # 自动用前缀命名图片（支持 .gz 和 .stat）
    output_file = os.path.join(os.path.dirname(data_file), f"{prefix}_LD_decay_plot.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图片已保存为: {output_file}")
else:
    print("由于未检测到matplotlib，跳过图片生成，仅生成数据文件供Excel作图使用")