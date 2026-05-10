/*
 * Copyright (c) 2026 BGI-Shenzhen
 * Licensed under the MIT License. See LICENSE file for details.
 */
#include "CommFun.h"

// ����??...

void split3(const std::string& str, std::vector<const char*>& tokens, std::vector<std::string> & inf , int VecSizeNum)
{
    std::string::size_type lastPos = 0;
    std::string::size_type pos =1;
    const char* strPtr = str.c_str();

    tokens[0] = (strPtr + lastPos);
    lastPos = str.find('\t', pos);
    inf[0]=str.substr(0,lastPos);

    pos = lastPos + 1;
    tokens[1] = (strPtr + pos);
    lastPos = str.find('\t', pos);
    inf[1]=str.substr(pos,lastPos-pos);

    pos = lastPos + 1;
    tokens[2] = (strPtr + pos);
    lastPos = str.find('\t', pos);

    pos = lastPos + 1;
    tokens[3] = (strPtr + pos);
    lastPos = str.find('\t', pos);
    inf[3]=str.substr(pos,lastPos-pos);

    pos = lastPos + 1;
    tokens[4] = (strPtr + pos);
    lastPos = str.find('\t', pos);
    inf[4]=str.substr(pos,lastPos-pos);

    for (int kkk = 5; kkk < VecSizeNum; kkk++)
    {
        pos = lastPos + 1;
        tokens[kkk] = (strPtr + pos);
        lastPos = str.find('\t', pos);
    }
}