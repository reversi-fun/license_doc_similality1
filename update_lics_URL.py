#coding: UTF-8

# update license URL column ny licenseName

import os
import io
import sys
import csv
import json
import re
from licenses_names import load_license_alias  # current module
from licenses_names import licName2Short  # current module

# 引数or実行環境の取得
if len(sys.argv) <= 1:
    sys.stderr.write("usage: python update_lic_url.py inputFile.csv \n")
    sys.exit(1)

inputFileName = os.path.abspath(sys.argv[1])
if not inputFileName.endswith('.csv'):
    sys.stderr.write("Invalid input file-type(CSV only) \n")
    sys.exit(1)

if not os.path.isfile(inputFileName):
    sys.stderr.write("Invalid input file \n")
    sys.exit(1)

toolDirName = os.path.dirname(__file__)
with open(os.path.join(toolDirName, "config/licenseName2URLl.json"), 'r', encoding="utf_8_sig") as f:
      licShortName2URLs = json.load(f)

outputFileName = inputFileName[0:-4] + '_updated.csv'
print('outpus file =' + outputFileName)

license_alias = load_license_alias()

with open(inputFileName, "r", encoding="utf_8_sig") as inFile:
    csvReader = csv.reader(inFile, delimiter=",", doublequote=True,
                           lineterminator="\r\n", quotechar='"', skipinitialspace=True)
    header = next(csvReader)  # 最初の一行をヘッダーとして取得
    licName_index = header.index("licenseName(s)")
    licURL_index = header.index("licenseURL(s)")
    with open(outputFileName, "w", encoding="utf_8_sig") as outFile:
        csvWriter = csv.writer(outFile, doublequote=True, quotechar='"', lineterminator="\n")
        csvWriter.writerow(header)
        for row in csvReader:
            licNames = list(filter(lambda x: len(x) > 0, re.split( r'\s*,?\s*[\r\n]\s*', row[licName_index])))
            licURLs = list(filter(lambda x: len(x) > 0, re.split(r'\s*,?\s*[\r\n]\s*', row[licURL_index])))
            licNames = licName2Short(license_alias, licNames, licURLs)
            licURLs = list(set(filter(lambda x: len(x) > 0,  licURLs +   [(licShortName2URLs[licName] + [''])[0] for licName in licNames if licName in licShortName2URLs] )))
            row[licName_index]= ",\n".join(licNames)
            row[licURL_index]= ",\n".join(licURLs)
            csvWriter.writerow(row) 
