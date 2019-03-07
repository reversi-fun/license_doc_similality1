import os
import urllib.request
from bs4 import BeautifulSoup
import re
import json
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
import html5lib # for BeautifulSoup parser

encode_detector = UniversalDetector()
license_metaData = {}
if not os.path.isfile('./config/OSI-licenses-full.json'): 
  try:
    with urllib.request.urlopen('https://opensource.org/licenses/alphabetical') as res:
        body = res.read()
    encode_detector.reset()
    encode_detector.feed( body)
    if encode_detector.done:
        encode_detector.close()
        raw_doc =  body.decode(encode_detector.result['encoding'], errors='ignore' ) # .encode('utf-8', 'ignore')
    else:
        encode_detector.close()
        raw_doc =  body.decode('utf-8', errors='ignore')
    for licLink, licFullName,licShortName in re.findall(r"<li><a href=\"(\/licenses\/[^\"]+)\"\s*>\s*(?:[^\/]+\/)?([^\(\/<]+)(?:\(([^\)<]+)\))?<\/a>",  raw_doc):
        if len(licShortName) <= 0:
            licShortName = licLink[10:]
        license_metaData[licFullName.strip()] = {'id': licShortName , 'url': 'https://opensource.org' + licLink }
    with open('./config/OSI-licenses-full.json', 'w') as outfile:
      json.dump(license_metaData, outfile, ensure_ascii=False, indent=4, sort_keys=True, separators=(',', ': '))
  except urllib.error.HTTPError as err:
    print( 'licenses.json get failed', err)
    exit(1)
  except urllib.error.URLError as err:
    print( 'licenses.json get failed', err)
    exit(1)
else:
    f = open("./config/OSI-licenses-full.json", "r")
    # jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
    license_metaData = json.load(f)
    # ファイルを閉じる
    f.close()

for licName,licMetaData in license_metaData.items():
    lic_count = 0
    url = licMetaData['url']
    req = urllib.request.Request(url)
    try:
                    with urllib.request.urlopen(req) as res:
                        body = res.read()
                        contentType = (res.info().get('Content-Type', ''))
                    encode_detector.reset()
                    encode_detector.feed( body)
                    if encode_detector.done:
                        encode_detector.close()
                        raw_doc =  body.decode(encode_detector.result['encoding'], errors='ignore' ) # .encode('utf-8', 'ignore')
                    else:
                        encode_detector.close()
                        raw_doc =  body.decode('utf-8', errors='ignore')
                    try:
                        soup = BeautifulSoup(raw_doc, 'html5lib')
                        # kill all script and style elements
                        for script in soup(["script", "style", "noscript","h1", "h2",  "hr", "em", "input", "button", "aside", "form", "label", "a", "div[class=\"license\"]"]):
                                script.extract()    # rip it out
                        raw_doc =  re.sub("[\\s\\n]+(?:SPDX short identifier:[^\\n]*)?\\n","\n",soup.find('div', id="page" ).get_text())
                        licSuffix = ".txt"
                    finally:
                        pass 
                    print(licName + licSuffix ,contentType, url) 
                    f = open('./OSI_texts/' + licName + licSuffix ,  "w", encoding='utf-8')
                    f.write(raw_doc)
                    f.close()
                    lic_count = lic_count  + 1
    except urllib.error.HTTPError as err:
                    print( licName, url, err.code)
    except urllib.error.URLError as err:
                    print( licName, url, err.reason)
    if  lic_count <= 0:
        print(licName, '** no text found **')

  