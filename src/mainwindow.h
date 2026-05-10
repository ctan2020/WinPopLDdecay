/*
 * Copyright (c) 2026 BGI-Shenzhen
 * Licensed under the MIT License. See LICENSE file for details.
 */
#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QFileDialog>
#include <QMessageBox>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void on_helpButton_clicked();
    void on_selectVCFFiles_clicked();
    void on_selectSubpopFile_clicked();
    void on_runGenerateResult_clicked();
    void on_selectResultFiles_clicked();
    void on_runGeneratePlot_clicked();
    void on_languageButton_clicked();

private:
    QString uiText(const QString& zh, const QString& en) const;
    void applyLanguage();

    Ui::MainWindow *ui;
    QString inputFilePath;
    QStringList multiInputFiles;
    QStringList vcfInputFiles;
    QString subpopFilePath;
    QStringList resultFiles;
    bool useEnglish = false;
    
    // 大文件处理函数
    QString runLargeFilePopLDdecay(const QString& vcfFile,
                                   const QString& outPrefix,
                                   double minSizeMB,
                                   int maxDistKb,
                                   double maf,
                                   double het,
                                   double miss,
                                   const QString& ehh,
                                   int outType);
};

#endif // MAINWINDOW_H 
