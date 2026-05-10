# PopLDdecayGUI 安装包制作指南

## 一、当前项目概况

- **主程序**：`PopLDdecayGUI_run.exe`（Release 构建位于 `build/Desktop_Qt_6_9_1_MinGW_64_bit-release1.1/src/`）
- **依赖**：Qt6（Widgets、Charts、OpenGL 等）、zlib（`libz.dll`）、Python 脚本（`plot_lddecay_multi.py`、`split_large_vcf.py`）
- **工具**：Qt 6.9.1 MinGW、CMake，本机已有 `windeployqt.exe` 和 `cpack.exe`

若你已把 **exe 及所有依赖** 集中放在 **src 文件夹**（或某一“发布用”文件夹），可直接从下文 **第二步** 开始；否则先完成 **第一步** 整理发布目录。

---

## 二、行动建议总览

| 步骤 | 内容 | 说明 |
|------|------|------|
| 1 | 整理“发布目录” | 把 exe、Qt DLL、zlib、Python 脚本等放到一个文件夹，便于打包 |
| 2 | 选安装包工具 | 推荐 **Inno Setup** 或 **NSIS**，或使用 **CMake CPack** 与 NSIS 集成 |
| 3 | 编写安装脚本/配置 | 定义安装路径、快捷方式、卸载、可选组件等 |
| 4 | 生成安装包并测试 | 在干净系统或虚拟机中测试安装与运行 |

---

## 三、第一步：整理发布目录（若尚未整理）

### 3.1 使用 windeployqt 收集 Qt 依赖

在 **PowerShell** 或 **命令提示符** 中执行（路径按你本机 Qt 安装调整）：

```powershell
# 进入 Release 构建的 exe 所在目录
cd D:\PopLDdecay10.0\PopLDdecayGUI\build\Desktop_Qt_6_9_1_MinGW_64_bit-release1.1\src

# 复制 Qt 所需 DLL、plugins、translations 等到当前目录
C:\Qt\6.9.1\mingw_64\bin\windeployqt.exe --release --no-compiler-runtime PopLDdecayGUI_run.exe
```

如需更精简，可加 `--no-translations`；若程序用到了 Qt 插件（如 styles、imageformats），不要加 `--no-plugins`。

### 3.2 确保以下文件在同一目录

- `PopLDdecayGUI_run.exe`
- windeployqt 生成的 Qt DLL 及 `plugins`、`translations` 等
- `libz.dll`（来自 zlib，若为动态链接）
- `plot_lddecay_multi.py`、`split_large_vcf.py`（程序运行时会调用）

### 3.3 建议的“发布根目录”结构

可以新建一个专门用于打包的目录，例如：

```
PopLDdecayGUI_Release/
├── PopLDdecayGUI_run.exe
├── libz.dll
├── plot_lddecay_multi.py
├── split_large_vcf.py
├── Qt6*.dll
├── plugins/
└── translations/   （如需要）
```

把你现有的 **src 中 exe + 依赖** 或 **build/.../src** 中上述文件拷贝到 `PopLDdecayGUI_Release`，后续安装包就打包这个目录。

---

## 四、第二步：选择安装包工具

### 方案 A：Inno Setup（推荐，易上手）

- **优点**：脚本简单、界面友好、中文支持好、可做单文件 exe 或目录安装。
- **下载**：https://jrsoftware.org/isinfo.php  
- **步骤概要**：  
  1. 安装 Inno Setup。  
  2. 用“向导”或自己写 `.iss` 脚本，指定“发布根目录”为待打包目录，安装目标目录如 `{pf}\PopLDdecayGUI`，勾选创建桌面/开始菜单快捷方式。  
  3. 编译脚本得到 `PopLDdecayGUI_Setup.exe`。

### 方案 B：NSIS（Nullsoft Scriptable Install System）

- **优点**：开源、与 CMake CPack 集成好、可做很细的控制。  
- **下载**：https://nsis.sourceforge.io/  
- **步骤概要**：  
  1. 安装 NSIS。  
  2. 用 CPack 的 NSIS 生成器（见下文），或手写 `.nsi` 脚本，指定安装目录、快捷方式、卸载程序。  
  3. 编译得到安装包 exe。

### 方案 C：CMake CPack + NSIS

- **优点**：与现有 CMake 工程一致，一次配置后可重复生成安装包。  
- **前提**：CMake 中已配置 `install()` 规则，且安装后目录结构正确（exe、DLL、脚本等都在同一逻辑目录）。  
- **步骤概要**：在顶层 `CMakeLists.txt` 中增加 CPack 与 NSIS 配置，然后 `cmake --build . --target package`（或先 `make install` 到 staging 目录再打包）。

---

## 五、第三步：具体实施示例

### 5.1 Inno Setup 脚本示例（.iss）

在 `PopLDdecayGUI` 下创建 `installer/PopLDdecayGUI.iss`（路径与名称可自定）：

```iss
[Setup]
AppName=PopLDdecayGUI
AppVersion=1.0
DefaultDirName={autopf}\PopLDdecayGUI
DefaultGroupName=PopLDdecayGUI
OutputDir=output
OutputBaseFilename=PopLDdecayGUI_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Files]
; 将 Source 改为你的“发布根目录”实际路径
Source: "D:\PopLDdecayGUI_Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PopLDdecayGUI"; Filename: "{app}\PopLDdecayGUI_run.exe"
Name: "{autodesktop}\PopLDdecayGUI"; Filename: "{app}\PopLDdecayGUI_run.exe"

[Run]
Filename: "{app}\PopLDdecayGUI_run.exe"; Description: "运行 PopLDdecayGUI"; Flags: nowait postinstall skipifsilent
```

用 Inno Setup 打开该 `.iss`，点击“编译”即可在 `output` 下得到安装包。

### 5.2 在 CMake 中启用 CPack（NSIS）

若希望用 CPack 生成 NSIS 安装包，可在 **顶层** `CMakeLists.txt` 末尾追加：

```cmake
# 安装规则：将可执行文件、脚本等安装到目标目录
install(TARGETS PopLDdecayGUI RUNTIME DESTINATION bin)
# 若 Python 脚本在 src 下，且 install 时需拷贝：
# install(FILES src/plot_lddecay_multi.py src/split_large_vcf.py DESTINATION bin)
# 并在安装后对该目录执行 windeployqt（通过 install(SCRIPT ...) 或 add_custom_target）

set(CPACK_PACKAGE_NAME "PopLDdecayGUI")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_INSTALL_DIRECTORY "PopLDdecayGUI")
set(CPACK_GENERATOR "NSIS")
set(CPACK_NSIS_MODIFY_PATH ON)
set(CPACK_NSIS_ENABLE_UNINSTALL_BEFORE_UPGRADE ON)
include(CPack)
```

注意：CPack 打包的是 **install 后的目录**，因此需要先配置好 `install()`，并且保证安装目录里已包含所有 DLL 和脚本（可在 install 后自动执行 windeployqt 或复制脚本）。

---

## 六、第四步：测试与发布

1. **本机**：用生成的安装包在另一目录安装一次，运行 `PopLDdecayGUI_run.exe`，确认界面、绘图、调用 Python 脚本均正常。  
2. **干净环境**：在一台未装 Qt/开发环境的 Windows 上（或虚拟机）安装并运行，确认无缺 DLL、缺脚本等错误。  
3. **可选**：在安装包中附带简短 `README.txt`（使用说明、Python 版本要求等），通过 Inno/NSIS 的 `[Files]` 一并打包。

---

## 七、检查清单（发布前）

- [ ] 所有 Qt 依赖已通过 windeployqt 或手动拷贝到发布目录  
- [ ] `libz.dll` 在 exe 同目录或系统 PATH  
- [ ] `plot_lddecay_multi.py`、`split_large_vcf.py` 在 exe 同目录（与当前运行逻辑一致）  
- [ ] 安装包在“仅用户安装”或“本机安装”下都测试通过  
- [ ] 卸载程序能正确移除快捷方式和安装文件  

按上述步骤，即可从“src 中已有 exe 与依赖”的现状，系统性地做出 Windows 安装包。若你确定发布目录的最终路径和安装包工具（Inno / NSIS / CPack），可以再细化对应脚本或 CMake 修改。
