/*
 * Copyright (c) 2026 BGI-Shenzhen
 * Licensed under the MIT License. See LICENSE file for details.
 */
#include "mainwindow.h"
#include "LD_Decay.h"

#include <QApplication>
#include <QString>
#include <QTextStream>
#include <QCoreApplication>
#include <QFileInfo>

static int runCliMode(int argc, char* argv[])
{
    // 简易解析：--cli-run --invcf <file> --outstat <prefix>
    QString invcf;
    QString outstat;
    int maxDistKb = 300;
    double maf = 0.005;
    double het = 0.88;
    double miss = 0.25;
    QString subpop;
    QString ehh;
    int outType = 1;
    for (int i = 1; i < argc; ++i) {
        QString arg = QString::fromLocal8Bit(argv[i]);
        if (arg.compare("--invcf", Qt::CaseInsensitive) == 0 && i + 1 < argc) {
            invcf = QString::fromLocal8Bit(argv[++i]);
        } else if (arg.compare("--outstat", Qt::CaseInsensitive) == 0 && i + 1 < argc) {
            outstat = QString::fromLocal8Bit(argv[++i]);
        } else if ((arg.compare("--maxdist", Qt::CaseInsensitive) == 0 || arg.compare("-MaxDist", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            maxDistKb = QString::fromLocal8Bit(argv[++i]).toInt();
        } else if ((arg.compare("--maf", Qt::CaseInsensitive) == 0 || arg.compare("-MAF", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            maf = QString::fromLocal8Bit(argv[++i]).toDouble();
        } else if ((arg.compare("--het", Qt::CaseInsensitive) == 0 || arg.compare("-Het", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            het = QString::fromLocal8Bit(argv[++i]).toDouble();
        } else if ((arg.compare("--miss", Qt::CaseInsensitive) == 0 || arg.compare("-Miss", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            miss = QString::fromLocal8Bit(argv[++i]).toDouble();
        } else if ((arg.compare("--subpop", Qt::CaseInsensitive) == 0 || arg.compare("-SubPop", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            subpop = QString::fromLocal8Bit(argv[++i]);
        } else if ((arg.compare("--ehh", Qt::CaseInsensitive) == 0 || arg.compare("-EHH", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            ehh = QString::fromLocal8Bit(argv[++i]);
        } else if ((arg.compare("--outtype", Qt::CaseInsensitive) == 0 || arg.compare("-OutType", Qt::CaseInsensitive) == 0) && i + 1 < argc) {
            outType = QString::fromLocal8Bit(argv[++i]).toInt();
        }
    }
    QTextStream out(stdout);
    if (invcf.isEmpty() || outstat.isEmpty()) {
        out << "Usage: PopLDdecayGUI --cli-run --invcf <vcf(.gz)> --outstat <out_prefix>\n";
        out.flush();
        return 2;
    }
    out << "CLI: running PopLDdecay on \n  VCF: " << invcf << "\n  OUT: " << outstat << "\n";
    out.flush();
    QString res = runPopLDdecay(invcf, outstat, maxDistKb, maf, het, miss, subpop, ehh, outType);
    if (!res.isEmpty()) {
        out << res << "\n";
        out.flush();
    }
    // 按约定返回0表示成功。runPopLDdecay内部会创建 <out_prefix>.stat.gz
    return 0;
}

int main(int argc, char *argv[])
{
    // 若检测到 --cli-run，则走命令行模式，无需GUI
    for (int i = 1; i < argc; ++i) {
        if (QString::fromLocal8Bit(argv[i]).compare("--cli-run", Qt::CaseInsensitive) == 0) {
            return runCliMode(argc, argv);
        }
    }

    QApplication a(argc, argv);
    MainWindow w;
    w.showMaximized();
    return a.exec();
}