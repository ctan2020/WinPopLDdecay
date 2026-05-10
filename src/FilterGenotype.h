/*
 * Copyright (c) 2026 BGI-Shenzhen
 * Licensed under the MIT License. See LICENSE file for details.
 */
#ifndef FilterGenotype_H_
#define FilterGenotype_H_

#include "HeadIN.h"
#include <iostream>

using namespace std ;

/*
int  print_usage_18()
{
	cout <<""
		"\n"
		"\tUsage: FilterGeno -InPut <in.genotype> -OutPut <out.genotype>\n"
		"\n"
		"\t\t-InPut     <str>   InPut file of genotype\n"
		"\t\t-OutPut    <str>   OutPut the filter file\n"
		"\n"
		"\t\t-Het      <float>  the max ratio of het allele[0.88]\n"
		"\t\t-Miss     <float>  the max ratio of miss allele[0.88]\n"
		"\t\t-MAF      <float>  filter the low minor allele frequency[0.0]\n"
		"\t\t-Cut3base          Filter position with 3 allele[off]\n"
		"\t\t-help              show this help\n" 
		"\n";
	return 1;
}
*/

int parse_cmd_18(int argc, char **argv, Para_18 * para_18);
int Filter_genotype_main(int argc, char *argv[]);

#endif //FilterGenotype_H_
///////// swimming in the sky and flying in the sea ////////////
