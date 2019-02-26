# javaのclassPackage名を含むようなprogramIdを返すClass
# 本クラス用の/config/classPath2ArtifactId.csvは、下記サイトで調査できる。
# API 指定例＝https://search.maven.org/search?q=fc:javax.xml.stream.EventFilter

import os,io,sys
import csv
import re
# import hachoir.regex  #  hachoir-3.0a3 =  python -m pip install -U hachoir / License: GNU GPL v2

class ClassPathMatcher:
    classPath2ProgramIdList = []
    classPath2matcher = None
    programID2FileInfoDict = {}
    def __init__(self,iniFileName='/config/classPath2ArtifactId.csv'):
        toolDirName = os.path.dirname(os.path.abspath(__file__))
        if  os.path.isfile(toolDirName + iniFileName):
            with  io.open(toolDirName +iniFileName, "r",  encoding="utf_8_sig", errors='ignore') as f:
                f.readline()
                reader = csv.reader(f)
                for classPathStr, programIdStr in  reader:
                    self.add_classPackage(classPathStr, programIdStr)
                reader = None
        else:
            print('no file:' + toolDirName + iniFileName )
        self.build()        

    def add_classPackage(self,classPathStr, programIdStr):
        # print(classPathStr, programIdStr)
        self.classPath2ProgramIdList.append((classPathStr, programIdStr))

    def build(self):
        self.classPath2ProgramIdList = sorted(self.classPath2ProgramIdList, key=lambda c2pTupple: (-len(c2pTupple[0]), c2pTupple[0], c2pTupple[1] ))
        patternStr = "(?:\\.jar#?|\\.zip#?|\\.war#?|classes|lib)[\\\\/\\.](?:("  \
           +  ')|('.join([ classPathStr.replace('.','[\.\\\\\\/]' ) for classPathStr, programIdStr in self.classPath2ProgramIdList]) \
           + "[\.\\\\\\/]))"
        self.classPath2matcher = re.compile(patternStr)

    def match(self,filePath):
        if filePath.endswith('.class'):
            md = self.classPath2matcher.search(filePath)
            if md:
                found_programInfo = next((i, v) for i,v in enumerate(list(md.groups())) if v)
                return self.remain(( (filePath[0 : md.start()],  self.classPath2ProgramIdList[found_programInfo[0]][1] ), (-found_programInfo[0], found_programInfo[1],filePath)))
        return None

    # foundData== tupple of ( (filePathPrefix, programIdStr),(packageNamelength, classPackageStr, fileName) )
    def remain(self, foundData):
        self.programID2FileInfoDict[foundData[0]] = min(foundData[1],  self.programID2FileInfoDict.get(foundData[0], foundData[1] ) )
        # print(foundData,  self.programID2FileInfoDict[foundData[0]] )
        return True

    def remainDuplicate(self,fileName,programIdStr):
        pass

    def list(self):
        for (_filePathPrefix, programIdStr),(_, _, fileName) in self.programID2FileInfoDict.items():
            yield (fileName, programIdStr)

# self test code
if __name__ == '__main__':
    r = ClassPathMatcher()
    print(r.match('a.jar#\\com/google/gson/bsh.mod'))
    print(r.match('a.jar#\\com/google/gson/bsh.class'))
    print(r.match('a.jar#/bsh/classes/com/google/gson/com.class'))
    print(r.match('a.jar#/bsh/classes/com/google/gson/com2.class'))
    print(r.match('a.jar#/bsh/classes/com/google/gson/com.aclass'))
    print(r.match('a.war\\com.fasterxml.jackson.class'))
    print(r.match('a.war\\com.fasterxml.jackson.xxx.class'))
    print(r.match('a.war\\com.fasterxml.jackson.annotation.class'))
    print(r.match('a.war\\com.fasterxml.jackson.annotation.yyy.class'))
    print(r.match('b.zip\\io.netty.handler.codec.z.class'))
    print(r.match('b.zip\\io.netty.handler.codec.http.yyy.class'))
    print(r.match('b.zip\\io.netty.handler.flow.yyy.class'))
    print(r.match('c.zip#\\io.netty.handler.codec.http.ddyyy.class'))
    print(r.match('a.war\\google/gson/com.aclass'))
    print(r.match('a.war\\google/gson/com.aclass'))
    print('----list of filepath , programId ---')
    for w in r.list():
        print(w)