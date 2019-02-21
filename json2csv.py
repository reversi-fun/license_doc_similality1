
import os
import csv
import glob
import json

if  os.path.isfile("./config/license_alias_updated.json"):
    f = open("./config/license_alias_updated.json", "r",  encoding="utf-8")
    license_alias  = json.load(f)
    f.close()
else:
    license_alias = {}

with open("./config/license_alias_updated.csv", 'w', encoding="utf_8_sig") as f:
    writer = csv.writer(f,quoting=csv.QUOTE_NONNUMERIC, delimiter=',',  lineterminator='\n') # 改行コード（\n）を指定しておく
    writer.writerow(['aliasNames', 'shortName'])
    for aliasName, shortName in license_alias.items():
        writer.writerow([aliasName, shortName])
