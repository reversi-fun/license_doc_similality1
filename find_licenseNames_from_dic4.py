# coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os
import io
import sys
import gensim
import glob
import fileinput
import re
import csv
# https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
from chardet.universaldetector import UniversalDetector
# 以下はpom.xml読みこみ用
import xml
import xml.etree.ElementTree as ET
# 以下はpackage.json読みこみ用
import json
# 以下は、ライセンス名の　名寄せ用
from classPathMatcher import ClassPathMatcher  # current module
from licenses_names import ProgramId2License  # current module
from licenses_names import load_license_alias  # current module
from licenses_names import licName2Short  # current module

# license name spaceのソート順を、licenses_namesでの標準とは変える
#licenseSortOrder={'spdx': 1, 'OSI': 2, 'FSF': 3, 'calculate-Linux':4, 'Approved': 5 , 'Considered':6, 'research': 7, '': 8}
licenseSortOrder = {'spdx': 1, 'OSI': 1,  'FSF': 1, 'calculate-Linux':4,  'Approved': 5, 'Considered': 6, 'research': 7, '': 8}

# カスタマイズ可能項目の設定
topN = 3  # 最大出力するライセンス名の個数
# model.docvecs.most_similarの類似度の下限。 node_modules\escape-string-regexp\readme.mdの類似度より大きな値
similarl_low = 0.63
# [spdx/BSD-2-Clauseとspdx/BSD-3-Clause-Clear]が候補になった場合、類似度の比率で、カットオフする閾値
similarl_cutoff = 0.95
projectArtifactId_pattern = re.compile(r'[\/\\]((?:(?![_-][VR]e?r?v?\d|\d\.|\.jar|\.war|\.zip|META-INF)[\w\d\.#@+_-])+)(?:(?:[_-](?:[V]e?r?|[R]e?v?|(?=\d)))(\d+(?:(?!\.(?:jar|war|zip))[\w\d\.@+_-]+)*))?(?:\.jar#?|\.war#?|\.zip#?|#)(?=[\/\\])|(?:^|(?:^|[\/\\])(node_modules|pkgs|site-packages|vendor|plugins|eclipse[\w\d\-\_]*[\\\/]features|(?:Library|lib)(?:share|common)?)[\/\\])(?!(?:node_modules|pkgs|site-packages|Library|lib|vendor|plugins|legal|licenses?)[\\\/])((?:(?![_-](?:[VR]e?r?v?)?\d)[\w\d\.#@+_-])+)(?:(?:[_-](?:[V]e?r?|[R]e?v?|(?=\d)))(\d+[\w\d\.#@+_-]*))?(?=[\/\\])|META-INF\\maven\\([^\\]+)\\([^\\]+)\\(?:[^\\]+$)|(?:(?:^|[\\\/])(?:legal|licenses?)[\\\/](?:(?:license[_-]?)?((?:(?!(?:[_-]license)?\.md$).)+)(?:[_-]license)?(?:\.md$)|([^\\\/]+)))', re.IGNORECASE)
#  注意：上記正規表現は「Lib\site-packages\bokeh\LICENSE.txt」に対して”site-packages”とマッチしないように
# 「pkgs\icu-58.2-h3fcc66b_1\Library\share\icu\58.2\LICENSE」に対して、"share"がマッチしないように

# 引数or実行環境の取得
if len(sys.argv) <= 2:
    sys.stderr.write(
        "usage: python find_licenseNames_from_dic4.py inputDir outputDir \n")
    sys.exit(1)

inDirName = os.path.abspath(sys.argv[1])
outputDirName = sys.argv[2].replace('\\', '/')
outputFileName = outputDirName + "/filePattern2License.csv"
toolFileName = sys.argv[0]
if len(toolFileName) <= 0:
    toolDirName = os.path.dirname(os.getcwd())
elif os.path.isdir(toolFileName):
    toolDirName = toolFileName
else:
    toolDirName = os.path.dirname(toolFileName)

print("input dir=" + inDirName)
print("output file(license names for FilePath pattern)=" + outputFileName)

if not os.path.exists(outputDirName):
    os.makedirs(outputDirName)

# licenseの条文の類似性によって分類したライセンスの別名を読み込む
license_alias = load_license_alias()
if license_alias:
    pass
else:
    print("not exist ./config/license_alias.csv")
    exit(1)

classPathMatcher1 = ClassPathMatcher()
programId2license = ProgramId2License()

outFile = open(outputFileName, "w", newline="\n", encoding="utf-8")
csvWriter = csv.writer(outFile, doublequote=True, quotechar='"')

# gensimで学習済みのデータ読み込み
model = gensim.models.doc2vec.Doc2Vec.load(
    os.path.join(toolDirName, 'data/doc2vec.model'))
# ファイル毎のライセンス名を探して、csv出力する。
csvWriter.writerow(['identificationType', 'fileIdentifier', 'fileSize', 'ArtifactId', 'similarity(s)',
                    'RawLicenseName(s)',
                    'licenseName(s)', 'licenseURL(s)', 'auther(s)', 'relatedURL(s)', 'name', 'description'])
# encodingの検出ツールを使う。
encode_detector = UniversalDetector()
for filename in glob.glob(inDirName + "/**/*",  recursive=True):
    try:
        if os.path.isfile(filename) and (os.path.getsize(filename) < 2048000):
            filePattern = (filename[len(inDirName)+1:] if filename.startswith(inDirName) else filename).replace('/', '\\')
            projectGroup = '?' # 不明なグループId
            projectArtifactId = '' # 著作物の識別名
            projectVersion = '' # 著作物のバージョン
            projectLicenseRawNames  = [] # 生のライセンス名
            similaritys = [0] # ライセンス条文の類似度、または、確かさ
            projectLicenseNames = [] # 不確かなライセンス名、名前空間つきで名寄せしたライセンス名
            projectLicenseURLs = []
            projectAuthers = []
            projectRelatedURLs = []
            projectName = []
            projectDescription = []
            if filename.endswith('pom.xml') or filename.endswith('.pom'):
                # xmlDocTree = ET.parse(filename) <-- error "xml.etree.ElementTree.ParseError  not well-formed (invalid token)""
               #  xmlDocRoot = xmlDocTree.getroot()
                raw_doc = open(filename, 'rb').read()
                encode_detector.reset()
                encode_detector.feed(raw_doc)
                if encode_detector.done:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding=encode_detector.result['encoding'], errors='replace') #.decode(encoding='utf-8', errors='replace')
                else:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding='utf-8', errors='replace')
                raw_doc = raw_doc.replace('&oslash;', 'Ø').replace('&nbsp;', ' ')
                xmlDocRoot = ET.fromstring(raw_doc)
                # <Element '{http://maven.apache.org/POM/4.0.0}project'
                # '{http://maven.apache.org/POM/4.0.0}'
                pomNS = xmlDocRoot.tag[0: -7] if len(xmlDocRoot.tag) > 6 else ''
                projectGroupEL = xmlDocRoot.find(pomNS + 'groupId')
                if isinstance(projectGroupEL, xml.etree.ElementTree.Element) and isinstance(projectGroupEL.text,str):
                    projectGroup = re.sub(r'[\s\r\n]+', ' ',projectGroupEL.text).strip()
                else:
                    projectGroupEL = xmlDocRoot.find(
                        pomNS + 'parent/' + pomNS + 'groupId')
                    if isinstance(projectGroupEL, xml.etree.ElementTree.Element) and isinstance(projectGroupEL.text,str):
                        projectGroup = re.sub(r'[\s\r\n]+', ' ',projectGroupEL.text).strip()
                projectArtifactIdEL = xmlDocRoot.find(pomNS + 'artifactId')
                if isinstance(projectArtifactIdEL, xml.etree.ElementTree.Element) and isinstance(projectArtifactIdEL.text,str):
                    projectArtifactId = re.sub(r'[\s\r\n]+', ' ',projectArtifactIdEL.text).strip()
                else:
                    projectArtifactIdEL = xmlDocRoot.find(
                        pomNS + 'parent/' + pomNS + 'artifactId')
                    print('parent/artifactId', projectArtifactIdEL)
                    if isinstance(projectArtifactIdEL, xml.etree.ElementTree.Element) and isinstance(projectArtifactIdEL.text,str):
                        projectArtifactId = re.sub(r'[\s\r\n]+', ' ',projectArtifactIdEL.text).strip()
                projectVersionEL = xmlDocRoot.find(pomNS + 'version')
                if isinstance( projectVersionEL, xml.etree.ElementTree.Element) and isinstance( projectVersionEL.text,str):
                    projectVersion = re.sub(r'[\s\r\n]+', ' ',projectVersionEL.text).strip()
                else:
                    projectVersionEL = xmlDocRoot.find(
                        pomNS + 'parent/' + pomNS + 'version')
                    if isinstance(projectVersionEL, xml.etree.ElementTree.Element) and isinstance(projectVersionEL.text,str):
                        projectVersion = re.sub(r'[\s\r\n]+', ' ',projectVersionEL.text).strip()
                for xml_project_license_element in xmlDocRoot.findall(pomNS + 'licenses/' + pomNS + 'license'):
                    project_lic_name_EL = xml_project_license_element.find(pomNS + 'name')
                    if isinstance( project_lic_name_EL, xml.etree.ElementTree.Element) and isinstance(project_lic_name_EL.text,str):
                       projectLicenseRawNames.append(re.sub(r'[\s\r\n]+', ' ',project_lic_name_EL.text).strip())
                    project_lic_url_EL = xml_project_license_element.find(pomNS + 'url')
                    if isinstance(project_lic_url_EL, xml.etree.ElementTree.Element) and isinstance(project_lic_url_EL.text,str):
                        projectLicenseURLs.append(re.sub(r'[\s\r\n]+', ' ',project_lic_url_EL.text).strip())
                for infoKey in ['developers/' + pomNS + 'developer', 'organization',  'contributors/' + pomNS + 'contributor']:
                    for project_authers_EL in xmlDocRoot.findall(pomNS + infoKey):
                        for itemKey in ['id',  'name',  'email', 'organization']:
                            project_auther_EL = project_authers_EL.find(
                                pomNS + itemKey)
                            if isinstance(project_auther_EL, xml.etree.ElementTree.Element) and isinstance(project_auther_EL.text,str):
                                projectAuthers.append(re.sub(r'[\s\r\n]+', ' ',project_auther_EL.text).strip())
                        for itemKey in ['url']:
                            project_auther_EL = project_authers_EL.find(pomNS + itemKey)
                            if isinstance(project_auther_EL, xml.etree.ElementTree.Element) and isinstance(project_auther_EL.text,str):
                                projectRelatedURLs.append(re.sub(r'[\s\r\n]+', ' ',project_auther_EL.text).strip())
                for infoKey in ['name']:
                    project_description_EL = xmlDocRoot.find(pomNS + infoKey)
                    if isinstance(project_description_EL, xml.etree.ElementTree.Element) and isinstance(project_description_EL.text,str) and(len(project_description_EL.text) > 0):
                        projectName.append(re.sub(r'[\s\r\n]+', ' ',project_description_EL.text).strip())
                if len(projectName) <= 0:
                       projectName.append(projectArtifactId) 
                for infoKey in ['description']:
                    project_description_EL = xmlDocRoot.find(pomNS + infoKey)
                    if isinstance(project_description_EL, xml.etree.ElementTree.Element) and isinstance(project_description_EL.text,str) and (len(project_description_EL.text) > 0):
                        projectDescription.append(re.sub(r'[\s\r\n]+', ' ',project_description_EL.text).strip())
                if (len(projectArtifactId) > 0):
                    if len(projectLicenseRawNames) > 0:
                        projectLicenseNames  = licName2Short(license_alias,projectLicenseRawNames,projectLicenseURLs)
                        # 類似度欄は、確定的であることを示す値. MS-EXCELのフィルターで絞込みし易くする為、len(projectLicenseNames)個は並べない
                        similaritys = [1]
                    else:
                        projectLicenseNames, projectLicenseURLs = programId2license.licNameWithUrls(
                            projectGroup, projectArtifactId,  projectVersion)
                        if len(projectLicenseNames) > 0: # projectArtifactIdからライセンス名の推定が出来た場合
                            # programIDが確かで、Mavenリポジトリから調べたlicenseNameにつき、npmより大きな確度とする
                            similaritys = [0.5]
                        else:
                            similaritys = [0]
            elif filename.endswith('package.json'):
                projectGroup = '.'  # npmリポジトリでのグループID
                # package.json読み込み
                raw_doc = open(filename, 'rb').read()
                encode_detector.reset()
                encode_detector.feed(raw_doc)
                if encode_detector.done:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding=encode_detector.result['encoding'], errors='replace').encode(
                        'utf-8', 'replace')
                else:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding='utf-8', errors='replace')
                packageInfoDic = json.loads(raw_doc)
                projectArtifactId = re.sub(r'[\s\r\n]+', ' ',packageInfoDic.get('name', '')).strip()
                projectName.append(projectArtifactId)
                projectVersion = packageInfoDic.get('version', '')
                for infoKey in ['license', 'licenses']:
                    curLicenses = packageInfoDic.get(infoKey, '')
                    if type(curLicenses) == type([]):  # list
                        for licInfo in curLicenses:
                            if isinstance(licInfo, dict):
                                curLicText = re.sub(r'[\s\r\n]+', ' ',licInfo.get('type', '')).strip()
                                if len(curLicText) > 0:
                                    projectLicenseRawNames.append(curLicText)
                                curLicText = licInfo.get('url', '')
                                if len(curLicText) > 0:
                                    projectLicenseURLs.append(curLicText.strip())
                            else:
                                projectLicenseRawNames.append(re.sub(r'[\s\r\n]+', ' ',licInfo).strip())
                    elif isinstance(curLicenses, dict):
                        curLicText = re.sub(r'[\s\r\n]+', ' ',curLicenses.get('type', '')).strip()
                        if len(curLicText) > 0:
                            projectLicenseRawNames.append(curLicText)
                        curLicText = re.sub(r'[\s\r\n]+', ' ',curLicenses.get('url', '')).strip()
                        if len(curLicText) > 0:
                            projectLicenseURLs.append(curLicText)
                    elif isinstance(curLicenses,str) and len(curLicenses) > 0:
                       projectLicenseRawNames.append(re.sub(r'[\s\r\n]+', ' ',curLicenses).strip())
                curAuthersText = packageInfoDic.get('homepage', '')
                if len(curAuthersText) > 0:
                    projectRelatedURLs.append(curAuthersText)
                for infoKey in ['author', 'maintainers', 'contributors']:
                    curAuthers = packageInfoDic.get(infoKey, '')
                    if type(curAuthers) == type([]):  # list
                        for authersInfo in curAuthers:
                            if isinstance(authersInfo, dict):
                                curAuthersText = authersInfo.get('name', '')
                                if len(curAuthersText) > 0:
                                    projectAuthers.append(curAuthersText)
                                curAuthersText = authersInfo.get('email', '')
                                if len(curAuthersText) > 0:
                                    projectAuthers.append(curAuthersText)
                                curAuthersText = authersInfo.get('url', '')
                                if len(curAuthersText) > 0:
                                    projectRelatedURLs.append(curAuthersText)
                            elif isinstance(authersInfo,str) and len(authersInfo) > 0:
                                projectAuthers.append(authersInfo)
                    elif isinstance(curAuthers, dict):
                        curAuthersText = curAuthers.get('name', '')
                        if len(curAuthersText) > 0:
                            projectAuthers.append(curAuthersText)
                        curAuthersText = curAuthers.get('email', '')
                        if len(curAuthersText) > 0:
                            projectAuthers.append(curAuthersText)
                        curAuthersText = curAuthers.get('url', '')
                        if len(curAuthersText) > 0:
                            projectRelatedURLs.append(curAuthersText)
                    elif isinstance(curAuthers,str) and len(curAuthers) > 0:
                        projectAuthers.append(curAuthers)
                for infoKey in ['description', 'keywords']:
                    curDescription = packageInfoDic.get(infoKey, '')
                    if isinstance(curDescription, list):
                        projectDescription.append(
                            '[' + ','.join(curDescription) + ']')
                    elif len(curDescription) > 0:
                        projectDescription.append(curDescription)
                if (len(projectArtifactId) > 0):
                    if len(projectLicenseRawNames) > 0:
                        projectLicenseNames  = licName2Short(license_alias,projectLicenseRawNames,projectLicenseURLs)
                        # 類似度欄は、確定的であることを示す値. MS-EXCELのフィルターで絞込みし易くする為、len(projectLicenseNames)個は並べない
                        similaritys = [1]
                    else:
                        projectLicenseNames, projectLicenseURLs = programId2license.licNameWithUrls(
                            projectGroup, projectArtifactId,  projectVersion)
                        if len(projectLicenseNames) > 0: # projectArtifactIdからライセンス名の推定が出来た場合
                            # programIDが確かでも、package.jsonに無かったlicenseNameの調べ方は確立していないので、mavenより小さな確度とする
                            similaritys = [0.4]
                        else:
                            similaritys = [0]
            elif filename.endswith('index.json'):
                projectGroup = '_pypi_'  # PiPyリポジトリでのグループID
                # package.json読み込み
                raw_doc = open(filename, 'rb').read()
                encode_detector.reset()
                encode_detector.feed(raw_doc)
                if encode_detector.done:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding=encode_detector.result['encoding'], errors='replace').encode(
                        'utf-8', 'replace')
                else:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding='utf-8', errors='replace')
                packageInfoDic = json.loads(raw_doc)
                if isinstance(packageInfoDic, dict ):
                    projectArtifactId = re.sub(r'[\s\r\n]+', ' ',packageInfoDic.get('name', '')).strip()
                    projectName.append(projectArtifactId)
                    projectVersion  =  re.sub(r'[\s\r\n]+', ' ',packageInfoDic.get('version', '?')).strip() + '-' + re.sub(r'[\s\r\n]+', ' ',packageInfoDic.get('build', '')).strip()
                    if len(packageInfoDic.get('license', '')) > 0:
                        projectLicenseRawNames.append(re.sub(r'[\s\r\n]+', ' ',packageInfoDic.get('license', '')).strip())   
                    if (len(projectArtifactId) > 0):
                        if len(projectLicenseRawNames) > 0:
                            projectLicenseNames  = licName2Short(license_alias,projectLicenseRawNames,projectLicenseURLs)
                            # 類似度欄は、確定的であることを示す値. MS-EXCELのフィルターで絞込みし易くする為、len(projectLicenseNames)個は並べない
                            similaritys = [1]
                        else:
                            projectLicenseNames, projectLicenseURLs = programId2license.licNameWithUrls(
                                projectGroup, projectArtifactId,  projectVersion)
                            if len(projectLicenseNames) > 0: # projectArtifactIdからライセンス名の推定が出来た場合
                                # programIDが確かでも、package.jsonに無かったlicenseNameの調べ方は確立していないので、mavenより小さな確度とする
                                similaritys = [0.4]
                            else:
                                similaritys = [0]
                else:
                    print('error document format',type(packageInfoDic),filename)  
            elif classPathMatcher1.match(filePattern):
                pass
            elif (os.path.splitext(filename)[1] not in ['.bin', '.class', '.exe', '.dll', '.zip', '.jar', '.tz', '.properties','gif','.png', '.sha1']) \
               and (any([licenseName in os.path.basename(filename) for licenseName in ['license', 'LICENSE', 'licence', 'LICENCE', 'notice', 'NOTICE', 'nitify', 'NOTIFY',  'Notices', 'THIRD-PARTY', 'ThirdParty', 'readme', 'copy', 'contribut',  'pom']]) \
                 or re.match(r'(?:legal|license.?)[\\\/].+?[\.](?:md|txt|html)$', filePattern, re.IGNORECASE)
               ):
                raw_doc = open(filename, 'rb').read()
                encode_detector.reset()
                encode_detector.feed(raw_doc)
                if encode_detector.done:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding=encode_detector.result['encoding'], errors='replace').encode(
                        'utf-8', 'replace')
                else:
                    encode_detector.close()
                    raw_doc = str(raw_doc, encoding='utf-8', errors='replace')
                doc3 = gensim.parsing.preprocess_string(raw_doc)
                if len(doc3) > 4:
                    new_doc_vec3 = model.infer_vector(doc3)
                    similarl_licenses = [[licName, similal1] for licName, similal1 in model.docvecs.most_similar(
                        [new_doc_vec3]) if (similal1 >= similarl_low)]
                    if len(similarl_licenses) > 1:
                        ccutoff_similarl = max(
                            [similal1 for licName, similal1 in similarl_licenses]) * similarl_cutoff
                        similarl_licenses = sorted([[licName, similal1] for licName, similal1 in similarl_licenses if similal1 >= ccutoff_similarl], key=lambda item: (
                            licenseSortOrder[(list(filter(lambda x: (x + '/') in item[0], licenseSortOrder)) + [''])[0]], -item[1]))[0:topN]
                    if len(similarl_licenses) > 0:
                        projectLicenseNames = [
                                licName for licName, similal1 in similarl_licenses]
                        projectLicenseURLs = []  # license URL欄は空
                        similaritys = [similal1 for licName,
                                           similal1 in similarl_licenses]
                        projectArtifactId = '?' # similarl_licensesが在る為、何かの著作物であると見なす
                        for mached in re.finditer(projectArtifactId_pattern, filePattern):
                            if mached.group(1) != None:
                                projectArtifactId = mached.group(1)
                                projectName.append(projectArtifactId)
                                projectVersion = mached.group(2) if (
                                    mached.group(2) != None) else ''
                            elif mached.group(4) != None:
                                projectArtifactId = mached.group(4)
                                if mached.group(3) == 'node_modules':
                                    projectGroup = '.'
                                elif mached.group(3) in ['pkgs', 'site-packages']:
                                    projectGroup = '_pypi_'
                                else:
                                    projectGroup = '?'
                                # maven用のpom.xmlに転記した場合にsyntax errorにならないバージョン
                                projectVersion = mached.group(5) if (
                                    mached.group(5) != None) else '0'
                            elif mached.group(6) != None:
                                projectGroup = mached.group(6)
                                projectArtifactId = mached.group(7)
                            elif mached.group(8) != None:
                                projectArtifactId = mached.group(8)
                            elif mached.group(9) != None:
                                projectArtifactId = mached.group(9)
                        projectName.append(projectArtifactId)
            if len(projectArtifactId) > 0:
                projectLicenseNames = licName2Short(license_alias,projectLicenseNames, projectLicenseURLs)
                csvWriter.writerow([
                        'pathSuffix',
                        filePattern,  # 　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
                        # patternType=fileNameの場合、ファイルサイズの一致でverify可能にする
                        os.path.getsize(filename),
                        projectGroup + '--' + projectArtifactId + '--' + \
                        projectVersion,  # mavenリポジトリ風に、groupId--artifactID--version
                        ",\n".join(['{:3.5f}'.format(similal1)
                                    for similal1 in similaritys]),
                        ",\n".join(projectLicenseRawNames ), # 生のライセンス名
                        ",\n".join(projectLicenseNames), # URLから逆変換したライセンス名など、不確かなライセンス名
                        ",\n".join(projectLicenseURLs),  # license URL欄
                        ",\n".join(projectAuthers),  # オリジナルBSD等で重要な原権利者名
                        ",\n".join(projectRelatedURLs),
                        "\n".join(projectName),
                        "\n".join(projectDescription)
                    ])
    except xml.etree.ElementTree.ParseError as e:
        print("SKIP by xml.etree.ElementTree.ParseError ", e, os.path.splitext(filename),raw_doc[0:90])
    except json.JSONDecodeError as e:
        print("SKIP by json.JSONDecodeError ", e, os.path.splitext(filename),raw_doc[0:90])
    except UnicodeDecodeError as e:
        print("SKIP by UnicodeDecodeError ", e, os.path.splitext(filename),raw_doc[0:9])

programId2license.save('./config/THIRD-PARTY.properties.updates.txt')
for filePattern, programId in classPathMatcher1.list():
    md = re.search(
        r'^((?:(?!\-\-).)*)\-\-((?:(?!\-\-).)+)\-\-(.*)$', programId)
    if md:
        projectGroup = md.group(1)
        projectArtifactId = md.group(2)
        projectVersion = md.group(3)
        projectLicenseNames, projectLicenseURLs = programId2license.licNameWithUrls(
            projectGroup, projectArtifactId,  projectVersion)
        if len(projectLicenseNames) > 0:
            similaritys = [0.3]
        else:
            similaritys = [0]
        csvWriter.writerow([
            'classPathMach',
            filePattern,  # 　一つのプログラムに多数のOSSが同梱されている場合と、区別できるよう、inDirName配下の相対パスをwindowsPath形式にした文字列。　
            0,  # patternType=classPathMachの場合、ファイルサイズは観ない
            projectGroup + '--' + projectArtifactId + '--' + \
                projectVersion,  # mavenリポジトリ風に、groupId--artifactID--version
            ",\n".join(['{:3.5f}'.format(similal1)
                        for similal1 in similaritys]),
            '',  # 確からしいライセンス名の欄は空
            ",\n".join(licName2Short(license_alias,
                projectLicenseNames, projectLicenseURLs)),
            ",\n".join(projectLicenseURLs),  # license URL欄
            '',  # auther欄は空
            '',  # relatedURL欄は空
            projectArtifactId  # name欄はArtifactId
        ])
    else:
        print('Error in  classPathMatcher interface ',
              md, filePattern, programId)

outFile.close
