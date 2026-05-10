/*
 * Copyright (c) 2026 BGI-Shenzhen
 * Licensed under the MIT License. See LICENSE file for details.
 */
#include "mainwindow.h"
#include "ui_mainwindow.h"
#include "LD_Decay.h"
#include <QAbstractButton>
#include <QLabel>
#include <QFileDialog>
#include <QProcess>
#include <QFile>
#include <QDir>
#include <QFileInfo>
#include <QMessageBox>
#include <QThread>
#include <QDateTime>
#include <QCoreApplication>
#include <QRegularExpression>

static QString localizeScriptOutput(const QString& text, bool useEnglish)
{
    if (!useEnglish || text.isEmpty()) {
        return text;
    }
    QString out;
    const auto lines = text.split('\n');
    const QRegularExpression zhRe("[\\x{4e00}-\\x{9fff}]");
    for (QString line : lines) {
        if (line.isEmpty()) {
            continue;
        }
        if (line.contains("合并完成(按Dist加权平均):")) {
            line.replace("合并完成(按Dist加权平均):", "Merge finished (Dist-weighted average):");
        } else if (line.contains("有效Dist数=")) {
            line.replace("有效Dist数=", "valid Dist count=");
        } else if (line.contains("已清理临时目录")) {
            line.replace("已清理临时目录", "Temporary directory cleaned");
        } else if (line.contains("处理异常")) {
            line.replace("处理异常", "Processing exception");
        } else if (line.contains("清理临时目录失败")) {
            line.replace("清理临时目录失败", "Failed to clean temporary directory");
        } else if (line.contains("执行:")) {
            line.replace("执行:", "Running:");
        } else if (line.contains("运行 PopLDdecay 异常")) {
            line.replace("运行 PopLDdecay 异常", "PopLDdecay runtime exception");
        } else if (line.contains("警告：")) {
            line.replace("警告：", "Warning: ");
        } else if (line.contains("错误：")) {
            line.replace("错误：", "Error: ");
        } else if (line.contains("检测到多个群体文件")) {
            line = "Detected multiple population files, generating comparison plot.";
        } else if (line.contains("检测到单个群体文件")) {
            line = "Detected single population file, generating single-population plot.";
        } else if (line.contains("总共需要处理")) {
            line.replace("总共需要处理", "Total files to process:");
            line.replace("个文件", "");
        } else if (line.contains("成功处理文件")) {
            line.replace("成功处理文件", "Processed file");
        } else if (line.contains("成功处理了")) {
            line.replace("成功处理了", "Successfully processed");
            line.replace("个文件", " files");
        } else if (line.contains("总共收集了")) {
            line.replace("总共收集了", "Collected");
            line.replace("个 r² 数据点", " r² points in total");
        } else if (line.contains("图形包含")) {
            line.replace("图形包含", "Figure contains");
            line.replace("条数据线，准备保存...", " plotted line(s), preparing to save...");
        } else if (line.contains("图片文件不存在，检查数据文件")) {
            line.replace("图片文件不存在，检查数据文件", "Plot file not found, checking data file");
        } else if (line.contains("由于未检测到matplotlib")) {
            line = "matplotlib not detected; skipped image generation and only exported data.";
        } else if (line.contains("生成空的占位文件")) {
            line.replace("生成空的占位文件", "Generated empty placeholder file");
        } else if (zhRe.match(line).hasMatch()) {
            // 英文模式下，未知中文行不直接展示，避免中英混杂
            continue;
        }
        out += line + "\n";
    }
    return out.trimmed();
}

namespace {

// 按中英两种文案分别测量 sizeHint，取较大值作为最小宽度，避免切换语言后同一行控件被挤压裁切。
void setStableMinWidthForButton(QAbstractButton *btn, const QString &zh, const QString &en)
{
    const QString prev = btn->text();
    btn->setText(zh);
    const int wZh = btn->sizeHint().width();
    btn->setText(en);
    const int wEn = btn->sizeHint().width();
    btn->setText(prev);
    btn->setMinimumWidth(qMax(wZh, wEn));
}

void setStableMinWidthForLabel(QLabel *lab, const QString &zh, const QString &en)
{
    const QString prev = lab->text();
    lab->setText(zh);
    const int wZh = lab->sizeHint().width();
    lab->setText(en);
    const int wEn = lab->sizeHint().width();
    lab->setText(prev);
    lab->setMinimumWidth(qMax(wZh, wEn));
}

} // namespace

QString MainWindow::uiText(const QString& zh, const QString& en) const
{
    return useEnglish ? en : zh;
}

void MainWindow::applyLanguage()
{
    setWindowTitle(uiText("PopLDdecay GUI - 连锁不平衡衰减分析工具", "PopLDdecay GUI - Linkage Disequilibrium Decay Analyzer"));
    ui->groupBox_vcf->setTitle(uiText("生成结果文件", "Generate Result Files"));
    ui->groupBox_plot->setTitle(uiText("生成结果图片", "Generate Plots"));
    ui->groupBox_Advanced->setTitle(uiText("过滤参数", "Filter Parameters"));
    ui->selectVCFFiles->setText(uiText("📁 选择VCF文件（可多选）", "📁 Select VCF Files (multi-select)"));
    ui->selectSubpopFile->setText(uiText("👥 选择样本列表文件", "👥 Select Sample List File"));
    ui->runGenerateResult->setText(uiText("⚡ 生成结果文件", "⚡ Generate Result Files"));
    ui->selectResultFiles->setText(uiText("📊 选择多个结果文件", "📊 Select Multiple Result Files"));
    ui->runGeneratePlot->setText(uiText("🎨 生成结果图片", "🎨 Generate Plot"));
    ui->labelGenotypeFilterCaption->setText(uiText("🔬 基因型过滤", "🔬 Genotype Filter"));
    ui->helpButton->setText(uiText("❓ 帮助", "❓ Help"));
    ui->languageButton->setText(uiText("🌐 中文 / English", "🌐 English / 中文"));
    ui->label_bin1->setText(uiText("bin1（分箱起始，bp）", "bin1 (start bin, bp)"));
    ui->label_bin2->setText(uiText("bin2（分箱宽度，bp）", "bin2 (bin width, bp)"));
    ui->label_break->setText(uiText("break（分段阈值，bp）", "break (bp)"));
    ui->label_maxX->setText(uiText("maxX（最大横坐标，kb）", "maxX (kb)"));
    ui->label_maxdist->setText(uiText("MaxDist（最大距离/kb）", "MaxDist (maximum distance/kb)"));
    ui->label_7->setText(uiText("OutType（1:R², 2:R²+D'）", "OutType (1:R², 2:R²+D')"));
    ui->resultTextEdit->setPlaceholderText(uiText("分析和作图结果将在此显示...", "Analysis and plotting logs will be shown here..."));
    ui->spinBox_OutType->setToolTip(uiText(
        "仅控制主程序输出类型：1=R²，2=R²+D'；按所选值原样传导",
        "Controls only output type for core program: 1=R^2, 2=R^2 + D'; value is passed through unchanged"));
    ui->spinBox_MaxDist->setToolTip(uiText(
        "分析最大距离(kb)，大文件模式下同样生效，不再复用为MB阈值",
        "Maximum analysis distance (kb). Still effective in large-file mode and no longer reused as MB threshold."));

    // 中英切换时文案长度差异大，为会变长的控件预留「两种语言下」的较大最小宽度，避免作图区一行被裁切。
    setStableMinWidthForButton(ui->selectVCFFiles,
                               QStringLiteral("📁 选择VCF文件（可多选）"),
                               QStringLiteral("📁 Select VCF Files (multi-select)"));
    setStableMinWidthForButton(ui->selectSubpopFile,
                               QStringLiteral("👥 选择样本列表文件"),
                               QStringLiteral("👥 Select Sample List File"));
    setStableMinWidthForButton(ui->runGenerateResult,
                               QStringLiteral("⚡ 生成结果文件"),
                               QStringLiteral("⚡ Generate Result Files"));
    setStableMinWidthForButton(ui->selectResultFiles,
                               QStringLiteral("📊 选择多个结果文件"),
                               QStringLiteral("📊 Select Multiple Result Files"));
    setStableMinWidthForButton(ui->runGeneratePlot,
                               QStringLiteral("🎨 生成结果图片"),
                               QStringLiteral("🎨 Generate Plot"));
    setStableMinWidthForButton(ui->helpButton,
                               QStringLiteral("❓ 帮助"),
                               QStringLiteral("❓ Help"));
    setStableMinWidthForButton(ui->languageButton,
                               QStringLiteral("🌐 中文 / English"),
                               QStringLiteral("🌐 English / 中文"));
    setStableMinWidthForLabel(ui->labelGenotypeFilterCaption,
                              QStringLiteral("🔬 基因型过滤"),
                              QStringLiteral("🔬 Genotype Filter"));
    setStableMinWidthForLabel(ui->label_bin1,
                              QStringLiteral("bin1（分箱起始，bp）"),
                              QStringLiteral("bin1 (start bin, bp)"));
    setStableMinWidthForLabel(ui->label_bin2,
                              QStringLiteral("bin2（分箱宽度，bp）"),
                              QStringLiteral("bin2 (bin width, bp)"));
    setStableMinWidthForLabel(ui->label_break,
                              QStringLiteral("break（分段阈值，bp）"),
                              QStringLiteral("break (bp)"));
    setStableMinWidthForLabel(ui->label_maxX,
                              QStringLiteral("maxX（最大横坐标，kb）"),
                              QStringLiteral("maxX (kb)"));
    setStableMinWidthForLabel(ui->label_maxdist,
                              QStringLiteral("MaxDist（最大距离/kb）"),
                              QStringLiteral("MaxDist (maximum distance/kb)"));
    setStableMinWidthForLabel(ui->label_7,
                              QStringLiteral("OutType（1:R², 2:R²+D'）"),
                              QStringLiteral("OutType (1:R², 2:R²+D')"));

    updateGeometry();
    const int needW = minimumSizeHint().width();
    if (width() < needW)
        resize(needW, height());
}

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    // 过滤参数区初始化
    ui->spinBox_MaxDist->setMinimum(1);
    ui->spinBox_MaxDist->setMaximum(10000);
    ui->spinBox_MaxDist->setValue(300);
    ui->doubleSpinBox_MAF->setMinimum(0.0);
    ui->doubleSpinBox_MAF->setMaximum(1.0);
    ui->doubleSpinBox_MAF->setDecimals(3);
    ui->doubleSpinBox_MAF->setSingleStep(0.01);
    ui->doubleSpinBox_MAF->setValue(0.005);
    ui->doubleSpinBox_Het->setMinimum(0.0);
    ui->doubleSpinBox_Het->setMaximum(1.0);
    ui->doubleSpinBox_Het->setDecimals(3);
    ui->doubleSpinBox_Het->setSingleStep(0.01);
    ui->doubleSpinBox_Het->setValue(0.88);
    ui->doubleSpinBox_Miss->setMinimum(0.0);
    ui->doubleSpinBox_Miss->setMaximum(1.0);
    ui->doubleSpinBox_Miss->setDecimals(3);
    ui->doubleSpinBox_Miss->setSingleStep(0.01);
    ui->doubleSpinBox_Miss->setValue(0.25);
    ui->lineEdit_EHH->setPlaceholderText("chr1:5000000");
    ui->spinBox_OutType->setMinimum(1);
    ui->spinBox_OutType->setMaximum(2);
    ui->spinBox_OutType->setValue(1);
    ui->spinBox_bin1->setMinimum(0);
    ui->spinBox_bin1->setMaximum(1000000);
    ui->spinBox_bin1->setValue(10);
    ui->spinBox_bin2->setMinimum(10);
    ui->spinBox_bin2->setMaximum(1000000);
    ui->spinBox_bin2->setValue(100);
    // 大文件处理选项初始化 - 使用现有控件
    // OutType 仅保留 1/2，并按原值传导到主程序
    ui->spinBox_OutType->setToolTip("仅控制主程序输出类型：1=R²，2=R²+D'；按所选值原样传导");
    ui->spinBox_MaxDist->setToolTip("分析最大距离(kb)，大文件模式下同样生效，不再复用为MB阈值");
    // MaxDist 变更时同步赋值到 xmax；xmax 后续仍可手动单独修改（不做双向绑定/锁定）
    ui->spinBox_maxX->setValue(ui->spinBox_MaxDist->value());
    connect(ui->spinBox_MaxDist, qOverload<int>(&QSpinBox::valueChanged), this, [this](int v) {
        ui->spinBox_maxX->setValue(v);
    });
    // 多余水平空间优先给左侧主区，避免右侧过滤栏拉长时把作图按钮行挤到裁切。
    ui->mainHLayout->setStretch(0, 1);
    ui->mainHLayout->setStretch(1, 0);
    // 固定所有文本控件字体颜色为黑色
    this->setStyleSheet("QLineEdit, QTextEdit, QPlainTextEdit, QLabel, QSpinBox, QDoubleSpinBox { color: black; }");
    applyLanguage();
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::on_selectVCFFiles_clicked()
{
    vcfInputFiles = QFileDialog::getOpenFileNames(this, uiText("选择VCF文件", "Select VCF files"), "", tr("VCF Files (*.vcf *.vcf.gz);;All Files (*)"));
    if (!vcfInputFiles.isEmpty()) {
        ui->resultTextEdit->append(uiText("已选择VCF文件：\n", "Selected VCF files:\n") + vcfInputFiles.join("\n"));
    }
}

void MainWindow::on_selectSubpopFile_clicked()
{
    subpopFilePath = QFileDialog::getOpenFileName(this, uiText("选择样本列表文件", "Select sample list file"), "", tr("Text Files (*.txt);;All Files (*)"));
    if (!subpopFilePath.isEmpty()) {
        ui->resultTextEdit->append(uiText("已选择样本列表文件：", "Selected sample list file: ") + subpopFilePath);
    }
}

void MainWindow::on_runGenerateResult_clicked()
{
    if (vcfInputFiles.isEmpty()) {
        QMessageBox::warning(this, uiText("提示", "Notice"), uiText("请先选择VCF文件！", "Please select VCF files first."));
        return;
    }
    
    const int maxDistKb = ui->spinBox_MaxDist->value();
    const double maf = ui->doubleSpinBox_MAF->value();
    const double het = ui->doubleSpinBox_Het->value();
    const double miss = ui->doubleSpinBox_Miss->value();
    const QString ehh = ui->lineEdit_EHH->text().trimmed();
    const int outType = ui->spinBox_OutType->value();
    // 大文件自动检测阈值固定为 300MB，避免复用 MaxDist 控件引起单位混淆（kb vs MB）。
    const double thresholdMB = 300.0;
    ui->resultTextEdit->append(uiText("文件大小>300mb，启用大文件输出模式", "File size > 300MB enables large-file output mode"));
    ui->resultTextEdit->append(uiText("当前OutType=%1（仅控制输出类型）", "Current OutType=%1 (controls output type only)").arg(outType));
    
    for (const QString& vcf : vcfInputFiles) {
        QString outStatPath = QFileDialog::getSaveFileName(this, uiText("选择结果文件保存路径", "Select output result file"), QDir::homePath() + "/" + QFileInfo(vcf).completeBaseName() + ".stat.gz", tr("Stat Files (*.stat.gz);;All Files (*)"));
        if (outStatPath.isEmpty()) continue;
        
        QString outPrefix = outStatPath;
        if (outPrefix.endsWith(".stat.gz")) outPrefix.chop(QString(".stat.gz").length());
        else if (outPrefix.endsWith(".stat")) outPrefix.chop(QString(".stat").length());
        
        // 自动检测VCF大小（对.gz粗略估算3倍），超过阈值则使用拆分模式
        QFileInfo fi(vcf);
        double sizeMB = 0.0;
        if (fi.exists()) {
            sizeMB = fi.size() / (1024.0 * 1024.0);
            if (vcf.endsWith(".gz", Qt::CaseInsensitive)) {
                sizeMB *= 3.0;
            }
        }
        ui->resultTextEdit->append(uiText("文件 %1 估算大小：%2 MB", "Estimated file size for %1: %2 MB").arg(vcf).arg(QString::number(sizeMB, 'f', 2)));
        
        QString result;
        const bool autoLarge = sizeMB >= thresholdMB;
        if (autoLarge) {
            result = runLargeFilePopLDdecay(vcf, outPrefix, thresholdMB, maxDistKb, maf, het, miss, ehh, outType);
        } else {
            result = runPopLDdecay(vcf, outPrefix, maxDistKb, maf, het, miss, subpopFilePath, ehh, outType);
        }
        
        ui->resultTextEdit->append(uiText("分析完成：", "Analysis completed: ") + outStatPath);
        if (!result.isEmpty()) {
            ui->resultTextEdit->append(result);
        }
    }
}

void MainWindow::on_selectResultFiles_clicked()
{
    resultFiles = QFileDialog::getOpenFileNames(this, uiText("选择多个结果文件", "Select multiple result files"), "", tr("Stat Files (*.stat *.stat.gz);;All Files (*)"));
    if (!resultFiles.isEmpty()) {
        ui->resultTextEdit->append(uiText("已选择结果文件：\n", "Selected result files:\n") + resultFiles.join("\n"));
    }
}

void MainWindow::on_runGeneratePlot_clicked()
{
    if (resultFiles.isEmpty()) {
        QMessageBox::warning(this, uiText("提示", "Notice"), uiText("请先选择多个结果文件！", "Please select result files first."));
        return;
    }
    // 根据文件数量设置默认文件名
    QString defaultFileName = (resultFiles.size() > 1) ? "multi_LD_decay_plot.png" : "single_LD_decay_plot.png";
    QString savePicPath = QFileDialog::getSaveFileName(this, uiText("保存图片为", "Save plot as"), QDir::homePath() + "/" + defaultFileName, tr("PNG图片 (*.png);;所有文件 (*)"));
    if (savePicPath.isEmpty()) return;
    QString tempPrefix = QDir::toNativeSeparators(QDir::temp().absoluteFilePath("temp_multi_lddecay_" + QString::number(QDateTime::currentMSecsSinceEpoch())));
    QString pythonExe = "python";
    QString scriptPath = QCoreApplication::applicationDirPath() + "/plot_lddecay_multi.py";
    if (!QFile::exists(scriptPath)) {
        QMessageBox::warning(this, uiText("作图失败", "Plot failed"), uiText("未找到作图脚本 %1", "Plot script not found: %1").arg(scriptPath));
        return;
    }
    int bin1 = ui->spinBox_bin1->value();
    int bin2 = ui->spinBox_bin2->value();
    int breakN = ui->spinBox_break->value();
    int maxX = ui->spinBox_maxX->value();
    QProcess process;
    process.setWorkingDirectory(QDir::currentPath());
    QStringList arguments;
    arguments << scriptPath << tempPrefix << QString::number(bin1) << QString::number(bin2) << QString::number(breakN) << QString::number(maxX);
    arguments << "--lang" << (useEnglish ? "en" : "zh");
    for (const QString& file : resultFiles) arguments << file;
    process.start(pythonExe, arguments);
    if (!process.waitForFinished(-1)) {
        // 检查python是否安装
        QProcess checkPy;
        checkPy.start("python", QStringList() << "--version");
        checkPy.waitForFinished(2000);
        QString pyOut = checkPy.readAllStandardOutput() + checkPy.readAllStandardError();
        if (!pyOut.contains("Python")) {
            QMessageBox::warning(this, uiText("作图失败", "Plot failed"), uiText("未检测到Python环境，请先安装Python后再试！\n可到 https://www.python.org/ 下载并安装。", "Python was not detected. Please install Python first:\nhttps://www.python.org/"));
        } else {
            QMessageBox::warning(this, uiText("作图失败", "Plot failed"), uiText("plot_lddecay_multi.py 运行失败，错误信息：%1", "plot_lddecay_multi.py failed: %1").arg(QString(process.readAllStandardError())));
        }
        return;
    } else {
        // 获取Python脚本的输出信息
        QString pythonOutput = process.readAllStandardOutput();
        QString pythonError = process.readAllStandardError();
        QString localizedOutput = localizeScriptOutput(pythonOutput, useEnglish);
        ui->resultTextEdit->append(uiText("Python脚本输出：%1", "Python output: %1").arg(localizedOutput));
        if (!pythonError.isEmpty()) {
            QString localizedError = localizeScriptOutput(pythonError, useEnglish);
            ui->resultTextEdit->append(uiText("Python脚本错误：%1", "Python error: %1").arg(localizedError));
        }
        
        // 根据文件数量检查对应的输出文件
        QString outputPath = (resultFiles.size() > 1) ? 
            tempPrefix + "_multi_LD_decay_plot.png" : 
            tempPrefix + "_single_LD_decay_plot.png";
        QString pdfOutputPath = (resultFiles.size() > 1) ?
            tempPrefix + "_multi_LD_decay_plot.pdf" :
            tempPrefix + "_single_LD_decay_plot.pdf";
        QString binFile = (resultFiles.size() > 1) ?
            tempPrefix + "_multi_bin.txt" :
            tempPrefix + "_single_bin.txt";
        QThread::msleep(2000); // 增加等待时间到2秒
        ui->resultTextEdit->append(uiText("检查输出文件：%1", "Checking output file: %1").arg(outputPath));
        if (QFile::exists(outputPath)) {
            // 若目标已存在，先删除以避免 QFile::copy 失败
            if (QFile::exists(savePicPath)) {
                QFile::remove(savePicPath);
            }

            if (QFile::copy(outputPath, savePicPath)) {
                QFileInfo pngInfo(savePicPath);
                QString pdfSavePath = QDir(pngInfo.path()).filePath(pngInfo.completeBaseName() + ".pdf");
                QString dataSavePath = QDir(pngInfo.path()).filePath(pngInfo.completeBaseName() + "_bin.txt");
                bool pdfCopied = false;
                bool dataCopied = false;
                if (QFile::exists(pdfOutputPath)) {
                    if (QFile::exists(pdfSavePath)) {
                        QFile::remove(pdfSavePath);
                    }
                    pdfCopied = QFile::copy(pdfOutputPath, pdfSavePath);
                }
                if (QFile::exists(binFile)) {
                    if (QFile::exists(dataSavePath)) {
                        QFile::remove(dataSavePath);
                    }
                    dataCopied = QFile::copy(binFile, dataSavePath);
                }

                QString message = (resultFiles.size() > 1) ?
                    uiText("多群体对比图已保存到：%1", "Multi-population plot saved to: %1").arg(savePicPath) :
                    uiText("单群体图已保存到：%1", "Single-population plot saved to: %1").arg(savePicPath);
                if (pdfCopied) {
                    message += uiText("\n同名PDF已保存到：%1", "\nPDF saved to: %1").arg(pdfSavePath);
                } else {
                    message += uiText("\n提示：未找到或未能保存PDF文件。", "\nNote: PDF not found or failed to save.");
                }
                if (dataCopied) {
                    message += uiText("\n绘图数据文件已保存到：%1", "\nPlot data file saved to: %1").arg(dataSavePath);
                } else {
                    message += uiText("\n提示：未找到或未能保存绘图数据文件。", "\nNote: Plot data file not found or failed to save.");
                }
                QMessageBox::information(this, uiText("作图完成", "Plot completed"), message);
            } else {
                QMessageBox::warning(this, uiText("作图失败", "Plot failed"), uiText("图片生成但保存失败：%1", "Plot was generated but failed to save: %1").arg(savePicPath));
            }
        } else {
            // 查找bin处理后的中间文件
            ui->resultTextEdit->append(uiText("图片文件不存在，检查数据文件：%1", "Plot image not found, checking data file: %1").arg(binFile));
            if (QFile::exists(binFile)) {
                QFile file(binFile);
                if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
                    QString content = file.readAll();
                    file.close();
                    ui->resultTextEdit->append(uiText("未能生成图片，但已生成分箱后的数据文件：%1\n你可以用Excel打开该文件，选择两列作图。\n内容预览：\n", "Plot was not generated, but binned data exists: %1\nYou can open it in Excel and draw from two columns.\nPreview:\n").arg(binFile) + content.left(1000));
                } else {
                    ui->resultTextEdit->append(uiText("未能生成图片，且无法读取分箱数据文件：%1", "Plot was not generated and binned data file cannot be read: %1").arg(binFile));
                }
            } else {
                ui->resultTextEdit->append(uiText("程序执行完成但未找到输出图片，也未找到分箱数据文件：%1", "Execution finished but neither plot image nor binned data file was found: %1").arg(binFile));
            }
            QMessageBox::warning(this, uiText("作图失败", "Plot failed"), uiText("程序执行完成但未找到输出图片：%1\n如未安装Python或matplotlib，请先安装。\n如有分箱数据文件，可用Excel作图。\n", "Execution finished but output image was not found: %1\nPlease install Python/matplotlib if missing.\nIf binned data exists, you can plot in Excel.\n").arg(outputPath));
        }
    }
}

QString MainWindow::runLargeFilePopLDdecay(const QString& vcfFile,
                                           const QString& outPrefix,
                                           double minSizeMB,
                                           int maxDistKb,
                                           double maf,
                                           double het,
                                           double miss,
                                           const QString& ehh,
                                           int outType)
{
    QString pythonExe = "python";
    // 递归向上查找脚本（应用目录与当前目录为起点，各向上最多6级）
    const QString appDir = QCoreApplication::applicationDirPath();
    const QString curDir = QDir::currentPath();
    QStringList tried;
    auto tryAppend = [&](const QString& base){
        QString p1 = QDir::cleanPath(base + "/split_large_vcf.py");
        QString p2 = QDir::cleanPath(base + "/src/split_large_vcf.py");
        tried << p1 << p2;
    };
    QStringList bases;
    bases << appDir << curDir;
    // 向上6级
    for (const QString& b0 : QList<QString>{appDir, curDir}) {
        QString b = b0;
        for (int i = 0; i < 6; ++i) {
            bases << b;
            b = QDir(b).absoluteFilePath("..");
        }
    }
    // 去重
    bases.removeDuplicates();
    for (const QString& base : bases) {
        tryAppend(base);
    }
    QString scriptPath;
    for (const QString& c : tried) {
        QFileInfo fi(c);
        if (fi.exists()) { scriptPath = fi.canonicalFilePath(); break; }
    }
    if (scriptPath.isEmpty()) {
        QString msg = uiText("错误：未找到大文件拆分脚本。已尝试路径：\n%1", "Error: large-file split script not found. Tried paths:\n%1")
            .arg(tried.join("\n"));
        ui->resultTextEdit->append(msg);
        return msg;
    }
    ui->resultTextEdit->append(uiText("使用脚本路径：%1", "Using script path: %1").arg(scriptPath));
    
    ui->resultTextEdit->append(uiText("开始大文件处理模式...", "Starting large-file mode..."));
    ui->resultTextEdit->append(uiText("VCF文件：%1", "VCF file: %1").arg(vcfFile));
    ui->resultTextEdit->append(uiText("最小拆分大小：%1 MB", "Split threshold: %1 MB").arg(minSizeMB));
    
    QProcess process;
    process.setWorkingDirectory(QDir::currentPath());
    QStringList arguments;
    arguments << scriptPath << vcfFile << outPrefix;
    arguments << "--maxdist" << QString::number(maxDistKb);
    arguments << "--maf" << QString::number(maf, 'g', 10);
    arguments << "--het" << QString::number(het, 'g', 10);
    arguments << "--miss" << QString::number(miss, 'g', 10);
    arguments << "--outtype" << QString::number(outType);
    arguments << "--lang" << (useEnglish ? "en" : "zh");
    if (!subpopFilePath.trimmed().isEmpty()) {
        arguments << "--subpop" << subpopFilePath;
        ui->resultTextEdit->append(uiText("使用样本列表文件：%1", "Using sample list file: %1").arg(subpopFilePath));
    }
    if (!ehh.isEmpty()) {
        arguments << "--ehh" << ehh;
    }

    // 查找并传递 PopLDdecay 可执行文件路径（若找到）
    QStringList exeCandidates;
    const QString appDir2 = QCoreApplication::applicationDirPath();
    const QString curDir2 = QDir::currentPath();
#ifdef Q_OS_WIN
    // 实际构建输出为 PopLDdecayGUI_run.exe，优先查找
    QStringList exeNames; exeNames << "PopLDdecayGUI_run.exe" << "PopLDdecay.exe" << "PopLDdecayGUI.exe";
#else
    QStringList exeNames; exeNames << "PopLDdecay";
#endif
    for (const QString &exeName : exeNames) {
        exeCandidates << QDir::cleanPath(appDir2 + "/" + exeName);
        exeCandidates << QDir::cleanPath(appDir2 + "/bin/" + exeName);
        exeCandidates << QDir::cleanPath(appDir2 + "/../bin/" + exeName);
        exeCandidates << QDir::cleanPath(curDir2 + "/" + exeName);
        exeCandidates << QDir::cleanPath(curDir2 + "/bin/" + exeName);
    }
    QString selectedExePath;
    for (const QString& cand : exeCandidates) {
        if (QFile::exists(cand)) { selectedExePath = cand; break; }
    }
    // 若检测到是 GUI 可执行，则仍然传递该路径，拆分脚本会自动以 --cli-run 模式调用
#ifdef Q_OS_WIN
    QString exeBase = QFileInfo(selectedExePath).fileName().toLower();
    if (!selectedExePath.isEmpty() && (exeBase == "poplddecaygui.exe" || exeBase == "poplddecaygui_run.exe")) {
        ui->resultTextEdit->append(uiText("检测到GUI可执行，将以命令行模式运行：%1", "GUI executable detected, will run in CLI mode: %1").arg(selectedExePath));
    }
#endif
    if (!selectedExePath.isEmpty()) {
        ui->resultTextEdit->append(uiText("使用PopLDdecay路径：%1", "Using PopLDdecay path: %1").arg(selectedExePath));
        arguments << "--poplddecay-exe" << selectedExePath;
    }
    
    process.setProcessChannelMode(QProcess::MergedChannels);
    // 强制Python无缓冲输出，便于实时日志
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONUNBUFFERED", "1");
    process.setProcessEnvironment(env);
    process.start(pythonExe, arguments);
    
    // 非阻塞等待，保持界面响应
    const int kSliceMs = 200; // 每次等待200ms
    int waitedMs = 0;
    int maxWaitMs = 24 * 60 * 60 * 1000; // 最多等待24小时，基本无限
    while (!process.waitForFinished(kSliceMs)) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, kSliceMs);
        waitedMs += kSliceMs;
        // 周期性读取输出，避免缓冲区阻塞
        const QString chunk = process.readAllStandardOutput();
        if (!chunk.isEmpty()) {
            const QString localizedChunk = localizeScriptOutput(chunk, useEnglish);
            if (!localizedChunk.isEmpty()) {
                ui->resultTextEdit->append(localizedChunk);
            }
        }
        if (waitedMs >= maxWaitMs) {
            process.kill();
            ui->resultTextEdit->append(uiText("超时终止拆分脚本", "Split script terminated due to timeout"));
            break;
        }
    }
    
    if (process.state() != QProcess::NotRunning && process.exitStatus() != QProcess::NormalExit) {
        // 检查python是否安装
        QProcess checkPy;
        checkPy.start("python", QStringList() << "--version");
        checkPy.waitForFinished(2000);
        QString pyOut = checkPy.readAllStandardOutput() + checkPy.readAllStandardError();
        if (!pyOut.contains("Python")) {
            return uiText("错误：未检测到Python环境，请先安装Python后再试！\n可到 https://www.python.org/ 下载并安装。", "Error: Python was not detected. Please install Python first:\nhttps://www.python.org/");
        } else {
            return uiText("错误：split_large_vcf.py 运行失败，错误信息：%1", "Error: split_large_vcf.py failed: %1").arg(QString(process.readAllStandardError()));
        }
    }
    
    QString pythonOutput = process.readAllStandardOutput();
    QString pythonError = process.readAllStandardError();
    
    QString localizedOutput = localizeScriptOutput(pythonOutput, useEnglish);
    ui->resultTextEdit->append(uiText("Python脚本输出：%1", "Python output: %1").arg(localizedOutput));
    if (!pythonError.isEmpty()) {
        QString localizedError = localizeScriptOutput(pythonError, useEnglish);
        ui->resultTextEdit->append(uiText("Python脚本错误：%1", "Python error: %1").arg(localizedError));
    }
    
    // 检查输出文件是否生成
    QString expectedOutput = outPrefix + ".stat.gz";
    if (QFile::exists(expectedOutput)) {
        ui->resultTextEdit->append(uiText("大文件处理完成：%1", "Large-file processing completed: %1").arg(expectedOutput));
        return uiText("大文件处理成功完成", "Large-file processing completed successfully");
    } else {
        return uiText("警告：大文件处理完成但未找到输出文件：%1", "Warning: large-file processing finished but output file was not found: %1").arg(expectedOutput);
    }
}


void MainWindow::on_helpButton_clicked()
{
    QString helpTextZh =
        "【PopLDdecay GUI 使用说明】\n\n"
        "1. 生成结果文件：\n"
        "   - 点击'选择VCF文件（可多选）'按钮，选择一个或多个VCF或VCF.GZ格式的基因型文件。\n"
        "   - 点击'选择样本列表文件'按钮，选择一个包含样本名称的txt文件（可选）。\n"
        "   - OutType参数仅支持1或2，并按所选值传导至PopLDdecay主程序。\n"
        "   - 点击'生成结果文件'按钮，依次为每个VCF文件选择输出路径，程序将自动生成分析结果文件。\n\n"
        "2. 生成结果图片：\n"
        "   - 点击'选择多个结果文件'按钮，选择多个.stat或.stat.gz分析结果文件。\n"
        "   - 设置bin1/bin2与break参数：Dist < break 使用bin1，Dist >= break 使用bin2进行分箱。\n"
        "   - 点击'生成结果图片'按钮，选择输出图片路径，程序将自动保存PNG图片，并同步导出同名PDF和分箱数据文件（*_bin.txt）。\n\n"
        "3. 过滤参数与基因型过滤：\n"
        "   - 在右侧栏设置MaxDist、MAF、Het、Miss、EHH、OutType等过滤参数。\n"
        "   - MaxDist始终用于设置分析的最大SNP距离，单位为kb，默认300。\n"
        "   - MAF、Het、Miss 等参数在点击「生成结果文件」时由主程序使用，参与基因型过滤与计算；界面上的「基因型过滤」为说明标识，无独立操作。\n\n"
        "4. 大文件处理模式：\n"
        "   - 适用于内存较小的Windows机器处理大型VCF文件。\n"
        "   - 文件大小>300mb，启用大文件输出模式。\n"
        "   - 自动检测大于指定大小（默认300MB）的文件并启用拆分处理（该阈值固定，不与MaxDist共用）。\n"
        "   - 拆分脚本会将VCF主体按约300MB（可通过--block-mb调整）切分为多个block块。\n"
        "   - 拆分脚本内部使用多进程并行运行PopLDdecay，充分利用多核CPU。\n"
        "   - 每个分块计算完成后自动删除临时VCF分块文件，节省硬盘空间。\n"
        "   - 最终自动合并所有分块的.stat.gz为一个结果文件。\n"
        "   - 需要安装Python环境支持。\n\n"
        "5. 结果与提示：\n"
        "   - 所有分析和作图结果、提示信息会显示在主界面下方的文本框中。\n\n"
        "如有疑问请联系开发者。";
    QString helpTextEn =
        "[PopLDdecay GUI Guide]\n\n"
        "1. Generate result files:\n"
        "   - Click 'Select VCF Files' to choose one or more VCF/VCF.GZ files.\n"
        "   - Click 'Select Sample List File' to choose a txt sample list (optional).\n"
        "   - OutType supports only 1 or 2 and is passed through to PopLDdecay.\n"
        "   - Click 'Generate Result Files' and choose output path(s).\n\n"
        "2. Generate plots:\n"
        "   - Click 'Select Multiple Result Files' and choose .stat/.stat.gz files.\n"
        "   - Set bin1/bin2 with break: Dist < break uses bin1; Dist >= break uses bin2.\n"
        "   - Click 'Generate Plot' to export PNG/PDF and *_bin.txt.\n\n"
        "3. Filter parameters and genotype filter:\n"
        "   - Set MaxDist, MAF, Het, Miss, EHH, OutType on the right panel.\n"
        "   - MaxDist is always the maximum SNP distance in kb.\n"
        "   - MAF, Het, Miss, etc. are used by the main program when you click Generate Result Files. The 'Genotype Filter' banner is informational only (not clickable).\n\n"
        "4. Large-file mode:\n"
        "   - Suitable for very large VCF files on low-memory machines.\n"
        "   - File size > 300MB enables large-file output mode.\n"
        "   - Files larger than 300MB are split and processed in parallel.\n"
        "   - Temporary split files are removed automatically.\n\n"
        "5. Logs:\n"
        "   - All processing messages appear in the bottom log panel.\n\n"
        "Contact developer if needed.";
    QMessageBox::information(this, uiText("帮助", "Help"), useEnglish ? helpTextEn : helpTextZh);
}

void MainWindow::on_languageButton_clicked()
{
    useEnglish = !useEnglish;
    applyLanguage();
    ui->resultTextEdit->append(uiText("语言已切换为中文。", "Language switched to English."));
}
