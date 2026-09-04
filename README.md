# PopLDdecayGUI

**WinPopLDdecay: a hardware-adaptive and reproducible reimplementation of PopLDdecay with a graphical interface**

A C#/.NET reimplementation of **[PopLDdecay](https://doi.org/10.1093/bioinformatics/bty875)** (Zhang *et al.*, *Bioinformatics*, 2019) with a graphical interface. It follows the reference implementation (hewm2008 v3.45) in its analysis semantics, parameter defaults and on-disk file formats, and adds one-click plotting, EHH analysis, automatic multi-core computation, vector figure export, result caching and reproducibility tracking. No command line and no database are required.

> If you use this tool, please cite the original PopLDdecay article &nbsp;·&nbsp; DOI: [10.1093/bioinformatics/bty875](https://doi.org/10.1093/bioinformatics/bty875) &nbsp;·&nbsp; PMID: [30321304](https://www.ncbi.nlm.nih.gov/pubmed/30321304)

中文使用说明见 **[README.zh-CN.md](README.zh-CN.md)**

### 1) Install
------------
**Requirements:** 64-bit Windows 7 SP1 – Windows 11, with **.NET Framework 4.8** (already present on Windows 10/11; Windows 7/8.1 users install it once from Microsoft). No database, no other dependency.

**Method 1 — Run the installer (recommended)**
<pre>
      1. Download and run   PopLDdecayGUI_Setup_2.3.2.exe
      2. Administrator rights are not required; a desktop shortcut is optional.
      #  It installs BOTH programs side by side:
      #      PopLDdecayGUI.exe     the graphical interface
      #      PopLDdecay.cli.exe    the headless command line (shipped since 2.3.2)
</pre>

**Method 2 — Build from source** (needs the **.NET SDK 8.0 or newer**)
<pre>
      git clone https://github.com/melonlink/PopLDdecayGUI.git
      cd PopLDdecayGUI/PopLDdecayGUI/csharp          # &lt;clone&gt;/PopLDdecayGUI/csharp
      dotnet build -c Release
      #  GUI  ->  src/PopLD.App/bin/Release/net48/PopLDdecayGUI.exe
      #  CLI  ->  src/PopLD.Cli/bin/Release/net48/PopLDdecay.cli.exe
</pre>

### 2) Example
------------

**A. Graphical interface — `PopLDdecayGUI.exe`**

The left rail has two numbered stages; the chart fills the rest of the window, with the run log and the status bar below it.
<pre>
      # Stage 1 - "Data & Computation"
            [Browse]        choose one or more  .vcf / .vcf.gz  (BGZF supported)
            Sample scope    [All samples] , or [Sample list] and then [Select] the list file
            Filters         MaxDist / MAF / Het / Miss
            Analysis        1 : r²      2 : r² + D'      3 : EHH
                            (type 3 shows an "EHH site" box; write the anchor as chr:pos)
            [Run Analysis]  -> writes  &lt;name&gt;.LDdecay.stat.gz  next to the VCF
                               (EHH: &lt;name&gt;.LDdecay.ehh.gz) and plots it right away.
                               The button reads [Cancel] while the run is going.

      # Stage 2 - "Plot & Export"   (replots without recomputing)
            [Select]        one or more  .stat.gz / .ehh.gz   (multiple = overlay populations)
            set  bin1 / bin2 / break / maxX  and the  Y axis , then  [Generate Plot]

      # Export
            [Export Image+Data]   -> &lt;name&gt;.png  +  &lt;name&gt;.pdf (true vector)
                                     +  one data file per plotted result file

      # Title bar
            [Reset]   clears the file selections, the chart and the cached results
            [中文 / English]   switches the interface language
            [Help]    prints a quick reference into the run log
</pre>

**B. Command line — `PopLDdecay.cli.exe`** (for scripts / clusters / reproducibility runs)
<pre>
      # 1)  Calculate LD decay from a VCF file, run directly
            PopLDdecay.cli  --vcf  SNP.vcf.gz  --out  LDdecay

      # 2)  Output both r^2 and D' , with a 500 kb window
            PopLDdecay.cli  --vcf  SNP.vcf.gz  --out  LDdecay  --outtype 2  --maxdist 500

      # 3)  Subgroup GroupA LD decay   # put GroupA sample names into GroupA.list
            PopLDdecay.cli  --vcf  in.vcf.gz  --out  GroupA  --subpop  GroupA.list

      # 4)  EHH around an anchor site   # needs a PHASED VCF; MAF is raised to 0.05
            PopLDdecay.cli  --vcf  phased.vcf.gz  --out  EHH  --ehh  22:17000000

      # 5)  Plot two populations together: vector PDF + the binned tables
            PopLDdecay.cli  --plot  "GroupA.stat.gz;GroupB.stat.gz"  --plotout  compare  --measure both
</pre>

### 3) Introduction
------------
Linkage disequilibrium (LD) decay is one of the most common and informative analyses in population resequencing: it reflects recombination history, effective population size, and the marker density required for association mapping. PopLDdecayGUI reads a VCF file directly, filters sites, computes pairwise r²/D' between every pair of SNPs within a maximum distance, and produces a compressed statistics file together with a decay-curve figure. It can also compute the extended haplotype homozygosity (EHH) around a chosen anchor site. Compressed files are used for both input and output to save storage, and the pairwise computation is automatically parallelised across CPU cores. The results follow the reference implementation exactly (see Note 5).

* **Parameter description**
```text
      Filter / analysis parameters                                      default   CLI flag
      -----------------------------------------------------------------------------------------
      MaxDist   (kb)     Max distance between two SNP ................... [300]     --maxdist
      MAF                Min minor allele frequency filter ............. [0.005]   --maf
      Het                Max ratio of heterozygous samples ............. [0.880]   --het
      Miss               Max ratio of missing samples .................. [0.250]   --miss
      Analysis           1: r^2   2: r^2 & D'   3: EHH ................. [1]       --outtype
      EHH site           Anchor for analysis 3, e.g. 22:17000000 ....... [none]    --ehh
      Sample list        Subgroup sample list .......................... [ALL]     --subpop

      Plot parameters
      -----------------------------------------------------------------------------------------
      bin1      (bp)     Fine bin width, used before 'break' ........... [10]      --bin1
      bin2      (bp)     Coarse bin width, used after 'break' .......... [100]     --bin2
      break     (bp)     Distance where fine/coarse binning switches ... [100]     --break
      maxX      (kb)     Upper bound of the plot X-axis; 0 = auto ...... [300]     --maxx
      Y axis             r^2 / D' / both, offered from the CONTENT of              --measure
                         the selected result files ..................... [r^2]
      Export size (px)   Canvas of the exported figure ............ [1200 x 900]   --w / --h

      CLI-only options
      -----------------------------------------------------------------------------------------
      --out      <str>   Output prefix (writes <prefix>.stat.gz)                   [out]
      --plot     <files> Plot existing result files, ';'-separated
      --plotout  <str>   Figure prefix                                             [LDdecay]
      --no-cache         Disable the result cache and provenance ledger
      --deterministic    Single-thread, fixed accumulation order (reproducible)
      --dop      <int>   Force the degree of parallelism [auto]
      --block    <int>   Pairwise block size, >= 8 [128]
      --scan     <file>  Reader self-check: print per-filter site counts
      --binn     <file>  Print the first bins of a .stat.gz under the default binning
```
The defaults above are the values the GUI starts with. On the command line `--maxx` defaults to the result file's own range rather than 300, and `--out` / `--plotout` create their output folder if it does not exist. `--maxx` only bounds the plotted range: it never drops data, so changing it does not change the exported table.

### 4) Output & Results
------------
`<name>.LDdecay.stat.gz` — gzip-compressed, tab-separated text, one row per distance (bp):
```text
      #Dist   Mean_r^2   Mean_D'   Sum_r^2   Sum_D'   NumberPairs
```
The format is identical to the original PopLDdecay (the D' columns are `NA` when the analysis type is 1), so existing downstream scripts work unchanged. Analysis type 3 instead writes `<name>.LDdecay.ehh.gz` in the original `.ehh` layout — `#Chr Site Dist EHH_all EHH_0 EHH_1`, with `Dist` signed relative to the anchor. A sample list or an EHH anchor is inserted into the file name, so different subgroups and anchors of one VCF never overwrite each other.

**Export** writes the figure twice — `<name>.png` (raster) and `<name>.pdf` (**true vector**, journal-ready) — plus the plotted values, one data file per result file on the chart: `<name>.bin.gz` for a single LD source and `<name>.<result>.bin.gz` for each of several, in the reference tool's own six-column `.bin` layout; an EHH plot writes `<name>.ehh.gz` instead, in the reference `.ehh` layout. The log lists every file it wrote by name.

Every result file gets a `<result>.provenance.txt` sidecar beside it recording the timestamp, tool version, input, all filter parameters, the number of pairs evaluated, and whether the bytes were computed or replayed from the cache. The result cache and a per-run provenance ledger are stored under `%LocalAppData%\PopLDdecay\`, so a repeated run with the same input and parameters returns instantly from cache; lowering MaxDist reuses a wider cached result by truncation instead of recomputing.

### 5) Note — result equivalence & performance
------------
The LD engine implements the exhaustive *all-pairs-within-MaxDist* algorithm of the original paper, and version 2.3.0 aligned every remaining computational path with the reference implementation (hewm2008 v3.45): the previously missing unphased-VCF encoder, duplicate-record handling, the four-decimal `%.4f` formatting, the sample-list join rules, and the reference's binning and export rules. Only the performance work — multi-core parallelism, bit-packing and the result cache — differs from the reference, and none of it changes a number. Validation: real 1000 Genomes chr22 (210,201 SNP / 408,898,445 pairs) matches the original PopLDdecay C++ compiled and run on Linux, at every distance bin; EHH output is byte-identical to the original binary's; unphased results are byte-identical to a reference-equivalent oracle. The original's other output modes (its `OutType` 3–8, pairwise LD dumps and count tables) are not implemented, and the CLI rejects those values instead of silently falling back. On modern machines the non-GUI core additionally targets **.NET 8**, where the pairwise kernel uses the hardware **POPCNT** instruction for extra speed; the shipping GUI stays on **.NET Framework 4.8** for Windows 7–11 compatibility.

### 6) Citation & Contact
------------
- **Please cite:**
- **Zhao BY et al., WinPopLDdecay: a hardware-adaptive and reproducible reimplementation of PopLDdecay with a graphical interface**
- ** Zhang C, Dong S-S, Xu J-Y, He W-M, Yang T-L. *PopLDdecay: a fast and effective tool for linkage disequilibrium decay analysis based on variant call format files.** **Bioinformatics**. 2019;35(10):1786–1788. DOI: [10.1093/bioinformatics/bty875](https://doi.org/10.1093/bioinformatics/bty875)
- Original PopLDdecay: https://github.com/hewm2008/PopLDdecay
- PopLDdecayGUI 2.3.2: https://github.com/melonlink/PopLDdecayGUI

######################  Linkage Disequilibrium Decay, made simple on Windows  ######################
