# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import traceback
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def process_ld_data(df, bin1=10, bin2=100):
    df['#Dist'] = pd.to_numeric(df['#Dist'])
    bins = np.arange(bin1, df['#Dist'].max() + bin2, bin2)
    df['bin'] = pd.cut(df['#Dist'], bins=bins)
    grouped = df.groupby('bin', observed=True).agg({
        'Mean_r^2': 'mean',
        '#Dist': 'mean'
    }).reset_index()
    return grouped

if len(sys.argv) < 5:
    print("Usage: python plot_lddecay_multi.py output_prefix bin1 bin2 break maxX pop1.stat[.gz] pop2.stat[.gz] ...")
    sys.exit(1)

out_prefix = sys.argv[1]
try:
    bin1 = int(sys.argv[2])
    bin2 = int(sys.argv[3])
    breakN = int(sys.argv[4])
    maxX = int(sys.argv[5])
    input_files = sys.argv[6:]
except Exception:
    bin1 = 10
    bin2 = 100
    breakN = 100
    maxX = 500
    input_files = sys.argv[2:]

plt.figure(figsize=(10, 6))
all_bin_data = []

for file in input_files:
    try:
        print(f"Processing: {file}")
        if not os.path.exists(file):
            print(f"File does not exist: {file}")
            continue
        if file.endswith('.gz'):
            df = pd.read_csv(file, delim_whitespace=True, compression='gzip')
        else:
            df = pd.read_csv(file, delim_whitespace=True)
        print(f"Data shape: {df.shape}")
        print(f"First 5 rows:\n{df.head()}")
        group_name = os.path.splitext(os.path.splitext(os.path.basename(file))[0])[0]
        processed_data = process_ld_data(df, bin1, bin2)
        # maxX截断
        processed_data = processed_data[processed_data['#Dist'] <= maxX * 1000]
        # break分段
        if breakN > 0 and len(processed_data) > breakN:
            idx = np.linspace(0, len(processed_data)-1, breakN, dtype=int)
            processed_data = processed_data.iloc[idx]
        plt.plot(processed_data['#Dist']/1000, processed_data['Mean_r^2'], linewidth=1, label=group_name)
        # 保存每个群体的分箱数据
        processed_data_out = processed_data[['#Dist', 'Mean_r^2']].copy()
        processed_data_out.columns = ['Distance(bp)', 'Mean_r^2']
        processed_data_out.to_csv(f"{out_prefix}_{group_name}_bin.txt", sep='\t', index=False)
        all_bin_data.append((group_name, processed_data_out))
    except Exception as e:
        print(f"Exception occurred while processing file {file}: {e}")
        traceback.print_exc()

plt.xlabel('Distance (kb)')
plt.ylabel('r²')
plt.title('LD Decay (Multi-Pop)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()
plt.tight_layout()
plt.xlim(0, maxX)

# 新增：如果前缀是绝对路径，则直接用该路径保存图片，否则保存到当前工作目录
if os.path.isabs(out_prefix):
    output_path = out_prefix + "_multi_LD_decay_plot.png"
else:
    output_path = os.path.join(os.getcwd(), out_prefix + "_multi_LD_decay_plot.png")
plt.savefig(output_path, dpi=300)
print(f"Multi-population plot saved as: {output_path}")

# 合并所有群体的分箱均值，保存一个总表
if all_bin_data:
    with open(f"{out_prefix}_bin.txt", "w", encoding="utf-8") as f:
        header = "Distance(bp)\t" + "\t".join([g for g, _ in all_bin_data]) + "\n"
        f.write(header)
        # 按距离合并
        all_dist = all_bin_data[0][1]['Distance(bp)']
        for i in range(len(all_dist)):
            line = [str(all_bin_data[0][1]['Distance(bp)'][i])]
            for _, data in all_bin_data:
                line.append(str(data['Mean_r^2'][i]))
            f.write("\t".join(line) + "\n")
    print(f"Bin-processed summary file saved as: {out_prefix}_bin.txt")

print("out_prefix:", out_prefix)
print("os.getcwd():", os.getcwd())
print("output_path:", output_path)
