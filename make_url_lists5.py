# programIDに対するURLの一覧を作成する
# SPDXのshort nameとFullName とsee alsoもマージする
import os,io
import csv
import glob
import urllib.request
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
import html5lib # for BeautifulSoup parser
import socket
from bs4 import BeautifulSoup
import json
import csv

# 以下は、ライセンス名の　名寄せ用
from licenses_names import load_license_alias  # current module
from licenses_names import save_license_alias  # current module

license_alias = load_license_alias()

f = open("license-list-data-master/json/licenses.json", "r", encoding="utf-8" )
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
f.close()   # ファイルを閉じる
if 'licenses'  in license_metaData:
    for licInfo in license_metaData['licenses']:
        licId = 'spdx/' + licInfo['licenseId']
        # license_alias[licInfo['name'].lower()] = licId
        if 'seeAlso' in licInfo:
            for seeAlso in licInfo['seeAlso']:
               license_alias[seeAlso.strip()] = licId # .lowerにするとhttp error 404 notfound

f = open("license-list-data-master/json/exceptions.json", "r", encoding="utf-8")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
f.close()   # ファイルを閉じる
if 'licenses'  in license_metaData:
    for licInfo in license_metaData['licenses']:
        licId = 'spdx/' + licInfo['licenseExceptionId']
        # license_alias[licInfo['name'].lower()] = licId
        if 'seeAlso' in licInfo:
            for seeAlso in licInfo['seeAlso']:
               license_alias[seeAlso.strip()] = licId

f = open("config/FSF-licenses-full.json", "r", encoding="utf-8")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
f.close()   # ファイルを閉じる
if 'licenses'  in license_metaData:
    for licName, licInfo in license_metaData['licenses'].items():
        licId = 'FSF/' +licName
        # license_alias[licInfo['name'].lower()] = licId
        if 'uris' in licInfo:
            for seeAlso in licInfo['uris']:
               license_alias[seeAlso.strip()] = licId

f = open("config/OSI-licenses-full.json", "r", encoding="utf-8")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
f.close()   # ファイルを閉じる
if isinstance(license_metaData,dict):
    for licName, licInfo in license_metaData.items():
        licId = 'OSI/' +licName
        if 'url' in licInfo:
               license_alias[licInfo['url'].strip()] = licId

licShortName2URLs = {}
encode_detector = UniversalDetector()
for corpus_dir, prefix in [['license-list-data-master/text', 'spdx'],['FSF_texts', 'FSF'], ['OSI_texts', 'OSI'],['Considered_texts','Considered'], ['Approved_texts','Approved']]:
    for filename in glob.glob(corpus_dir + '/**', recursive=True):
        if filename.endswith('.txt'):
            licName =  filename[len(corpus_dir) + 1 :-4]
        else:
            licName =  filename[len(corpus_dir) + 1:]
        licShortName2URLs[prefix + '/' + licName] = []

for lic_alias, lic_name1 in license_alias.items():
        lic_name2 = license_alias.get(lic_name1.lower(), lic_name1)
        if  lic_name2 != lic_name1:
            license_alias[lic_alias] = lic_name2
        if lic_name2 not in  licShortName2URLs:
            print('WARNING: licence name not in sample dir:' + lic_name2.encode('cp932','ignore') + ', url='  + lic_alias.encode('cp932','ignore')) # 先頭で纏めて出力する
            licShortName2URLs[lic_name2] = [] # appendの為、空listを作る。

save_license_alias(license_alias) # update config/lic_alias.csv

for licName in [n for n in licShortName2URLs.keys()]: # RuntimeError: dictionary changed size during iteration　を避ける
    try:
        c = licName.encode('cp932')
    except UnicodeEncodeError as err:
        print(err,licName.encode('cp932','ignore'))
        licShortName2URLs.pop(licName)

print(licShortName2URLs.keys())

for lic_alias, lic_name1 in license_alias.items():
    if lic_alias.startswith('http://') or lic_alias.startswith('https://'):
        # lic_name2 = license_alias.get(lic_name1.lower(), lic_name1)
        curUrl = lic_alias
        try:
            print('try http access',lic_name1,curUrl)
            with urllib.request.urlopen(curUrl, timeout=6) as res:
                body = res.read()
                encode_detector.reset()
                encode_detector.feed( body)
                if encode_detector.done:
                    encode_detector.close()
                    raw_doc =  body.decode(encode_detector.result['encoding'], errors='ignore' ) # .encode('utf-8', 'ignore')
                else:
                    encode_detector.close()
                raw_doc =  body.decode('utf-8', errors='ignore')
                if len(raw_doc) > 8:
                    if lic_name1 not in  licShortName2URLs:
                        licShortName2URLs[lic_name1] = [] # appendの為、空listを作る。
                    licShortName2URLs[lic_name1].append(curUrl)
        except socket.timeout:
            print('WARNING timeout URL=' + curUrl)
            pass
        except urllib.error.HTTPError as err:
            print('WARNING HTTPError URL=' + curUrl)
            pass
        except urllib.error.URLError as err:
            print('WARNING URLError URL=' + curUrl)
            pass

# ソートする
# license name spaceのソート順
licenseSortOrder={
'//spdx.org/licenses': 1,
'//opensource.org/': 2,
'//www.gnu.org/':3,
'//directory.fsf.org/wiki':4,
'//fedoraproject.org/wiki/licensing':5,
'//www.r-project.org':6,
'':7}
for licName, curURLS in licShortName2URLs.items():
    licShortName2URLs[licName] = sorted( list(set(curURLS)), key=lambda x: (licenseSortOrder[ (list(filter(lambda infix: infix in x,licenseSortOrder)) + [''])[0]], len(x), x))

with open('./config/licenseName2URLl.json', 'w', encoding="utf_8_sig") as outfile:
      json.dump(licShortName2URLs, outfile, ensure_ascii=False, indent=4, sort_keys=True, separators=(',', ': '))
