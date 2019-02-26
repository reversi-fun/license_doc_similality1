#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os, io
import sys
import gensim
import glob
import fileinput
import re
import csv
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
# 以下はpom.xml読みこみ用
import xml
import xml.etree.ElementTree as ET 
# 以下はpackage.json読みこみ用
import json
# 以下は、ライセンス名の　名寄せ用
from classPathMatcher  import ClassPathMatcher # current module
from programId2license import ProgramId2License # current module

## カスタマイズ可能項目の設定
topN = 3 # 最大出力するライセンス名の個数
similarl_low = 0.63 # model.docvecs.most_similarの類似度の下限。 node_modules\escape-string-regexp\readme.mdの類似度より大きな値
similarl_cutoff = 0.95 # [spdx/BSD-2-Clauseとspdx/BSD-3-Clause-Clear]が候補になった場合、類似度の比率で、カットオフする閾値
projectArtifactId_pattern = re.compile('[\\/\\\\]((?:(?![_-][vVrR]e?r?v?\\d|\\d\\.|\\.jar|\\.war|\\.zip|META-INF)[\\w\\d\\.#@+_-])+)(?:(?:[_-][vV]e?r?|[_-][rR]e?v?|(?=\\d+\\.))(\\d+(?:\\.(?!jar|war|zip)[\\w\\d+_-]+)*))?(?:\\.jar#?|\\.war#?|\\.zip#?|#)(?=[\\/\\\\])|(?:^|(?:^|[\/\\\\])(node_modules|pkgs|site-packages|Library|lib|vendor)[\/\\\\])((?!META-INF|node_modules|pkgs|site-packages|Library|lib|vendor)(?:(?![_-][vVrR]e?r?v?\\d|\\d\\.)[\\w\\d\\.#@+_-])+)(?:(?:[_-][vV]e?r?|[_-][rR]e?v?|(?=\\d+\\.))(\\d+(?:\\.\\d+)*))?(?=[\\/\\\\])|META-INF\\\\maven\\\\([^\\\\]+)\\\\([^\\\\]+)\\\\(?:[^\\\\]+$)')

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
licenseSortOrder={'spdx': 1, 'ONI': 1, 'FSF': 1, 'Approved': 3 , 'research': 4, '': 5}

print("input dir=" + inDirName)
print("output file(license names for FilePath pattern)=" + outputFileName)

if not os.path.exists(outputDirName):
    os.makedirs(outputDirName)

# licenseの条文の類似性によって分類したライセンスの別名を読み込む
if  os.path.isfile(toolDirName + "/config/license_alias.csv"):
    with  io.open(toolDirName + "/config/license_alias.csv", "r",  encoding="utf_8_sig", errors='ignore') as f:
        f.readline()
        reader = csv.reader(f)
        license_alias = {}
        for aliasName, shortName in  reader:
            # TODO: aliasNameとshortNamealiasとは、1対多、または、多対多に、対応つけるよう、1セル内の複数行を読めたほうが良い。
            license_alias[aliasName.lower()] = shortName
        reader = None
else:
    print("not exist ./config/license_alias.csv")
    exit(1)

classPathMatcher1 = ClassPathMatcher()
programId2license =  ProgramId2License()

def licName2Short(licNames,licURLs):
    return sorted(list(set(
        [license_alias.get(aliasName.lower(),aliasName) for aliasName in licNames] +
        [license_alias[aliasName.lower()] for aliasName in licURLs if  aliasName.lower() in license_alias]
        )),
        key=lambda item: (licenseSortOrder[(list(filter(lambda x: (x+ '/' ) in item, licenseSortOrder)) + [''])[0] ] , item))

outFile = open(outputFileName, "w", newline="\n", encoding="utf-8")
csvWriter = csv.writer(outFile, doublequote=True, quotechar='"')

# gensimで学習済みのデータ読み込み
model = gensim.models.doc2vec.Doc2Vec.load(os.path.join(toolDirName,'data/doc2vec.model'))
# ファイル毎のライセンス名を探して、csv出力する。
csvWriter.writerow(['identificationType','fileIdentifier','fileSize', 'ArtifactId','similarity(s)','licenseName(s)', 'licenseURL(s)','auther(s)', 'relatedURL(s)','name', 'description']) 
# encodingの検出ツールを使う。
encode_detector = UniversalDetector()
for filename in glob.glob(inDirName + "/**/*",  recursive=True):
      try:
        if  os.path.isfile(filename)  and (os.path.getsize(filename) < 2048000):
          filePattern = (filename[len(inDirName)+1:] if filename[0: len(inDirName)] == inDirName else filename ).replace('/', '\\')
          if filename.endswith('pom.xml') or filename.endswith('.pom')  :
            projectGroup = '?'
            projectArtifactId = ''
            projectVersion = ''
            projectLicenseNames = []
            projectLicenseURLs = []
            projectAuthers = []
            projectRelatedURLs = []
            projectName = []
            projectDescription = []
            xmlDocTree  = ET.parse(filename)
            xmlDocRoot = xmlDocTree.getroot() #  <Element '{http://maven.apache.org/POM/4.0.0}project'
            pomNS =  xmlDocRoot.tag[0: -7] if len(xmlDocRoot.tag) > 6 else '' #  '{http://maven.apache.org/POM/4.0.0}'
            projectGroupEL = xmlDocRoot.find(pomNS + 'groupId')
            if projectGroupEL != None:
                    projectGroup = projectGroupEL.text
            else:
                    projectGroupEL = xmlDocRoot.find(pomNS + 'parent/' + pomNS + 'groupId')
                    if projectGroupEL != None:
                        projectGroup = projectGroupEL.text
            projectArtifactIdEL = xmlDocRoot.find(pomNS + 'artifactId')
            if projectArtifactIdEL != None:
                    projectArtifactId = projectArtifactIdEL.text
            else:
                    projectArtifactIdEL = xmlDocRoot.find(pomNS + 'parent/' + pomNS +'artifactId')
                    if projectArtifactIdEL != None:
                        projectArtifactId = projectArtifactIdEL.text
            projectVersionEL = xmlDocRoot.find(pomNS + 'version')
            if projectVersionEL != None:
                    projectVersion = projectVersionEL.text
            else:
                    projectVersionEL = xmlDocRoot.find(pomNS + 'parent/' + pomNS + 'version')
                    if projectVersionEL != None:
                        projectVersion = projectVersionEL.text
            for xml_project_license_element in xmlDocRoot.findall(pomNS + 'licenses/' + pomNS + 'license'):
                    project_lic_name_EL = xml_project_license_element.find(pomNS + 'name')
                    if project_lic_name_EL != None:
                         projectLicenseNames.append(project_lic_name_EL.text)
                    project_lic_url_EL = xml_project_license_element.find(pomNS + 'url')
                    if project_lic_url_EL != None:
                         projectLicenseURLs.append(project_lic_url_EL.text)
            for infoKey in ['developers/' + pomNS + 'developer', 'organization',  'contributors/' + pomNS + 'contributor']:
                    for project_authers_EL in xmlDocRoot.findall(pomNS + infoKey):
                        for itemKey in ['id',  'name',  'email', 'organization']:
                          project_auther_EL = project_authers_EL.find(pomNS + itemKey)
                          if project_auther_EL != None:
                            if project_auther_EL.text != None:
                              projectAuthers.append(project_auther_EL.text)
                        for itemKey in ['url']:
                          project_auther_EL = project_authers_EL.find(pomNS + itemKey)
                          if project_auther_EL != None:
                            if project_auther_EL.text != None:
                              projectRelatedURLs.append(project_auther_EL.text)
            for infoKey in ['name']:
                  project_description_EL =  xmlDocRoot.find(pomNS +  infoKey)
                  if project_description_EL != None:
                    if project_description_EL.text != None:
                      if len(project_description_EL.text) > 0:
                          projectName.append(project_description_EL.text) 
            for infoKey in ['description']:
                  project_description_EL =  xmlDocRoot.find(pomNS +  infoKey)
                  if project_description_EL != None:
                    if project_description_EL.text != None:
                     if len(project_description_EL.text) > 0:
                        projectDescription.append(project_description_EL.text) 
            if (len(projectArtifactId) > 0):
                csvWriter.writerow([
                      'pathSuffix',
                      filePattern,  #　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
                      os.path.getsize(filename),  # patternType=fileNameの場合、ファイルサイズの一致でverify可能にする
                        projectGroup + '--' + projectArtifactId + '--' + projectVersion, # mavenリポジトリ風に、groupId--artifactID--version
                       (1  if len(projectLicenseNames) > 0 else 0), # 類似度欄は、確定的であることを示す値. MS-EXCELのフィルターで絞込みし易くする為、len(projectLicenseNames)個は並べない
                       "\n".join(licName2Short(projectLicenseNames, projectLicenseURLs)),
                       "\n".join(projectLicenseURLs),
                       "\n".join(projectAuthers), ## オリジナルBSD等で重要な原権利者名
                       "\n".join(projectRelatedURLs),
                       "\n".join(projectName),
                       "\n".join(projectDescription)
                       ]) 
          elif filename.endswith('package.json'):
            projectGroup = '.' # npmリポジトリでのグループID
            projectArtifactId = ''
            projectVersion = ''
            projectLicenseNames = []
            projectLicenseURLs = []
            projectAuthers = []
            projectRelatedURLs = []
            projectName = []
            projectDescription = []
            # package.json読み込み
            raw_doc = open(filename, 'rb').read()
            encode_detector.reset()
            encode_detector.feed(raw_doc)
            if encode_detector.done:
                encode_detector.close()
                raw_doc = str(raw_doc, encoding = encode_detector.result['encoding'], errors='replace' ).encode('utf-8', 'replace')
            else:
                encode_detector.close()
                raw_doc = str(raw_doc, encoding = 'utf-8', errors='replace' )
            packageInfoDic = json.loads(raw_doc)
            projectArtifactId = packageInfoDic.get('name', '') 
            projectName.append( projectArtifactId ) 
            projectVersion = packageInfoDic.get('version', '') 
            for infoKey in ['license','licenses']:
              curLicenses =  packageInfoDic.get(infoKey, '')
              if  type(curLicenses) == type([]): # list
                  for licInfo in curLicenses:
                    if isinstance(licInfo,dict):
                        curLicText = licInfo.get('type', '')
                        if len(curLicText) > 0:
                            projectLicenseNames.append('spdx/' + curLicText)
                        curLicText = licInfo.get('url', '')
                        if len(curLicText) > 0:
                            projectLicenseURLs.append(curLicText)
                    else:
                        projectLicenseNames.append('spdx/' + licInfo)
              elif isinstance(curLicenses,dict):
                        curLicText = curLicenses.get('type', '')
                        if len(curLicText) > 0:
                            projectLicenseNames.append('spdx/' + curLicText)
                        curLicText = curLicenses.get('url', '')
                        if len(curLicText) > 0:
                            projectLicenseURLs.append(curLicText)
              elif type(curLicenses) == type('') and len(curLicenses) > 0:
                        projectLicenseNames.append('spdx/' +curLicenses)
            curAuthersText = packageInfoDic.get('homepage', '')
            if len(curAuthersText) > 0:
                        projectRelatedURLs.append(curAuthersText)
            for infoKey in ['author','maintainers','contributors']:
              curAuthers =  packageInfoDic.get(infoKey, '')
              if  type(curAuthers) == type([]): # list
                for authersInfo in curAuthers:
                    if isinstance(authersInfo,dict):
                        curAuthersText = authersInfo.get('name', '')
                        if len(curAuthersText) > 0:
                            projectAuthers.append(curAuthersText)
                        curAuthersText = authersInfo.get('email', '')
                        if len(curAuthersText) > 0:
                            projectAuthers.append(curAuthersText)
                        curAuthersText = authersInfo.get('url', '')
                        if len(curAuthersText) > 0:
                            projectRelatedURLs.append(curAuthersText)
                    elif type(authersInfo) == type('') and len(authersInfo) > 0:
                        projectAuthers.append(authersInfo)
              elif isinstance(curAuthers,dict):
                        curAuthersText = curAuthers.get('name', '')
                        if len(curAuthersText) > 0:
                            projectAuthers.append(curAuthersText)
                        curAuthersText = curAuthers.get('email', '')
                        if len(curAuthersText) > 0:
                            projectAuthers.append(curAuthersText)
                        curAuthersText = curAuthers.get('url', '')
                        if len(curAuthersText) > 0:
                            projectRelatedURLs.append(curAuthersText)
              elif type(curAuthers) == type('') and len(curAuthers) > 0:
                        projectAuthers.append(curAuthers)
            for infoKey in ['description', 'keywords']:
                 curDescription = packageInfoDic.get(infoKey, '')
                 if isinstance(curDescription,list):
                    projectDescription.append('[' + ','.join(curDescription) + ']')
                 elif len(curDescription) > 0:
                    projectDescription.append(curDescription)
            if (len(projectArtifactId) > 0):
                csvWriter.writerow([
                      'pathSuffix',
                      filePattern,  #　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
                      os.path.getsize(filename),  # patternType=fileNameの場合、ファイルサイズの一致でverify可能にする
                        projectGroup + '--' + projectArtifactId + '--' + projectVersion, # mavenリポジトリ風に、groupId--artifactID--version
                       (1 if len(projectLicenseNames) > 0 else 0), # 類似度欄は、確定的であることを示す値. MS-EXCELのフィルターで絞込みし易くする為、len(projectLicenseNames)個は並べない
                       "\n".join(licName2Short(projectLicenseNames, projectLicenseURLs)),
                       "\n".join(projectLicenseURLs),
                       "\n".join(projectAuthers), ## オリジナルBSD等で重要な原権利者名
                       "\n".join(projectRelatedURLs),
                       "\n".join(projectName),
                       "\n".join(projectDescription)
                       ]) 
          elif classPathMatcher1.match(filePattern):
              pass
          elif (os.path.splitext(filename)[1]  not in ['.bin', '.class', '.exe', '.dll', '.zip', '.jar', '.tz', '.properties']) and  any([licenseName in os.path.basename(filename) for licenseName in ['license','LICENSE', 'licence' , 'LICENCE', 'notice', 'NOTICE', 'nitify', 'NOTIFY',  'Notices', 'THIRD-PARTY', 'ThirdParty' ,'readme','copy','contribut',  'pom']]):
            raw_doc = open(filename, 'rb').read()
            encode_detector.reset()
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
                    projectGroup = '?'
                    projectArtifactId = ''
                    projectVersion = ''
                    for mached in re.finditer(projectArtifactId_pattern, filePattern):
                        if mached.group(1) != None:
                             projectArtifactId = mached.group(1)
                             projectVersion =  mached.group(2) if ( mached.group(2) != None) else ''
                        elif  mached.group(4) != None:
                            if mached.group(3) == 'node_modules':
                                projectGroup = '.'
                            else:
                                projectGroup = '?'
                            projectArtifactId = mached.group(4)
                            projectVersion =  mached.group(5) if ( mached.group(5) != None) else '0' # maven用のpom.xmlに転記した場合にsyntax errorにならないバージョン
                        elif  mached.group(6) != None:
                            projectGroup = mached.group(6)
                            projectArtifactId = mached.group(7)
                    csvWriter.writerow([
                      'pathSuffix',
                      filePattern,  #　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
                      os.path.getsize(filename),  # patternType=fileNameの場合、ファイルサイズの一致でverify可能にする
                        projectGroup + '--' + projectArtifactId + '--' + projectVersion, # mavenリポジトリ風に、groupId--artifactID--version
                       ",\n".join(['{:3.5f}'.format(similal1) for licName,similal1 in similarl_licenses]),
                       "\n".join(licName2Short([licName for licName,similal1 in similarl_licenses], [])),
                        '', # license URL欄は空
                        '', # auther欄は空
                        '',  # relatedURL欄は空
                        projectArtifactId # name欄はArtifactId
                       ]) 
      except xml.etree.ElementTree.ParseError:
            print("SKIP " , os.path.splitext(filename))
      except  json.JSONDecodeError:
            print("SKIP " , os.path.splitext(filename))
      except UnicodeDecodeError:
            print("SKIP " , os.path.splitext(filename))

for filePattern,programId in classPathMatcher1.list():
      md =  re.search(r'^((?!\-\-).)+\-\-((?:(?!\-\-).)+)\-\-(.*)',programId)
      if md:
          projectGroup = md.groups(1)[0]
          projectArtifactId =md.groups(1)[1]
          projectVersion = md.groups(1)[2]
          csvWriter.writerow([
                       'classPathMach',
                       filePattern,  #　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
                       0,  # patternType=classPathMachの場合、ファイルサイズは観ない
                       projectGroup + '--' + projectArtifactId + '--' + projectVersion, # mavenリポジトリ風に、groupId--artifactID--version
                       ",\n".join(['{:3.5f}'.format(0.25)]),
                       ",\n".join(licName2Short(programId2license.licNames( projectGroup, projectArtifactId,  projectVersion )),
                        '', # license URL欄は空
                        '', # auther欄は空
                        '',  # relatedURL欄は空
                        projectArtifactId # name欄はArtifactId
                       ])
      else:
          print('Error in  classPathMatcher interface ', md,filePattern,programId)
 
outFile.close
