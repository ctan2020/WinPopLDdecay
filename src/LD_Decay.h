/*
 * Copyright (c) 2026 BGI-Shenzhen
 * Licensed under the MIT License. See LICENSE file for details.
 */
#ifndef LD_DECAY_H
#define LD_DECAY_H

#include <QString>

// ?? LDdecay???? GUI ??????
QString runPopLDdecay(const QString& vcfFile,
                      const QString& outPrefix,
                      int maxDistKb,
                      double maf,
                      double het,
                      double miss,
                      const QString& subPopFile,
                      const QString& ehh,
                      int outType);

#endif // LD_DECAY_H