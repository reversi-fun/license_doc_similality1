# maven形式のprogramIdから、ライセンス名を返すクラス
import os
import io
import sys
import csv
import re


class ProgramId2License:
    programId2License_dict = {}

    def __init__(self, iniFileName='/config/THIRD-PARTY.properties'):
        toolDirName = os.path.dirname(os.path.abspath(__file__))
        if os.path.isfile(toolDirName + iniFileName):
            self.load(toolDirName + iniFileName)
        else:
            print('no file:' + toolDirName + iniFileName)

    # MVN license:add-third-party形式のデータから、プログラムID毎のライセンス名をロードする
    def load(self, iniFileName):
        ProgramID_line_regexp1 = re.compile(
            r'^\s*([^#](?:(?!--).)*)--((?:(?!--).)+)--((?:(?!=).)+)=(.*?)\s*$')
        ProgramID_data_record_regexp = re.compile(
            r'((?:(?!\s+(?:-\s+)?https?:\/\/|\s+no\s+url\s+defined)[^\(\)])*)(?:\s+(?:-\s+)?(?:(no\s+url\s+defined)|(https?:\/\/[^\(,\s\)]+)))?\s*(?:[\(,\)]|$)')
        with io.open(iniFileName, "r",  encoding="utf_8_sig", errors='ignore') as f:
            for line in f.readlines():
                md1 = ProgramID_line_regexp1.match(line)  # 先頭でマッチしないと駄目
                if md1:  # コメント行はスキップする
                    program_groupId1 = md1.groups(0)[0]
                    program_artifactId1 = md1.groups(0)[1]
                    program_version1 = md1.groups(0)[2]
                    if program_version1 in ['', '?', '*']:
                        program_version1 = '0'
                    raw_licenseNames = md1.groups(0)[3]
                    license_names = []
                    program_org_urls = []  # 該当プログラムを開発した組織またはライセンスのURL
                    for cur_licName, cur_lic_NoURL, cur_orgURL in ProgramID_data_record_regexp.findall(raw_licenseNames):
                        if len(cur_licName) > 1:  # ','を除外する
                            if (cur_licName[0] == '?') and (cur_licName[-1:] == '?'):
                                cur_licName = cur_licName[1:-1]
                            license_names.append((cur_licName, cur_orgURL))
                    self.add_license_info_2_programId(
                        program_groupId1,  program_artifactId1, program_version1, license_names)
                    # print (line,program_groupId1,  program_artifactId1, program_version1,license_names, self. programId2License_dict [program_artifactId1][program_groupId1][ program_version1])

    def add_license_info_2_programId(self, program_groupId1,  program_artifactId1, program_version1, license_names):
        if (len(license_names) > 0):
            if program_artifactId1 not in self. programId2License_dict:
                self. programId2License_dict[program_artifactId1] = {}
            if program_groupId1 not in self. programId2License_dict[program_artifactId1]:
                self. programId2License_dict[program_artifactId1][program_groupId1] = {
                }
            if program_version1 not in self. programId2License_dict[program_artifactId1][program_groupId1]:
                self. programId2License_dict[program_artifactId1][program_groupId1][program_version1] = [
                ]
            for cur_licName in license_names:
                if (cur_licName not in self. programId2License_dict[program_artifactId1][program_groupId1][program_version1]) and  \
                   ((len(cur_licName[1]) <= 0) or (cur_licName[0] not in [pastName[0] for pastName in self. programId2License_dict[program_artifactId1][program_groupId1][program_version1]])):
                    self. programId2License_dict[program_artifactId1][program_groupId1][program_version1].append(
                        cur_licName)
                if (len(cur_licName[1]) > 0) and ((cur_licName[0], '') in self. programId2License_dict[program_artifactId1][program_groupId1][program_version1]):
                    self. programId2License_dict[program_artifactId1][program_groupId1][program_version1].remove(
                        (cur_licName[0], ''))
            return True
        return False

    # 全エントリをトラバースする
    def items(self):
        for program_artifactId1 in sorted(self.programId2License_dict.keys(), key=lambda x: (x.lower(), x)):
            for program_groupId1, group_info in self.programId2License_dict[program_artifactId1].items():
                for program_version1, lic_names in group_info.items():
                    yield ((program_groupId1, program_artifactId1, program_version1), lic_names)

    def save(self, iniFileName):
        if not os.path.isdir(os.path.dirname(iniFileName)):
            os.makedirs(os.path.dirname(iniFileName))
        with io.open(iniFileName, "w",  encoding="utf_8_sig", errors='ignore') as f:
            for (program_groupId1, program_artifactId1, program_version1), lic_info_list in self.items():
                programId_str = program_groupId1 + '--' + \
                    program_artifactId1 + '--' + program_version1
                licInfo_str = ''
                if len(lic_info_list) > 1:
                    lic_info_list = sorted(
                        list(set(lic_info_list)), key=lambda w: (w[0].lower(), w[0]))
                    licInfo_str = '(' + '),('.join([(lic_info[0] + ' - ' + lic_info[1] if len(
                        lic_info[1]) > 0 else lic_info[0]) for lic_info in lic_info_list]) + ')'
                elif len(lic_info_list) == 1:
                    # url部有り? or 曖昧なライセンス名
                    if (len(lic_info_list[0][1]) > 0) or (lic_info_list[0][-1:] == '?'):
                        licInfo_str = '(' + lic_info_list[0][0] + \
                            ' - ' + lic_info_list[0][1] + ')'
                    else:
                        licInfo_str = lic_info_list[0][0]
                f.write(programId_str + '=' + licInfo_str + '\n')

    def add_license_info(self, programId_str, license_names):
        md1 = re.match(
            r'^\s*([^#](?:(?!--).)*)--((?:(?!--).)*)--((?:(?!=).)*)',  programId_str)
        if md1:
            program_groupId1 = md1.groups(0)[0]
            program_artifactId1 = md1.groups(0)[1]
            program_version1 = md1.groups(0)[2]
            return self.add_license_info_2_programId(program_groupId1,  program_artifactId1, program_version1, license_names)
        return False

    # 存在するlicense_namesエントリを更新する
    def replace_license_info2_programId(self, program_groupId1,  program_artifactId1, program_version1, license_names):
        try:
            self. programId2License_dict[program_artifactId1][program_groupId1][program_version1] = license_names
            return True
        except KeyError:
            return False

    def licNameWithURL1(self,  program_groupId1, program_artifactId1,  program_version1):
        license_names = []
        if program_version1 in ['', '?', '*']:
            program_version1 = '0'
        if program_artifactId1 in self. programId2License_dict:
            if (program_groupId1 in self. programId2License_dict[program_artifactId1]):
                if (program_version1 in self. programId2License_dict[program_artifactId1][program_groupId1]):
                    return self. programId2License_dict[program_artifactId1][program_groupId1][program_version1]
        return []

    def licNameWithUrls(self,  program_groupId1, program_artifactId1,  program_version1):
        license_names = []
        license_urls = []
        if program_version1 in ['', '?', '*']:
            program_version1 = '0'
        if program_artifactId1 in self. programId2License_dict:
            if (program_groupId1 not in ['', '?', '*']) and (program_groupId1 in self. programId2License_dict[program_artifactId1]):
                if (program_version1 not in ['', '0', '?', '*']) and (program_version1 in self. programId2License_dict[program_artifactId1][program_groupId1]):
                    for licName, licURL in self. programId2License_dict[program_artifactId1][program_groupId1][program_version1]:
                        license_names.append(licName)
                        license_urls.append(licURL)
                else:
                    for _, lic_names in self. programId2License_dict[program_artifactId1][program_groupId1].items():
                        for licName, licURL in lic_names:
                            license_names.append(licName)
                            license_urls.append(licURL)
            else:
                for _, grpInfo in self.programId2License_dict[program_artifactId1].items():
                    for _, lic_names in grpInfo.items():
                        for licName, licURL in lic_names:
                            license_names.append(licName)
                            license_urls.append(licURL)
            license_names = sorted(
                list(set(license_names)), key=lambda w: (w.lower(), w))
            license_urls = sorted(
                list(set([str(url1) for url1 in license_urls if url1 and (len(url1) > 0)])))
        else:
            pass
        return (license_names, license_urls)


def load_license_alias():
    license_alias = {}
    toolFileName = sys.argv[0]
    if len(toolFileName) <= 0:
        toolDirName = os.path.dirname(os.getcwd())
    elif os.path.isdir(toolFileName):
        toolDirName = toolFileName
    else:
        toolDirName = os.path.dirname(toolFileName)
    if os.path.isfile(toolDirName + "/config/license_alias.csv"):
        with io.open(toolDirName + "/config/license_alias.csv", "r",  encoding="utf_8_sig", errors='ignore') as f:
            f.readline()
            reader = csv.reader(f)
            for aliasName, shortName in reader:
                # TODO: aliasNameとshortNamealiasとは、1対多、または、多対多に、対応つけるよう、1セル内の複数行を読めたほうが良い。
                license_alias[aliasName.lower()] = shortName
                # print(aliasName, shortName)
                # TODO: skip ValueError: not enough values to unpack (expected 2, got 0)
            reader = None
    else:
        return None
    return license_alias

def save_license_alias(license_alias):  
    toolFileName = sys.argv[0]
    if len(toolFileName) <= 0:
        toolDirName = os.path.dirname(os.getcwd())
    elif os.path.isdir(toolFileName):
        toolDirName = toolFileName
    else:
        toolDirName = os.path.dirname(toolFileName)
    with open( toolDirName + "/config/license_alias_updated.csv", 'w', encoding="utf_8_sig") as f:
        writer = csv.writer(f, lineterminator='\n') # 改行コード（\n）を指定しておく
        writer.writerow(['aliasNames', 'shortName'])
        for aliasName, shortName in sorted(license_alias.items()):
            writer.writerow([aliasName.lower(), shortName])

# license name spaceのソート順
licenseSortOrder={'spdx': 1, 'OSI': 2, 'FSF': 3, 'Approved': 4 , 'research': 5, '': 6}

def licName2Short(license_alias, licNames, licURLs):
    return sorted(list(set(
        [license_alias.get(aliasName.lower(), aliasName).replace('\\n', '\r').replace('\\r', '\r') for aliasName in licNames if aliasName] +
        [license_alias[aliasName.lower()].replace('\\n', '\n').replace('\\r', '\n')
         for aliasName in licURLs if aliasName and (len(aliasName) > 0) and (aliasName.lower() in license_alias)]
    )),
        key=lambda item: (licenseSortOrder[(list(filter(lambda x: (x + '/') in item, licenseSortOrder)) + [''])[0]], item))

# self test code
# THIRD-PARTY.propertiesの内容を正規化したファイル（THIRD-PARTY.properties.updates.txt）を作成する。
# THIRD-PARTY.properties.updates.txtにヘッダコメントを追加して、THIRD-PARTY.propertiesに上書きすればよい。
if __name__ == '__main__':
    t = ProgramId2License()
    for projectGroup, projectArtifactId, projectVersion in [('org.bouncycastle', 'bcmail-jdk14', ''),
                                                            ('annogen', 'annogen', '0'), 
                                                            ('asm.wso2', 'asm', '0'), ('xmlpull', 'xmlpull', '0'),
                                                            ('net.jcip', 'jcip-annotations',
                                                             '0'), ('urbanophile', 'java-getopt', '*'),
                                                            ('xml-apis', 'xml-apis', '0'), ('xml-apis', 'xmlparserapis', '*'), ('xpp3', 'xpp3_xpath', '0')]:
        print(projectGroup, projectArtifactId, projectVersion, t.licNameWithUrls(
            projectGroup, projectArtifactId, projectVersion))
    # licenseの条文の類似性によって分類したライセンスの別名を読み込む
    license_alias = load_license_alias()
    if (license_alias):
        for (program_groupId1, program_artifactId1, program_version1), lic_names in t.items():
            nomalized_license_names = []
            for licName1, licURL in lic_names:
                if licName1.lower() in license_alias:
                    nomalized_license_name = license_alias[licName1.lower()]
                else:
                    nomalized_license_name = '?' + licName1 + '?'
                    print(nomalized_license_name)
                for prefix in ['spdx', 'OSI', 'FSF', 'Approved', 'research']:
                    if nomalized_license_name.startswith(prefix + '/'):
                        nomalized_license_name = nomalized_license_name[(
                            len(prefix) + 1):]
                nomalized_license_names.append(
                    (nomalized_license_name, licURL))
            nomalized_license_names = sorted(
                list(set(nomalized_license_names)),
                key=lambda w: (w[0].lower(), w[0]))
            t.replace_license_info2_programId(
                program_groupId1,  program_artifactId1, program_version1,  nomalized_license_names)
    t.save('./config/THIRD-PARTY.properties.updates.txt')
