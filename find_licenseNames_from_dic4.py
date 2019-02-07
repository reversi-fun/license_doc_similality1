#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os
import sys
import gensim
import glob
import fileinput
import re
import csv
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function

## カスタマイズ可能項目の設定
topN = 3 # 最大出力するライセンス名の個数
similarl_low = 0.5 # model.docvecs.most_similarの類似度の下限
similarl_cutoff = 0.95 # [spdx/BSD-2-Clauseとspdx/BSD-3-Clause-Clear]が候補になった場合、類似度の比率で、カットオフする閾値
projectName_pattern = re.compile('[\\/\\\\]((?:(?![_-][vVrR]e?r?v?\\d|\\d\\.|\\.jar|\\.war|\\.zip|META-INF)[\\w\\d\\.#@+_-])+)(?:(?:[_-][vV]e?r?|[_-][rR]e?v?|(?=\\d+\\.))(\\d+(?:\\.(?!jar|war|zip)[\\w\\d+_-]+)*))?(?:\\.jar#?|\\.war#?|\\.zip#?|#)(?=[\\/\\\\])|(?:^|(?:^|[\/\\\\])(node_modules|pkgs|site-packages|Library|lib|vendor)[\/\\\\])((?!META-INF|node_modules|pkgs|site-packages|Library|lib|vendor)(?:(?![_-][vVrR]e?r?v?\\d|\\d\\.)[\\w\\d\\.#@+_-])+)(?:(?:[_-][vV]e?r?|[_-][rR]e?v?|(?=\\d+\\.))(\\d+(?:\\.\\d+)*))?(?=[\\/\\\\])|META-INF\\\\maven\\\\([^\\\\]+)\\\\([^\\\\]+)\\\\(?:[^\\\\]+$)')

## 引数or実行環境の取得
if len(sys.argv) <= 2:
    sys.stderr.write("usage: python find_licenseNames_from_dic4.py inputDir outputDir \n")
    sys.exit(1)

inDirName = os.path.abspath(sys.argv[1])
outputDirName = sys.argv[2].replace('\\', '/')
outputFileName =  outputDirName + "/filePattern2License.csv"
toolFileName = sys.argv[0]
if len(toolFileName) <= 0:
    toolDirName = os.path.dirname(os.getcwd())
elif os.path.isdir(toolFileName):
    toolDirName = toolFileName
else:
    toolDirName = os.path.dirname(toolFileName)

# license name spaceのソート順
licenseSortOrder={'spdx': 1, 'FSF': 1, 'Approved': 2 , 'research': 3, '': 4}

print("input dir=" + inDirName)
print("output file(license names for FilePath pattern)=" + outputFileName)

if not os.path.exists(outputDirName):
    os.makedirs(outputDirName)

outFile = open(outputFileName, "w", newline="\n", encoding="utf-8")
csvWriter = csv.writer(outFile, doublequote=True, quotechar='"')

# gensimで学習済みのデータ読み込み
model = gensim.models.doc2vec.Doc2Vec.load(os.path.join(toolDirName,'data/doc2vec.model'))
# ファイル毎のライセンス名を探して、csv出力する。
csvWriter.writerow(['identificationType','fileIdentifier','fileSize', 'projectsName','licenseName(s)','similarity(s)']) 
# encodingの検出ツールを使う。
encode_detector = UniversalDetector()
for filename in glob.glob(inDirName + "/**/*",  recursive=True):
      try:
          if  os.path.isfile(filename)  and (os.path.getsize(filename) < 2048000) and (os.path.splitext(filename)[1]  not in ['.bin', '.class', '.exe', '.dll', '.zip', '.jar', '.tz', '.properties']) and  any([licenseName in os.path.basename(filename) for licenseName in ['license','LICENSE', 'licence' , 'LICENCE', 'notice', 'NOTICE', 'nitify', 'NOTIFY',  'Notices', 'THIRD-PARTY', 'ThirdParty' ,'readme','copy','contribut',  'pom']]):
            encode_detector.reset()
            raw_doc = open(filename, 'rb').read()
            encode_detector.feed(raw_doc)
            if encode_detector.done:
                encode_detector.close()
                raw_doc = str(raw_doc, encoding = encode_detector.result['encoding'], errors='replace' ).encode('utf-8', 'replace')
            else:
                encode_detector.close()
                raw_doc = str(raw_doc, encoding = 'utf-8', errors='replace' )
            doc3 = gensim.parsing.preprocess_string(raw_doc)
            if len(doc3) > 4:
                new_doc_vec3 = model.infer_vector(doc3)
                similarl_licenses = [[licName,similal1] for licName,similal1 in  model.docvecs.most_similar([new_doc_vec3]) if (similal1>= similarl_low)]
                if len(similarl_licenses) > 1:
                    ccutoff_similarl = max([similal1 for licName,similal1 in similarl_licenses]) * similarl_cutoff
                    similarl_licenses = sorted([[licName,similal1] for licName,similal1 in similarl_licenses if similal1 >= ccutoff_similarl], key=lambda item: (licenseSortOrder[list(filter(lambda x: (x+ '/' ) in item[0], licenseSortOrder))[0]] , -item[1]))[0:topN]
                if len(similarl_licenses) > 0:
                    filePattern = (filename[len(inDirName)+1:] if filename[0: len(inDirName)] == inDirName else filename )
                    projectGroup = '?'
                    projectName = ''
                    projectVersion = ''
                    for mached in re.finditer(projectName_pattern, filePattern):
                        if mached.group(1) != None:
                             projectName = mached.group(1)
                             projectVersion =  mached.group(2) if ( mached.group(2) != None) else ''
                        elif  mached.group(4) != None:
                            if mached.group(3) == 'node_modules':
                                projectGroup = '.'
                            else:
                                projectGroup = '?'
                            projectName = mached.group(4)
                            projectVersion =  mached.group(5) if ( mached.group(5) != None) else '0' # maven用のpom.xmlに転記した場合にsyntax errorにならないバージョン
                        elif  mached.group(6) != None:
                            projectGroup = mached.group(6)
                            projectName = mached.group(7)
                    csvWriter.writerow([
                      'pathSuffix',
                      filePattern.replace('/', '\\'),  #　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
                      os.path.getsize(filename),  # patternType=fileNameの場合、ファイルサイズの一致でverify可能にする
                        projectGroup + '--' + projectName + '--' + projectVersion, # mavenリポジトリ風に、groupId--artifactID--version
                       "\n".join([licName for licName,similal1 in similarl_licenses]),
                       ",\n".join(['{:3.5f}'.format(similal1) for licName,similal1 in similarl_licenses])
                       ]) 
      except UnicodeDecodeError:
            print("SKIP " , os.path.splitext(filename))

outFile.close
