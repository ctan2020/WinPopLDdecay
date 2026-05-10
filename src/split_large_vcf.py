# Copyright (c) 2026 BGI-Shenzhen
# Licensed under the MIT License. See LICENSE file for details.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VCF 大文件拆分脚本
- 检测大于阈值(默认 5MB)的染色体，将其分块写出临时 VCF
- 依次对每个分块运行 PopLDdecay
- 合并所有 .stat(.gz) 到最终输出

返回码:
 0: 成功并生成最终输出
 1: 输入/参数错误
 2: 未找到或无法执行 PopLDdecay
 3: 处理过程中无有效输出(提醒检查 PopLDdecay 或数据)
"""

import os
import sys
import io
import gzip
import argparse
import tempfile
import shutil
import time
import subprocess
import multiprocessing as mp
from collections import defaultdict
import shutil
from decimal import Decimal, InvalidOperation

# 强制 stdout/stderr 使用 utf-8，避免 Windows 控制台编码导致的异常
try:
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')
except Exception:
    pass

LANG = 'zh'

def tr(zh: str, en: str) -> str:
    return en if LANG == 'en' else zh

def human_mb(bytes_size: int) -> float:
    return bytes_size / (1024.0 * 1024.0)

def estimate_uncompressed_mb(path: str) -> float:
    size_mb = human_mb(os.path.getsize(path))
    # 粗略估计.gz 解压后 3 倍
    if path.lower().endswith('.gz'):
        return size_mb * 3.0
    return size_mb

def read_header(path: str):
    header = []
    opener = gzip.open if path.lower().endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('#'):
                header.append(line)
            else:
                break
    return header

def analyze_by_chrom_sizes(path: str):
    chr_sizes = defaultdict(int)
    opener = gzip.open if path.lower().endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line or line.startswith('#'):
                continue
            # 仅按长度累加，避免存储整行
            parts = line.rstrip('\n').split('\t')
            if not parts:
                continue
            chrom = parts[0]
            chr_sizes[chrom] += len(line)
    chr_sizes_mb = {c: human_mb(sz) for c, sz in chr_sizes.items()}
    return chr_sizes_mb

def split_selected_chroms(path: str, header: list, large_chrs: set, out_root: str, max_lines: int):
    """
    第二遍：仅对 large_chrs 中的染色体流式分块写文件，返回 {chrom: [chunk_paths...]}
    不缓存整染色体行，内存占用稳定。
    """
    result = {c: [] for c in large_chrs}
    opener = gzip.open if path.lower().endswith('.gz') else open
    # 为每个染色体维护当前块信息
    current_idx = {c: 0 for c in large_chrs}
    lines_in_chunk = {c: 0 for c in large_chrs}
    handles = {c: None for c in large_chrs}
    try:
        with opener(path, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line or line.startswith('#'):
                    continue
                parts = line.rstrip('\n').split('\t')
                if not parts:
                    continue
                chrom = parts[0]
                if chrom not in large_chrs:
                    continue
                # 轮转打开 chunk 文件
                if handles[chrom] is None or lines_in_chunk[chrom] >= max_lines:
                    # 关闭旧文件
                    if handles[chrom] is not None:
                        handles[chrom].close()
                    # 新文件
                    current_idx[chrom] += 1
                    chrom_dir = os.path.join(out_root, f"chr_{chrom}")
                    os.makedirs(chrom_dir, exist_ok=True)
                    chunk_path = os.path.join(chrom_dir, f"{chrom}_chunk_{current_idx[chrom]}.vcf")
                    w = open(chunk_path, 'w', encoding='utf-8')
                    for h in header:
                        w.write(h)
                    handles[chrom] = w
                    lines_in_chunk[chrom] = 0
                    result[chrom].append(chunk_path)
                    print(tr(f"  写出分块: {chunk_path}", f"  Wrote chunk: {chunk_path}"))
                handles[chrom].write(line)
                lines_in_chunk[chrom] += 1
    finally:
        for c, h in handles.items():
            try:
                if h is not None:
                    h.close()
            except Exception:
                pass
    return result

def split_chrom_to_chunks(chrom: str, lines: list, header: list, out_dir: str, max_lines: int = 100000):
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for i in range(0, len(lines), max_lines):
        chunk = lines[i:i+max_lines]
        fp = os.path.join(out_dir, f"{chrom}_chunk_{(i//max_lines)+1}.vcf")
        with open(fp, 'w', encoding='utf-8') as w:
            for h in header:
                w.write(h)
            for ln in chunk:
                w.write(ln)
        files.append(fp)
        print(tr(f"  写出分块: {fp} 行数={len(chunk)}", f"  Wrote chunk: {fp} lines={len(chunk)}"))
    return files

def stream_blocks(path: str, header: list, out_root: str, max_lines: int):
    """按固定行数 block 流式切分全文件（不区分染色体），返回分块文件列表"""
    blocks = []
    opener = gzip.open if path.lower().endswith('.gz') else open
    idx = 0
    written = 0
    w = None
    try:
        with opener(path, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line or line.startswith('#'):
                    continue
                if w is None or written >= max_lines:
                    if w is not None:
                        w.close()
                    idx += 1
                    block_path = os.path.join(out_root, f"block_{idx}.vcf")
                    w = open(block_path, 'w', encoding='utf-8')
                    for h in header:
                        w.write(h)
                    written = 0
                    blocks.append(block_path)
                    print(tr(f"  写出分块: {block_path}", f"  Wrote block: {block_path}"))
                w.write(line)
                written += 1
    finally:
        if w is not None:
            try:
                w.close()
            except Exception:
                pass
    return blocks


def split_vcf_to_size_blocks(input_vcf: str, header: list, temp_dir: str, block_mb: float):
    """
    按近似大小(字节)将 VCF 主体(非header)流式切成多个 block 文件。
    - 不区分染色体，每个 block 代表一个连续的“区域”。
    - 单次只保持一个输出文件句柄，内存占用稳定。
    - 使用较大的缓冲区以提升磁盘 IO 吞吐。
    返回: block_vcf_path 列表(按顺序)。
    """
    target_bytes = int(block_mb * 1024 * 1024)
    print(f"[split] target block size: {target_bytes} bytes ({block_mb} MB)")

    opener = gzip.open if input_vcf.lower().endswith('.gz') else open
    idx = 0
    written_bytes = 0
    w = None
    current_block_path = None
    block_paths = []
    try:
        # 逐行读取，避免一次性读入内存
        with opener(input_vcf, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line or line.startswith('#'):
                    continue
                # 需要开启新 block
                if w is None or written_bytes >= target_bytes:
                    if w is not None:
                        try:
                            w.close()
                        except Exception:
                            pass
                        actual_mb = written_bytes / (1024.0 * 1024.0)
                        print(f"[split] finished block {idx}: {current_block_path} (size: {actual_mb:.2f} MB)")
                    idx += 1
                    current_block_path = os.path.join(temp_dir, f"block_{idx}.vcf")
                    # 使用 1MB 缓冲区提升写入性能
                    w = open(current_block_path, 'w', encoding='utf-8', buffering=1024 * 1024)
                    for h in header:
                        w.write(h)
                    written_bytes = 0
                    block_paths.append(current_block_path)
                    print(f"[split] writing block {idx}: {current_block_path} (target: {block_mb} MB)")
                # 写入当前行
                w.write(line)
                # 使用编码后的字节长度，更接近真实磁盘大小
                written_bytes += len(line.encode('utf-8', errors='ignore'))
    finally:
        if w is not None:
            try:
                w.close()
            except Exception:
                pass

    if not block_paths:
        print("[split] no data lines found when splitting into blocks")
    else:
        print(f"[split] total blocks: {len(block_paths)}")

    return block_paths


def _worker_run_poplddecay(task):
    """
    多进程 worker：在一个 block 上运行 PopLDdecay。
    task: (poplddecay_exe, vcf_path, out_prefix, maxdist, maf, het, miss, subpop, ehh, outtype)
    返回 (vcf_path, out_prefix, ok: bool)
    """
    poplddecay_exe, vcf_path, out_prefix, maxdist, maf, het, miss, subpop, ehh, outtype = task
    ok = run_poplddecay(poplddecay_exe, vcf_path, out_prefix, maxdist, maf, het, miss, subpop, ehh, outtype)
    return (vcf_path, out_prefix, ok)

def resolve_executable(exe_path: str) -> str:
    """解析可执行文件：绝对路径存在则用之，否则尝试 PATH / 后缀变体。"""
    # 绝对/相对路径存在
    if exe_path and os.path.exists(exe_path):
        return exe_path
    # PATH 中查找
    found = shutil.which(exe_path)
    if found:
        return found
    # Windows 下尝试附加 .exe 以及常见可执行名（实际构建输出为 PopLDdecayGUI_run.exe）
    if os.name == 'nt':
        bases = [exe_path]
        if not exe_path.lower().endswith('.exe'):
            bases.append(exe_path + '.exe')
        # 常见别名：CLI 与 GUI 可执行（GUI 支持 --cli-run）
        bases.extend(['PopLDdecay.exe', 'PopLDdecayGUI.exe', 'PopLDdecayGUI_run.exe'])
        for b in bases:
            found = shutil.which(b)
            if found:
                return found
    return ''

def is_executable_available(exe_path: str) -> bool:
    # 仅检查路径是否存在或 PATH 可解析；不做试运行，避免 GUI 可执行挂起
    if not exe_path:
        return False
    if os.path.isabs(exe_path):
        return os.path.exists(exe_path)
    return shutil.which(exe_path) is not None

def run_poplddecay(poplddecay_exe: str,
                   vcf_path: str,
                   out_prefix: str,
                   maxdist: int,
                   maf: float,
                   het: float,
                   miss: float,
                   subpop: str,
                   ehh: str,
                   outtype: int):
    # 如果是 GUI 可执行（含 PopLDdecayGUI_run.exe），优先尝试同目录的 PopLDdecay.exe，否则使用 GUI 的 --cli-run 模式
    exe_basename = os.path.basename(poplddecay_exe).lower()
    is_gui_exe = exe_basename in ('poplddecaygui.exe', 'poplddecaygui_run.exe')
    if os.name == 'nt' and is_gui_exe:
        same_dir = os.path.dirname(poplddecay_exe)
        cli_candidate = os.path.join(same_dir, 'PopLDdecay.exe')
        if os.path.exists(cli_candidate):
            poplddecay_exe = cli_candidate
            print(f"Switch to CLI executable: {poplddecay_exe}")
            cmd = [poplddecay_exe, '-InVCF', vcf_path, '-OutStat', out_prefix]
        else:
            # 使用 GUI 的命令行模式：--cli-run --invcf ... --outstat ...
            cmd = [poplddecay_exe, '--cli-run', '--invcf', vcf_path, '--outstat', out_prefix]
    else:
        cmd = [poplddecay_exe, '-InVCF', vcf_path, '-OutStat', out_prefix]
    cmd.extend(['-MaxDist', str(maxdist),
                '-MAF', str(maf),
                '-Het', str(het),
                '-Miss', str(miss),
                '-OutType', str(outtype)])
    if subpop:
        cmd.extend(['-SubPop', subpop])
    if ehh:
        cmd.extend(['-EHH', ehh])
    print(tr(f"执行: {' '.join(cmd)}", f"Running: {' '.join(cmd)}"))
    try:
        exe_dir = os.path.dirname(cmd[0]) or None
        # 流式读取，避免长时间无日志
        p = subprocess.Popen(cmd, cwd=exe_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        last_print = time.time()
        output_lines = []
        while True:
            line = p.stdout.readline()
            if line:
                print(line.rstrip('\n'))
                output_lines.append(line)
                last_print = time.time()
            elif p.poll() is not None:
                break
            else:
                # 心跳日志：每30秒提示仍在运行
                now = time.time()
                if now - last_print > 30:
                    print(tr("[split] 子进程仍在运行...", "[split] subprocess still running..."))
                    last_print = now
                time.sleep(0.2)
        rc = p.returncode
        if rc != 0:
            joined = ''.join(output_lines[-200:])  # 最近输出
            print(tr(f"PopLDdecay 返回码={rc}\n最近输出:\n{joined}", f"PopLDdecay exit_code={rc}\nRecent output:\n{joined}"))
            return False
        print(tr(f"PopLDdecay 完成: {out_prefix}.stat.gz", f"PopLDdecay completed: {out_prefix}.stat.gz"))
        return True
    except Exception as e:
        print(tr(f"运行 PopLDdecay 异常: {e}", f"PopLDdecay runtime exception: {e}"))
        return False

def _to_decimal(value: str):
    if value is None:
        return None
    text = value.strip()
    if not text or text.upper() == 'NA':
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None

def _format_mean(val: Decimal):
    # 与 C++ setprecision(4)+fixed 对齐：4位小数
    return f"{val:.4f}"

def _format_sum(val: Decimal):
    # Sum 字段沿用 C++ 默认 double 输出风格：去掉无意义尾随0
    text = format(val, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text if text else '0'

def _format_dist(val: Decimal):
    # Dist 保留原始数值粒度，避免 int 截断造成误合并
    text = format(val.normalize(), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text if text else '0'

def merge_stats(stat_files, output_file):
    """
    按 Dist 聚合所有分块统计结果，并按 NumberPairs 做加权平均：
      Mean_r^2 = sum(Sum_r^2) / sum(NumberPairs)
      Mean_D'  = sum(Sum_D')  / sum(NumberPairs)   (若存在有效 D' 数据)
    """
    if not stat_files:
        return False

    merged = {}  # dist(Decimal) -> {'sum_r2': Decimal, 'sum_d': Decimal|None, 'count_r2': int, 'count_d': int}
    header = "#Dist\tMean_r^2\tMean_D'\tSum_r^2\tSum_D'\tNumberPairs\n"

    for sf in stat_files:
        op = gzip.open if sf.lower().endswith('.gz') else open
        with op(sf, 'rt', encoding='utf-8', errors='ignore') as f:
            first = f.readline()
            if first and first.lstrip().startswith('#Dist'):
                header = first if first.endswith('\n') else (first + '\n')
            else:
                # 兼容无表头文件：把首行当数据处理
                f.seek(0)

            for line in f:
                raw = line.strip()
                if not raw or raw.startswith('#'):
                    continue
                cols = raw.split()
                if len(cols) < 6:
                    continue
                dist = _to_decimal(cols[0])
                if dist is None:
                    continue
                try:
                    count = int(cols[5])
                except ValueError:
                    continue
                if count <= 0:
                    continue

                sum_r2 = _to_decimal(cols[3])
                sum_d = _to_decimal(cols[4])
                if sum_r2 is None:
                    continue

                bucket = merged.get(dist)
                if bucket is None:
                    bucket = {'sum_r2': Decimal('0'), 'sum_d': None, 'count_r2': 0, 'count_d': 0}
                    merged[dist] = bucket

                bucket['sum_r2'] += sum_r2
                bucket['count_r2'] += count
                if sum_d is not None:
                    if bucket['sum_d'] is None:
                        bucket['sum_d'] = Decimal('0')
                    bucket['sum_d'] += sum_d
                    bucket['count_d'] += count

    if not merged:
        print("[split] error: no valid rows found when merging stat files")
        return False

    lines_out = []
    for dist in sorted(merged.keys()):
        item = merged[dist]
        count_r2 = item['count_r2']
        if count_r2 <= 0:
            continue
        mean_r2 = item['sum_r2'] / Decimal(count_r2)

        if item['sum_d'] is None or item['count_d'] <= 0:
            mean_d = 'NA'
            sum_d = 'NA'
        else:
            mean_d = _format_mean(item['sum_d'] / Decimal(item['count_d']))
            sum_d = _format_sum(item['sum_d'])

        row = (
            f"{_format_dist(dist)}\t{_format_mean(mean_r2)}\t{mean_d}\t"
            f"{_format_sum(item['sum_r2'])}\t{sum_d}\t{count_r2}\n"
        )
        lines_out.append(row)

    if output_file.lower().endswith('.gz'):
        with gzip.open(output_file, 'wt', encoding='utf-8') as w:
            w.write(header if header else "#Dist\tMean_r^2\tMean_D'\tSum_r^2\tSum_D'\tNumberPairs\n")
            w.writelines(lines_out)
    else:
        with open(output_file, 'w', encoding='utf-8') as w:
            w.write(header if header else "#Dist\tMean_r^2\tMean_D'\tSum_r^2\tSum_D'\tNumberPairs\n")
            w.writelines(lines_out)
    print(tr(f"合并完成(按Dist加权平均): {output_file} (有效Dist数={len(lines_out)})", f"Merge finished (Dist-weighted average): {output_file} (valid Dist count={len(lines_out)})"))
    return True

def main():
    print("[split] script started")
    ap = argparse.ArgumentParser(description='Split large VCF and run PopLDdecay')
    ap.add_argument('input_vcf')
    ap.add_argument('output_prefix')
    # 兼容旧调用参数（忽略）：
    ap.add_argument('--min-size', type=float, default=None, help='Deprecated argument (ignored)')
    ap.add_argument('--block-mb', type=float, default=300.0, help='Target VCF block size in MB (default: 300MB)')
    ap.add_argument('--max-lines', type=int, default=100000, help='Deprecated argument (ignored)')
    ap.add_argument('--workers', type=int, default=0, help='Parallel PopLDdecay process count, 0=auto(cpu_count)')
    ap.add_argument('--poplddecay-exe', default='PopLDdecay', help='PopLDdecay executable path or name in PATH')
    ap.add_argument('--temp-dir', default=None, help='Custom temporary directory')
    ap.add_argument('--maxdist', type=int, default=300, help='MaxDist (kb) passed to PopLDdecay')
    ap.add_argument('--maf', type=float, default=0.005, help='MAF passed to PopLDdecay')
    ap.add_argument('--het', type=float, default=0.88, help='Het passed to PopLDdecay')
    ap.add_argument('--miss', type=float, default=0.25, help='Miss passed to PopLDdecay')
    ap.add_argument('--subpop', default='', help='SubPop sample list file passed to PopLDdecay')
    ap.add_argument('--ehh', default='', help='EHH parameter passed to PopLDdecay')
    ap.add_argument('--outtype', type=int, default=1, help='OutType passed to PopLDdecay')
    ap.add_argument('--lang', choices=['zh', 'en'], default='zh', help='Output language (zh/en)')
    args = ap.parse_args()
    global LANG
    LANG = args.lang

    if not os.path.exists(args.input_vcf):
        print(tr(f"错误: 输入文件不存在: {args.input_vcf}", f"Error: input file does not exist: {args.input_vcf}"))
        return 1

    # 检测 PopLDdecay 可执行
    exe_resolved = resolve_executable(args.poplddecay_exe)
    if not exe_resolved or not is_executable_available(exe_resolved):
        print(f"Error: PopLDdecay not found or not executable: {args.poplddecay_exe}")
        return 2

    # 创建临时目录
    temp_dir = args.temp_dir or tempfile.mkdtemp(prefix='vcf_split_')
    created_temp = args.temp_dir is None
    print(f"[split] temp dir: {temp_dir}")
    try:
        print("[split] reading header...")
        header = read_header(args.input_vcf)
        # 决策是否分块（固定策略）
        est_mb = estimate_uncompressed_mb(args.input_vcf)
        print(f"[split] estimated uncompressed size: {est_mb:.2f} MB")
        THRESHOLD_MB = 100.0  # 默认阈值100MB（适合16G内存机器）
        # 每个block的目标大小(MB)，支持通过命令行 --block-mb 调整，默认300MB
        BLOCK_MB = float(args.block_mb or 300.0)
        if est_mb <= THRESHOLD_MB + 1e-6:
            print("[split] below threshold, run whole file (no split)")
            out_prefix = args.output_prefix
            ok = run_poplddecay(exe_resolved, args.input_vcf, out_prefix, args.maxdist, args.maf, args.het, args.miss, args.subpop, args.ehh, args.outtype)
            stat_path = out_prefix + '.stat.gz'
            all_stats = []
            if ok and os.path.exists(stat_path):
                all_stats.append(stat_path)
            else:
                print(f"[split] warn: no stat file: {stat_path}")
            if not all_stats:
                print("[split] warn: no stat files generated")
                return 3
            final_stat = args.output_prefix + '.stat.gz'
            print(f"[split] final stat: {final_stat}")
            return 0

        # 按固定大小(默认300MB)流式分块 -> 多进程并行运行 PopLDdecay -> 合并结果
        print(f"[split] splitting into ~{BLOCK_MB}MB blocks, then running PopLDdecay in parallel...")

        # 1) 先只做 IO 分块，不在循环内串行调用 PopLDdecay，避免单线程瓶颈
        block_paths = split_vcf_to_size_blocks(args.input_vcf, header, temp_dir, BLOCK_MB)
        if not block_paths:
            print("[split] warn: no blocks generated from input VCF")
            return 3

        # 2) 为每个 block 准备任务，并行运行 PopLDdecay
        tasks = []
        for idx, block_path in enumerate(block_paths, start=1):
            out_prefix_b = os.path.join(temp_dir, f"block_{idx}")
            tasks.append((exe_resolved, block_path, out_prefix_b, args.maxdist, args.maf, args.het, args.miss, args.subpop, args.ehh, args.outtype))

        # 自动选择进程数：默认使用 CPU 核心数，至少 1，且不超过 block 数量
        cpu_cnt = max(1, mp.cpu_count())
        workers = int(args.workers) if isinstance(args.workers, int) else 0
        if workers <= 0:
            workers = min(cpu_cnt, len(tasks))
        else:
            workers = max(1, min(workers, len(tasks)))
        print(f"[split] using {workers} worker processes on {len(tasks)} blocks (cpu_count={cpu_cnt})")

        all_stats = []
        # Windows 下需要在 if __name__ == '__main__' 保护中调用 main()，本脚本已满足
        with mp.Pool(processes=workers) as pool:
            for vcf_path, out_prefix_b, ok in pool.imap_unordered(_worker_run_poplddecay, tasks):
                stat_path = out_prefix_b + '.stat.gz'
                if ok and os.path.exists(stat_path):
                    all_stats.append(stat_path)
                else:
                    print(f"[split] warn: PopLDdecay failed or no stat file for block: {vcf_path}")
                # 处理完成后尽早删除临时 block vcf，节省磁盘空间
                try:
                    os.remove(vcf_path)
                except Exception:
                    pass

        if not all_stats:
            print("[split] warn: no stat files generated from any block")
            return 3

        final_stat = args.output_prefix + '.stat.gz'
        if not merge_stats(all_stats, final_stat):
            print("[split] error: merge stats failed")
            return 3
        print(f"[split] final stat: {final_stat}")
        return 0

    except Exception as e:
        print(tr(f"[split] 处理异常: {e}", f"[split] processing exception: {e}"))
        import traceback
        traceback.print_exc()
        return 3
    finally:
        if created_temp:
            try:
                shutil.rmtree(temp_dir)
                print(tr(f"[split] 已清理临时目录: {temp_dir}", f"[split] temporary directory cleaned: {temp_dir}"))
            except Exception as e:
                print(tr(f"[split] 清理临时目录失败: {e}", f"[split] failed to clean temporary directory: {e}"))

if __name__ == '__main__':
    sys.exit(main())

