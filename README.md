
# WinPopLDdecay :A User-Friendly Tool for Linkage Disequilibrium Decay Analysis
WinPopLDdecay is a Windows-native graphical user interface (GUI) tool for efficient linkage disequilibrium (LD) decay analysis in population genetics. It is developed in C++ and Python, integrating core algorithms from the original Linux-based PopLDdecay, providing fast, accurate, and user-friendly LD decay calculations and visualization.

## Features
- Supports VCF and VCF.GZ input formats
- Automatic large-file mode for efficient processing of big datasets
- Parallel computing to reduce runtime and memory usage
- Intuitive GUI with language switching (English/Chinese)
- Supports subgroup analysis within VCF files
- Generates publication-quality LD decay plots
- Compatible with Windows 10 and above

## Installation
1. Download the latest release from the [Releases](https://github.com/XXXXXXXXXXXXXXXXX/WinPopLDdecay/releases) page.
2. Extract the ZIP file to your preferred directory.
3. Double-click the *setup.exe installation package, and follow the prompts to select the installation path and other custom information.
4. Ensure Python 3.16+ is installed for visualization features (optional but recommended).

## Usage

### LD Decay Calculation
1. Launch `WinPopLDdecay.exe` by double click.
2. Click **Select Input File** to load your VCF or VCF.GZ file.
3. (Optional) Import subgroup sample list via **Select Sample List File**.
4. Adjust parameters as needed (e.g., filter parameters, output type).
5. Click **Generate Result File** to start the calculation.
6. Monitor progress in the feedback area.

### Visualization
1. After calculation, click **Select Result File** to choose one or multiple result files.
2. Click **Generate Result Image** to get LD decay plots and binned data.

## Requirements
- Windows 10 or later
- Python 3.16 or higher (for visualization)
- Minimum 8 GB RAM recommended for large datasets

## License
This project is licensed under the MIT license.

## Citation
If you use WinPopLDdecay in your research, please cite:
Zhao, Boyang, et al. WinPopLDdecay: A User-Friendly Tool for Linkage Disequilibrium Decay Analysis. xxx
> [==CITATION HERE==]

## Contact
For questions or feedback, please open an issue or contact [hewm@genomics.cn] and [tancong_2012@hotmail.com].

---

*Developed by BGI-Shenzhen*  
*GitHub: [https://github.com/XXXXXXXXXXXXXXXXXXXXXXXXX/WinPopLDdecay](https://github.com/XXXXXXXXXXXXXXXXXXXXXXXXXX/WinPopLDdecay)*
