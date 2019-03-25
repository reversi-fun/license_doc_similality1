import os
import urllib.request
from bs4 import BeautifulSoup
import re
import json
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
import html5lib # for BeautifulSoup parser

encode_detector = UniversalDetector()
license_metaData = {}
if not os.path.isfile('./config/calculate-Linux-licenses-full.json'): 
  try:
    with urllib.request.urlopen('https://www.calculate-linux.org/packages/licenses') as res:
        body = res.read()
    encode_detector.reset()
    encode_detector.feed( body)
    if encode_detector.done:
        encode_detector.close()
        raw_doc =  body.decode(encode_detector.result['encoding'], errors='ignore' ) # .encode('utf-8', 'ignore')
    else:
        encode_detector.close()
        raw_doc =  body.decode('utf-8', errors='ignore')
    print(raw_doc)
    for licLink,licShortName in re.findall(r"<a href=\"(\/packages\/licenses\/[^\"]+)\"\s+title=\"([^\"]+)\"",  raw_doc):
        # <a href="/packages/licenses/LGPL-2.1-with-linking-exception" title="LGPL-2.1-with-linking-exception">LGPL-2.1-with-linkin…</a>
        license_metaData[licShortName.strip()] = { 'url': 'https://www.calculate-linux.org' + licLink }
    with open('./config/calculate-Linux-licenses-full.json', 'w', encoding="utf_8_sig" ) as outfile:
        json.dump(license_metaData, outfile, ensure_ascii=False, indent=4, sort_keys=True, separators=(',', ': '))
  except urllib.error.HTTPError as err:
    print( 'licenses.json get failed', err)
    exit(1)
  except urllib.error.URLError as err:
    print( 'licenses.json get failed', err)
    exit(1)
else:
    f = open("./config/calculate-Linux-licenses-full.json", "r", encoding="utf_8_sig" )
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
                        # for script in soup(["script", "style", "noscript","h1",  "hr", "em", "input", "button", "aside", "form", "label", "a", "div[class=\"license\"]"]):
                        #         script.extract()    # rip it out
                        soap_doc = soup.find('pre') # find('div[class=\"portage_license\"]
                        if soap_doc:
                            raw_doc =  soap_doc.get_text()
                            licSuffix = ".txt"
                            print(licName + licSuffix ,contentType, url) 
                            f = open('./calculate-Linux_texts/' + licName + licSuffix ,  "w", encoding='utf_8')
                            f.write(raw_doc)
                            f.close()
                            lic_count = lic_count  + 1
                        else:
                           print('html5 parse error',licName,raw_doc)
                    finally:
                        pass 
    except urllib.error.HTTPError as err:
                    print( licName, url, err.code)
    except urllib.error.URLError as err:
                    print( licName, url, err.reason)
    if  lic_count <= 0:
        print(licName, '** no text found **')

  