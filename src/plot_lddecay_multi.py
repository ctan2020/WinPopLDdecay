# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

import pandas as pd
import numpy as np
import os
import sys
import traceback
import io
import gzip
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

LANG = 'zh'
def tr(zh: str, en: str) -> str:
    return en if LANG == 'en' else zh

# 尝试导入matplotlib，如果失败则只生成数据文件
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print(tr("警告：未检测到matplotlib，将只生成数据文件供Excel作图使用", "Warning: matplotlib not detected. Only data files will be generated for Excel plotting."))

def _select_columns(df: pd.DataFrame):
    # 自动选择距离和LD列，兼容不同命名
    cols_lower = {c.lower(): c for c in df.columns}
    # 距离列候选
    dist_candidates = ['#dist', 'dist', 'distance', 'distance(bp)', 'kb', 'bp', 'posdist', 'd']
    # r2列候选
    r2_candidates = ['mean_r^2', 'mean_r2', 'r2', 'r^2', 'mean_r', 'ld', 'mean_r-squared']
    dist_col = None
    r2_col = None
    for key in dist_candidates:
        if key in cols_lower:
            dist_col = cols_lower[key]
            break
    for key in r2_candidates:
        if key in cols_lower:
            r2_col = cols_lower[key]
            break
    return dist_col, r2_col

def _infer_column_positions(df_sample: pd.DataFrame) -> tuple:
    """
    推断距离和r²列的位置（当文件没有表头时）
    返回: (dist_col_idx, r2_col_idx) 或 (None, None)
    """
    # 尝试将每列转换为数值，找出哪些列是数值列
    numeric_cols = []
    for col_idx, col_name in enumerate(df_sample.columns):
        try:
            col_data = pd.to_numeric(df_sample[col_name], errors='coerce')
            valid_data = col_data.dropna()
            if len(valid_data) > len(df_sample) * 0.5:  # 至少50%是有效数值
                numeric_cols.append((col_idx, col_name, valid_data))
        except:
            pass
    
    if len(numeric_cols) < 2:
        return None, None
    
    # 找出距离列：通常数值较大（>10），且可能有递增趋势
    # 找出r²列：通常在0-1之间，或较小的正数
    dist_candidates = []
    r2_candidates = []
    
    for col_idx, col_name, valid_data in numeric_cols:
        data_min = valid_data.min()
        data_max = valid_data.max()
        data_mean = valid_data.mean()
        data_std = valid_data.std()
        
        # r²列：通常在0-1之间，或较小的正数（<10），且标准差较小
        # 优先选择0-1之间的值
        if 0 <= data_min and data_max <= 1.5:
            # 典型的r²值范围
            r2_candidates.append((col_idx, col_name, abs(data_mean - 0.5), data_mean))
        elif 0 <= data_min and data_max <= 10 and data_mean < 5:
            # 可能是r²但范围稍大
            r2_candidates.append((col_idx, col_name, abs(data_mean - 0.5) + 1, data_mean))
        
        # 距离列：通常数值较大（>10），且可能有较大的最大值和标准差
        if data_min >= 0 and data_max > 10:
            # 距离值通常变化范围大
            score = data_max + data_std  # 综合考虑最大值和标准差
            dist_candidates.append((col_idx, col_name, score, data_max))
    
    # 选择最可能的列
    dist_col_idx = None
    r2_col_idx = None
    
    if dist_candidates:
        # 选择score最大的作为距离列
        dist_col_idx = max(dist_candidates, key=lambda x: x[2])[0]
        print(f"Distance column candidate: column {dist_col_idx}, max={max(dist_candidates, key=lambda x: x[2])[3]:.2f}")
    
    if r2_candidates:
        # 选择均值最接近0.5的作为r²列（r²通常在0-1之间）
        r2_col_idx = min(r2_candidates, key=lambda x: x[2])[0]
        print(f"r² column candidate: column {r2_col_idx}, mean={min(r2_candidates, key=lambda x: x[2])[3]:.4f}")
    
    return dist_col_idx, r2_col_idx

def _read_stat_file(file_path: str, chunk_size: int = 100000) -> pd.DataFrame:
    """
    读取.stat或.stat.gz文件，支持大文件分块读取
    如果文件很大（>100MB），使用分块读取避免内存溢出
    自动检测是否有表头，如果没有则推断列位置
    """
    if not os.path.exists(file_path):
        print(f"File does not exist: {file_path}")
        return pd.DataFrame()
    
    try:
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"Reading file: {file_path} (size: {file_size_mb:.2f} MB)")
        
        compression = 'gzip' if file_path.endswith('.gz') else None
        is_large_file = file_size > 100 * 1024 * 1024  # 100MB阈值
        
        # 先读取前几行检测文件格式
        sample_size = 1000 if is_large_file else 100
        
        # 先尝试有表头的方式读取
        # 不能使用 comment='#'：会把 '#Dist' 表头误当注释丢弃，导致列识别错位
        sample_df_with_header = pd.read_csv(file_path, sep=r'\s+', compression=compression, 
                                           engine='python', nrows=sample_size)
        
        if sample_df_with_header.empty:
            sample_df_with_header = pd.read_csv(file_path, sep=r'\s+', compression=compression, 
                                               engine='python', nrows=sample_size)
        
        # 检查是否有表头（通过列名识别）
        dist_col, r2_col = _select_columns(sample_df_with_header)
        has_header = (dist_col is not None and r2_col is not None)
        
        if not has_header:
            # 尝试标准列名
            if '#Dist' in sample_df_with_header.columns and 'Mean_r^2' in sample_df_with_header.columns:
                dist_col = '#Dist'
                r2_col = 'Mean_r^2'
                has_header = True
        
        # 如果没有找到表头，尝试无表头方式读取来推断列位置
        if not has_header:
            # 文件没有表头，需要推断列位置
            print("No header detected, reading without header to infer column positions...")
            sample_df_no_header = pd.read_csv(file_path, sep=r'\s+', compression=compression, 
                                            engine='python', nrows=sample_size, 
                                            header=None)
            if sample_df_no_header.empty:
                sample_df_no_header = pd.read_csv(file_path, sep=r'\s+', compression=compression, 
                                                 engine='python', nrows=sample_size, header=None)
            
            dist_col_idx, r2_col_idx = _infer_column_positions(sample_df_no_header)
            
            if dist_col_idx is not None and r2_col_idx is not None:
                print(f"Inferred column positions: dist at column {dist_col_idx}, r² at column {r2_col_idx}")
                # 显示样本数据以便确认
                print(f"Sample dist values: {sample_df_no_header.iloc[:5, dist_col_idx].tolist()}")
                print(f"Sample r² values: {sample_df_no_header.iloc[:5, r2_col_idx].tolist()}")
                dist_col = '#Dist'
                r2_col = 'Mean_r^2'
                use_cols = [dist_col_idx, r2_col_idx]
            else:
                print(f"Error: Cannot infer column positions.")
                print(f"Sample data (first 5 rows, assuming no header):")
                print(sample_df_no_header.head())
                print(f"Available numeric columns: {len([c for c in sample_df_no_header.columns if pd.api.types.is_numeric_dtype(sample_df_no_header[c])])}")
                return pd.DataFrame()
        else:
            print(f"Header detected. Columns: dist={dist_col}, r²={r2_col}")
            use_cols = None
        
        if is_large_file:
            print(f"Large file detected ({file_size_mb:.2f} MB), using chunked reading...")
            
            # 分块读取大文件
            chunks = []
            total_rows = 0
            
            for chunk in pd.read_csv(file_path, sep=r'\s+', compression=compression, 
                                    engine='python', chunksize=chunk_size, 
                                    header=0 if has_header else None):
                total_rows += len(chunk)
                
                # 只保留需要的列，减少内存
                if has_header:
                    if dist_col in chunk.columns and r2_col in chunk.columns:
                        chunk = chunk[[dist_col, r2_col]].copy()
                    else:
                        print(f"Warning: Expected columns not found in chunk: {list(chunk.columns)}")
                        continue
                else:
                    # 使用推断的列位置（直接通过索引选择列）
                    if len(chunk.columns) > max(use_cols):
                        chunk = chunk.iloc[:, use_cols].copy()
                        chunk.columns = ['#Dist', 'Mean_r^2']
                    else:
                        print(f"Warning: Chunk has fewer columns ({len(chunk.columns)}) than expected (need at least {max(use_cols)+1})")
                        continue
                
                # 转换为数值类型并清理
                chunk['#Dist'] = pd.to_numeric(chunk['#Dist'], errors='coerce')
                chunk['Mean_r^2'] = pd.to_numeric(chunk['Mean_r^2'], errors='coerce')
                chunk = chunk.dropna(subset=['#Dist', 'Mean_r^2'])
                if len(chunk) > 0:
                    chunks.append(chunk)
                
                if total_rows % (chunk_size * 10) == 0:
                    print(f"  Processed {total_rows:,} rows, {len(chunks)} valid chunks...")
            
            if chunks:
                print(f"Concatenating {len(chunks)} chunks (total {total_rows:,} rows)...")
                df = pd.concat(chunks, ignore_index=True)
                print(f"Final dataframe shape: {df.shape}, columns: {list(df.columns)}")
                return df
            else:
                print("Warning: No valid data chunks found")
                return pd.DataFrame()
        else:
            # 小文件直接读取
            if has_header:
                df = pd.read_csv(file_path, sep=r'\s+', compression=compression, engine='python')
            else:
                # 没有表头，使用推断的列位置
                df = pd.read_csv(file_path, sep=r'\s+', compression=compression, engine='python', 
                                header=None)
                # 只保留需要的列
                df = df.iloc[:, use_cols].copy()
                df.columns = ['#Dist', 'Mean_r^2']
            
            print(f"Read {len(df):,} rows from file")
            return df
    except MemoryError as e:
        print(f"Memory error reading file: {e}")
        print("Try reducing chunk_size or using a machine with more RAM")
        return pd.DataFrame()
    except Exception as e:
        print(f"Failed to read file with pandas: {e}")
        traceback.print_exc()
        # 尝试粗略探测：打印文件大小和前几字节，帮助定位问题
        try:
            size = os.path.getsize(file_path)
            print(f"Stat file size (bytes): {size}")
            if file_path.endswith('.gz'):
                with gzip.open(file_path, 'rb') as f:
                    head = f.read(200)
            else:
                with open(file_path, 'rb') as f:
                    head = f.read(200)
            print(f"Head bytes: {head[:100]}")
        except Exception as e2:
            print(f"Failed to probe file bytes: {e2}")
        return pd.DataFrame()

def process_ld_data(df, bin1=10, bin2=100, breakN=100):
    print(f"Data columns: {list(df.columns)}")
    
    # 自动识别列名
    dist_col, r2_col = _select_columns(df)
    if dist_col is None or r2_col is None:
        # 尝试兼容常见PopLDdecay列名
        if '#Dist' in df.columns:
            dist_col = '#Dist'
        if 'Mean_r^2' in df.columns:
            r2_col = 'Mean_r^2'
    if dist_col is None or r2_col is None:
        print(f"Error: cannot find distance/LD columns. Available columns: {list(df.columns)}")
        return pd.DataFrame()
    
    # 清洗与重命名方便后续统一处理
    df[dist_col] = pd.to_numeric(df[dist_col], errors='coerce')
    df[r2_col] = pd.to_numeric(df[r2_col], errors='coerce')
    df = df.dropna(subset=[dist_col, r2_col])
    
    if len(df) == 0:
        print("Error: No valid data after cleaning")
        return pd.DataFrame()
    
    # 优先保留 x=0 处峰值（若存在多个0距离点，取最大值避免被均值稀释）
    zero_rows = df[df[dist_col] == 0].copy()
    zero_point = None
    if not zero_rows.empty:
        zero_point = pd.DataFrame({
            '#Dist': [0.0],
            'Mean_r^2': [zero_rows[r2_col].max()]
        })

    # 其余距离按 breakN 分段分箱：
    # Dist < breakN 使用 bin1；Dist >= breakN 使用 bin2
    df_nonzero = df[df[dist_col] > 0].copy()
    if df_nonzero.empty:
        if zero_point is not None:
            return zero_point
        return pd.DataFrame(columns=['#Dist', 'Mean_r^2'])

    break_threshold = max(0, breakN)
    short_df = df_nonzero[df_nonzero[dist_col] < break_threshold].copy()
    long_df = df_nonzero[df_nonzero[dist_col] >= break_threshold].copy()
    grouped_parts = []

    if not short_df.empty:
        short_step = max(1, bin1)
        short_end = max(break_threshold, short_df[dist_col].max()) + short_step
        short_bins = np.arange(0, short_end, short_step)
        if len(short_bins) < 2:
            short_bins = np.array([0, short_end])
        short_df['bin'] = pd.cut(short_df[dist_col], bins=short_bins, include_lowest=True, right=False)
        short_grouped = short_df.groupby('bin', observed=True).agg({
            r2_col: 'mean',
            dist_col: 'mean'
        }).reset_index(drop=True)
        short_grouped.columns = ['Mean_r^2', '#Dist']
        grouped_parts.append(short_grouped)

    if not long_df.empty:
        long_step = max(1, bin2)
        long_start = break_threshold
        long_end = long_df[dist_col].max() + long_step
        long_bins = np.arange(long_start, long_end, long_step)
        if len(long_bins) < 2:
            long_bins = np.array([long_start, long_end])
        long_df['bin'] = pd.cut(long_df[dist_col], bins=long_bins, include_lowest=True, right=False)
        long_grouped = long_df.groupby('bin', observed=True).agg({
            r2_col: 'mean',
            dist_col: 'mean'
        }).reset_index(drop=True)
        long_grouped.columns = ['Mean_r^2', '#Dist']
        grouped_parts.append(long_grouped)

    if grouped_parts:
        grouped = pd.concat(grouped_parts, ignore_index=True)
    else:
        grouped = pd.DataFrame(columns=['#Dist', 'Mean_r^2'])

    if zero_point is not None:
        grouped = pd.concat([zero_point, grouped], ignore_index=True)

    grouped = grouped.sort_values('#Dist').reset_index(drop=True)
    return grouped

argv = sys.argv[:]
if '--lang' in argv:
    i = argv.index('--lang')
    if i + 1 < len(argv):
        LANG = argv[i + 1].lower()
    del argv[i:i+2]

print(f"Received {len(argv)} arguments: {argv}")

# 检查参数数量
if len(argv) < 4:
    print("Usage: python plot_lddecay_multi.py output_prefix bin1 bin2 [breakN] [maxX] [files...]")
    print(f"Received {len(argv)} arguments: {argv}")
    sys.exit(1)

# 智能参数解析：根据参数数量自动判断格式
if len(argv) >= 7:
    # 调用格式：script_path, out_prefix, bin1, bin2, breakN, maxX, files...
    out_prefix = argv[1]
    bin1 = int(argv[2])
    bin2 = int(argv[3])
    breakN = int(argv[4])
    maxX = int(argv[5])
    input_files = argv[6:]
    print("Format detected: out_prefix, bin1, bin2, breakN, maxX, files...")
elif len(argv) >= 4:
    # 简化格式：out_prefix, bin1, bin2, files...（使用默认 breakN/maxX）
    out_prefix = argv[1]
    bin1 = int(argv[2])
    bin2 = int(argv[3])
    breakN = 100
    maxX = 500
    input_files = argv[4:]
    print("Format detected: out_prefix, bin1, bin2, files... (using defaults)")

print(f"Parameters: bin1={bin1}, bin2={bin2}, breakN={breakN}, maxX={maxX}")
print(f"Input files: {input_files}")

# 判断单群体/多群体并设置标题
is_multi_pop = len(input_files) > 1
if is_multi_pop:
    plot_title = "LD Decay (Multi-Population)"
    print(tr("检测到多个群体文件，生成多群体对比图", "Detected multiple population files, generating comparison plot."))
else:
    plot_title = "LD Decay (Single Population)"
    print(tr("检测到单个群体文件，生成单-population图", "Detected single population file, generating single-population plot.").replace("single-population图", "single-population plot."))

all_bin_data = []
all_r2_values = []

# 初始化输出路径变量
output_path = None

# 只有在matplotlib可用时才创建图形
if MATPLOTLIB_AVAILABLE:
    plt.figure(figsize=(8, 8))  # 画布改为正方形

print(tr(f"总共需要处理 {len(input_files)} 个文件", f"Total files to process: {len(input_files)}"))
successful_files = 0

for file in input_files:
    try:
        print(f"Processing: {file}")
        if not os.path.exists(file):
            print(f"File does not exist: {file}")
            continue
        df = _read_stat_file(file)
        if df.empty:
            print(f"Warning: empty or unreadable data file: {file}")
            continue
        print(f"Data shape: {df.shape}")
        print(f"First 5 rows:\n{df.head()}")
        group_name = os.path.splitext(os.path.splitext(os.path.basename(file))[0])[0]
        processed_data = process_ld_data(df, bin1, bin2, breakN)
        
        # 检查处理后的数据是否为空
        if processed_data.empty:
            print(f"Warning: No data after processing for file {file}")
            continue
            
        # maxX截断
        processed_data = processed_data[processed_data['#Dist'] <= maxX * 1000]
        
        # 检查截断后的数据是否为空
        if len(processed_data) == 0:
            print(f"Warning: No data points after maxX truncation (maxX={maxX}kb) for file {file}")
            continue
        
        # 收集用于Y轴范围的数据并按单/多群体分别绘制
        r2_list = processed_data['Mean_r^2'].tolist()
        dist_list = (processed_data['#Dist']/1000).tolist()
        print(f"Plotting {len(r2_list)} data points (dist range: {min(dist_list):.2f}-{max(dist_list):.2f} kb, r2 range: {min(r2_list):.4f}-{max(r2_list):.4f})")
        all_r2_values.extend(r2_list)
        
        if MATPLOTLIB_AVAILABLE:
            print(f"Drawing plot line for {group_name}...")
            try:
                if is_multi_pop:
                    plt.plot(dist_list, r2_list, linewidth=2.1, label=group_name, marker='o', markersize=2)
                else:
                    plt.plot(dist_list, r2_list, linewidth=2.1, marker='o', markersize=2)
                print(f"Successfully plotted {len(r2_list)} points for {group_name}")
            except Exception as plot_err:
                print(f"Error plotting data: {plot_err}")
                traceback.print_exc()
        
        # 保存每个群体的分箱数据
        print("Saving individual group data...")
        processed_data_out = processed_data[['#Dist', 'Mean_r^2']].copy().reset_index(drop=True)
        processed_data_out.columns = ['Distance(bp)', 'Mean_r^2']
        processed_data_out.to_csv(f"{out_prefix}_{group_name}_bin.txt", sep='\t', index=False)
        all_bin_data.append((group_name, processed_data_out))
        successful_files += 1
        print(tr(f"成功处理文件: {file}", f"Processed file: {file}"))
    except Exception as e:
        print(f"Exception occurred while processing file {file}: {e}")
        traceback.print_exc()

print(tr(f"成功处理了 {successful_files} 个文件", f"Successfully processed {successful_files} files"))
print(tr(f"总共收集了 {len(all_r2_values)} 个 r² 数据点", f"Collected {len(all_r2_values)} r² points in total"))

# 检查是否有数据可绘制
if successful_files == 0:
    print(tr("ERROR: 没有成功处理任何文件，无法生成图片！", "ERROR: No files were processed successfully; cannot generate plot."))
    print(tr("请检查：", "Please check:"))
    print(tr("  1. 输入文件是否存在且可读", "  1. Whether input files exist and are readable"))
    print(tr("  2. 文件格式是否正确（应包含 #Dist 和 Mean_r^2 列）", "  2. Whether file format is correct (must contain #Dist and Mean_r^2 columns)"))
    print(tr("  3. 数据是否在有效范围内", "  3. Whether data values are in a valid range"))
    sys.exit(1)

if len(all_r2_values) == 0:
    print(tr("ERROR: 处理后的数据为空，无法生成图片！", "ERROR: Processed data is empty; cannot generate plot."))
    print(tr("可能原因：", "Possible reasons:"))
    print(tr("  1. 所有数据点都被 maxX 过滤掉了", "  1. All data points were filtered by maxX"))
    print(tr("  2. 数据清洗后没有有效值", "  2. No valid values remain after data cleaning"))
    sys.exit(1)

# 只有在matplotlib可用时才绘制图形
if MATPLOTLIB_AVAILABLE:
    # 检查当前图形是否有数据
    axes = plt.gca()
    if len(axes.lines) == 0:
        print(tr("WARNING: 图形中没有绘制任何线条！", "WARNING: No lines were plotted in the figure."))
        print(f"all_r2_values length: {len(all_r2_values)}")
        print(f"all_bin_data length: {len(all_bin_data)}")
    
    plt.xlabel('Distance (kb)', fontsize=12)
    plt.ylabel('r²', fontsize=12)
    plt.title(plot_title, fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    if is_multi_pop:
        plt.legend(loc='best', fontsize=10)
    plt.tight_layout()
    y_axis_offset = -10
    x_axis_offset = -0.01
    # plt.xlim(y_axis_offset, maxX)
    x_min = -maxX / 10
    plt.xlim(x_min, maxX * 1.1)
    maxY = max(all_r2_values)
    y_min = -maxY / 10
    # y_max = maxY
    plt.ylim(y_min, maxY)
    plt.grid(False)
    # axes.spines['left'].set_position(('data', y_axis_offset))
    # axes.spines['bottom'].set_position(('data', x_axis_offset))
    axes.spines['bottom'].set_visible(True)
    axes.spines['left'].set_visible(True)
    axes.spines['top'].set_visible(False)
    axes.spines['right'].set_visible(False)

    if all_r2_values:
        try:
            # ymax = max(all_r2_values) * 1.1
            ymax = maxY * 1.1
            ymin = y_min
            # ymin = min(ymin, x_axis_offset)
            if ymax <= ymin:
                ymax = ymin + 0.1
            plt.ylim(ymin, ymax)
            print(f"Y-axis range set to: [{ymin:.4f}, {ymax:.4f}]")
        except ValueError as ve:
            print(f"Warning: Could not set Y-axis limits: {ve}")
    else:
        print("WARNING: No r² values available for Y-axis")
        plt.ylim(0, 1.0)

    # 根据单群体/多群体设置不同的输出文件名前缀
    if os.path.isabs(out_prefix):
        if is_multi_pop:
            output_base = out_prefix + "_multi_LD_decay_plot"
        else:
            output_base = out_prefix + "_single_LD_decay_plot"
    else:
        if is_multi_pop:
            output_base = os.path.join(os.getcwd(), out_prefix + "_multi_LD_decay_plot")
        else:
            output_base = os.path.join(os.getcwd(), out_prefix + "_single_LD_decay_plot")
    output_path = output_base + ".png"
    # 保存前再次检查图形是否有内容
    axes = plt.gca()
    if len(axes.lines) == 0:
        print(tr("ERROR: 图形中没有数据线，图片将为空！", "ERROR: No data lines in the figure; output image will be empty."))
        print(tr("请检查数据文件和参数设置", "Please check data files and parameter settings."))
    else:
        print(tr(f"图形包含 {len(axes.lines)} 条数据线，准备保存...", f"Figure contains {len(axes.lines)} line(s); preparing to save..."))
    
    try:
        png_path = output_base + ".png"
        pdf_path = output_base + ".pdf"
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        plt.savefig(pdf_path, bbox_inches='tight')
        output_path = png_path  # 保持与 C++ 侧兼容（继续以 png 路径为主）
        file_size = os.path.getsize(png_path) if os.path.exists(png_path) else 0
        if file_size < 1000:  # 小于1KB可能为空图
            print(tr(f"WARNING: 保存的PNG文件很小 ({file_size} bytes)，可能为空图！", f"WARNING: saved PNG is very small ({file_size} bytes), may be empty."))
        else:
            print(tr(f"PNG已保存，文件大小: {file_size / 1024:.2f} KB", f"PNG saved, file size: {file_size / 1024:.2f} KB"))
        pdf_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        if pdf_size > 0:
            print(tr(f"PDF已保存，文件大小: {pdf_size / 1024:.2f} KB", f"PDF saved, file size: {pdf_size / 1024:.2f} KB"))
        else:
            print(tr("WARNING: PDF文件未正确生成或大小为0", "WARNING: PDF was not generated correctly or size is 0."))
        
        if is_multi_pop:
            print(f"Multi-population plot saved as: {png_path}")
            print(f"Multi-population plot saved as: {pdf_path}")
        else:
            print(f"Single population plot saved as: {png_path}")
            print(f"Single population plot saved as: {pdf_path}")
    except Exception as save_err:
        print(f"ERROR: 保存图片失败: {save_err}")
        traceback.print_exc()
else:
    # 即使没有matplotlib，也设置输出路径以便C++代码能找到数据文件
    if os.path.isabs(out_prefix):
        if is_multi_pop:
            output_base = out_prefix + "_multi_LD_decay_plot"
        else:
            output_base = out_prefix + "_single_LD_decay_plot"
    else:
        if is_multi_pop:
            output_base = os.path.join(os.getcwd(), out_prefix + "_multi_LD_decay_plot")
        else:
            output_base = os.path.join(os.getcwd(), out_prefix + "_single_LD_decay_plot")
    output_path = output_base + ".png"
    print(tr("由于未检测到matplotlib，跳过图片生成，仅生成数据文件供Excel作图使用", "matplotlib not detected, skipped image generation and only exported data files."))
    print(tr(f"预期图片路径（未生成）: {output_path}", f"Expected image path (not generated): {output_path}"))

# 生成数据文件（无论是否有数据）
if is_multi_pop:
    bin_filename = f"{out_prefix}_multi_bin.txt"
else:
    bin_filename = f"{out_prefix}_single_bin.txt"

if all_bin_data and len(all_bin_data) > 0:
    # 有数据时，生成正常的数据文件
    merged_df = None
    for group_name, data in all_bin_data:
        group_df = data[['Distance(bp)', 'Mean_r^2']].copy()
        group_df = group_df.rename(columns={'Mean_r^2': group_name})
        if merged_df is None:
            merged_df = group_df
        else:
            merged_df = pd.merge(merged_df, group_df, on='Distance(bp)', how='outer')
    merged_df = merged_df.sort_values('Distance(bp)').reset_index(drop=True)
    merged_df.to_csv(bin_filename, sep='\t', index=False)
    print(f"Bin-processed summary file saved as: {bin_filename}")
else:
    # 没有数据时，生成空的占位文件
    print(tr("警告：没有有效数据，生成空的占位文件", "Warning: no valid data, generated an empty placeholder file."))
    with open(bin_filename, "w", encoding="utf-8") as f:
        f.write("Distance(bp)\tMean_r^2\n")
        f.write("0\t0\n")
    print(tr(f"生成空的占位文件: {bin_filename}", f"Generated placeholder file: {bin_filename}"))

print("out_prefix:", out_prefix)
print("os.getcwd():", os.getcwd())
if output_path:
    print("output_path:", output_path)
else:
    print(tr("output_path: 未生成图片（matplotlib不可用）", "output_path: image not generated (matplotlib unavailable)"))
