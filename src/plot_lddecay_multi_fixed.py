# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

import pandas as pd
import numpy as np
import os
import sys
import traceback
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 尝试导入matplotlib，如果失败则只生成数据文件
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告：未检测到matplotlib，将只生成数据文件供Excel作图使用")

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

print(f"Received {len(sys.argv)} arguments: {sys.argv}")

# 检查参数数量
if len(sys.argv) < 4:
    print("Usage: python plot_lddecay_multi.py output_prefix bin1 bin2 [breakN] [maxX] [files...]")
    print(f"Received {len(sys.argv)} arguments: {sys.argv}")
    sys.exit(1)

# 智能参数解析：根据参数数量自动判断格式
if len(sys.argv) >= 7:
    # 格式1: script_path, temp_prefix, bin1, bin2, breakN, maxX, files...
    out_prefix = sys.argv[2]
    bin1 = int(sys.argv[3])
    bin2 = int(sys.argv[4])
    breakN = int(sys.argv[5])
    maxX = int(sys.argv[6])
    input_files = sys.argv[7:]
    print(f"Format 1 detected: script_path, temp_prefix, bin1, bin2, breakN, maxX, files...")
elif len(sys.argv) >= 6:
    # 格式2: temp_prefix, bin1, bin2, breakN, maxX, files...
    out_prefix = sys.argv[1]
    bin1 = int(sys.argv[2])
    bin2 = int(sys.argv[3])
    breakN = int(sys.argv[4])
    maxX = int(sys.argv[5])
    input_files = sys.argv[6:]
    print(f"Format 2 detected: temp_prefix, bin1, bin2, breakN, maxX, files...")
elif len(sys.argv) >= 4:
    # 格式3: temp_prefix, bin1, bin2, files...
    out_prefix = sys.argv[1]
    bin1 = int(sys.argv[2])
    bin2 = int(sys.argv[3])
    breakN = 100  # 默认值
    maxX = 500    # 默认值
    input_files = sys.argv[4:]
    print(f"Format 3 detected: temp_prefix, bin1, bin2, files... (using defaults: breakN=100, maxX=500)")
else:
    # 格式4: 只有文件
    out_prefix = "output"
    bin1 = 10
    bin2 = 100
    breakN = 100
    maxX = 500
    input_files = sys.argv[1:]
    print(f"Format 4 detected: files only (using defaults)")

print(f"Parameters: bin1={bin1}, bin2={bin2}, breakN={breakN}, maxX={maxX}")
print(f"Input files: {input_files}")

# 判断单群体/多群体并设置标题
is_multi_pop = len(input_files) > 1
if is_multi_pop:
    plot_title = "LD Decay (Multi-Population)"
    print("检测到多个群体文件，生成多群体对比图")
else:
    plot_title = "LD Decay (Single Population)"
    print("检测到单个群体文件，生成单群体图")

all_bin_data = []
all_r2_values = []

# 初始化输出路径变量
output_path = None

# 只有在matplotlib可用时才创建图形
if MATPLOTLIB_AVAILABLE:
    plt.figure(figsize=(8, 8))  # 画布改为正方形

print(f"总共需要处理 {len(input_files)} 个文件")
successful_files = 0

for file in input_files:
    try:
        print(f"Processing: {file}")
        if not os.path.exists(file):
            print(f"File does not exist: {file}")
            continue
        if file.endswith('.gz'):
            df = pd.read_csv(file, sep=r'\s+', compression='gzip')
        else:
            df = pd.read_csv(file, sep=r'\s+')
        print(f"Data shape: {df.shape}")
        print(f"First 5 rows:\n{df.head()}")
        group_name = os.path.splitext(os.path.splitext(os.path.basename(file))[0])[0]
        processed_data = process_ld_data(df, bin1, bin2)
        
        # 检查处理后的数据是否为空
        if processed_data.empty:
            print(f"Warning: No data after processing for file {file}")
            continue
            
        # maxX截断
        processed_data = processed_data[processed_data['#Dist'] <= maxX * 1000]
        
        # break分段
        if breakN > 0 and len(processed_data) > breakN:
            idx = np.linspace(0, len(processed_data)-1, breakN, dtype=int)
            processed_data = processed_data.iloc[idx]
        
        # 收集用于Y轴范围的数据并按单/多群体分别绘制
        print(f"Adding r2 values: {len(processed_data['Mean_r^2'].tolist())} values")
        all_r2_values.extend(processed_data['Mean_r^2'].tolist())
        if MATPLOTLIB_AVAILABLE:
            print("Plotting data...")
            if is_multi_pop:
                plt.plot(processed_data['#Dist']/1000, processed_data['Mean_r^2'], linewidth=1, label=group_name)
            else:
                plt.plot(processed_data['#Dist']/1000, processed_data['Mean_r^2'], linewidth=1)
        
        # 保存每个群体的分箱数据
        print("Saving individual group data...")
        processed_data_out = processed_data[['#Dist', 'Mean_r^2']].copy()
        processed_data_out.columns = ['Distance(bp)', 'Mean_r^2']
        processed_data_out.to_csv(f"{out_prefix}_{group_name}_bin.txt", sep='\t', index=False)
        all_bin_data.append((group_name, processed_data_out))
        successful_files += 1
        print(f"成功处理文件: {file}")
    except Exception as e:
        print(f"Exception occurred while processing file {file}: {e}")
        traceback.print_exc()

print(f"成功处理了 {successful_files} 个文件")

# 只有在matplotlib可用时才绘制图形
if MATPLOTLIB_AVAILABLE:
    plt.xlabel('Distance (kb)')
    plt.ylabel('r²')
    plt.title(plot_title)
    plt.grid(True, linestyle='--', alpha=0.7)
    if is_multi_pop:
        plt.legend()
    plt.tight_layout()
    plt.xlim(0, maxX)
    if all_r2_values:
        try:
            ymax = min(1.0, max(all_r2_values) * 1.1)
            plt.ylim(0, ymax)
        except ValueError:
            pass

    # 根据单群体/多群体设置不同的输出文件名
    if os.path.isabs(out_prefix):
        if is_multi_pop:
            output_path = out_prefix + "_multi_LD_decay_plot.png"
        else:
            output_path = out_prefix + "_single_LD_decay_plot.png"
    else:
        if is_multi_pop:
            output_path = os.path.join(os.getcwd(), out_prefix + "_multi_LD_decay_plot.png")
        else:
            output_path = os.path.join(os.getcwd(), out_prefix + "_single_LD_decay_plot.png")
    plt.savefig(output_path, dpi=300)
    if is_multi_pop:
        print(f"Multi-population plot saved as: {output_path}")
    else:
        print(f"Single population plot saved as: {output_path}")
else:
    # 即使没有matplotlib，也设置输出路径以便C++代码能找到数据文件
    if os.path.isabs(out_prefix):
        if is_multi_pop:
            output_path = out_prefix + "_multi_LD_decay_plot.png"
        else:
            output_path = out_prefix + "_single_LD_decay_plot.png"
    else:
        if is_multi_pop:
            output_path = os.path.join(os.getcwd(), out_prefix + "_multi_LD_decay_plot.png")
        else:
            output_path = os.path.join(os.getcwd(), out_prefix + "_single_LD_decay_plot.png")
    print("由于未检测到matplotlib，跳过图片生成，仅生成数据文件供Excel作图使用")
    print(f"预期图片路径（未生成）: {output_path}")

# 生成数据文件（无论是否有数据）
if is_multi_pop:
    bin_filename = f"{out_prefix}_multi_bin.txt"
else:
    bin_filename = f"{out_prefix}_single_bin.txt"

if all_bin_data and len(all_bin_data) > 0:
    # 有数据时，生成正常的数据文件
    with open(bin_filename, "w", encoding="utf-8") as f:
        header = "Distance(bp)\t" + "\t".join([g for g, _ in all_bin_data]) + "\n"
        f.write(header)
        # 按距离合并
        all_dist = all_bin_data[0][1]['Distance(bp)']
        for i in range(len(all_dist)):
            line = [str(all_bin_data[0][1]['Distance(bp)'][i])]
            for _, data in all_bin_data:
                line.append(str(data['Mean_r^2'][i]))
            f.write("\t".join(line) + "\n")
    print(f"Bin-processed summary file saved as: {bin_filename}")
else:
    # 没有数据时，生成空的占位文件
    print("警告：没有有效数据，生成空的占位文件")
    with open(bin_filename, "w", encoding="utf-8") as f:
        f.write("Distance(bp)\tMean_r^2\n")
        f.write("0\t0\n")
    print(f"生成空的占位文件: {bin_filename}")

print("out_prefix:", out_prefix)
print("os.getcwd():", os.getcwd())
if output_path:
    print("output_path:", output_path)
else:
    print("output_path: 未生成图片（matplotlib不可用）")
