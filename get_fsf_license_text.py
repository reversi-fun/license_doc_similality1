import urllib.request
import json
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
from bs4 import BeautifulSoup
import html5lib # for BeautifulSoup parser

encode_detector = UniversalDetector()
f = open("./config/FSF-licenses-full.json", "r")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
# ファイルを閉じる
f.close()
for licName,licMetaData in license_metaData['licenses'].items():
    lic_count = 0
    if (len(licMetaData.get('uris', [])) > 0):
        for url in licMetaData['uris']:
            if not url.startswith("https://www.gnu.org/licenses/license-list.html"):
                req = urllib.request.Request(url)
                try:
                    with urllib.request.urlopen(req) as res:
                        body = res.read()
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
                        for script in soup(["script", "style", "noscript","h1", "h2", "h3", "hr", "input", "button", "aside", "form", "label", "a"]):
                            script.extract()    # rip it out
                        raw_doc = soup.get_text()
                    finally:
                        pass 
                    print(licName,url) 
                    f = open('./FSF_texts/' + licName,  "w", encoding='utf-8')
                    f.write(raw_doc)
                    f.close()
                    lic_count = lic_count  + 1
                except urllib.error.HTTPError as err:
                    print( licName, url, err.code)
                except urllib.error.URLError as err:
                    print( licName, url, err.reason)
    if  lic_count <= 0:
        print(licName, '** no text found **')

  