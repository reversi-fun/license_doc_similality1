#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os
import sys
import gensim
# from gensim import models
import fileinput
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
from licenses_names import load_license_alias  # current module

topN = 32
similarl_low = 0.5

##
toolFileName = sys.argv[0]
if len(toolFileName) <= 0:
    toolDirName = os.path.dirname(os.getcwd())
elif os.path.isdir(toolFileName):
    toolDirName = toolFileName
else:
    toolDirName = os.path.dirname(toolFileName)
print(toolDirName , sys.argv[1])
# licenseの条文の類似性によって分類したライセンスの別名を読み込む
license_alias = load_license_alias()
if license_alias:
    pass
else:
    print("not exist ./config/license_alias.csv")
    exit(1)

# encodingの検出ツールを使う。
encode_detector = UniversalDetector()
encode_detector.reset()
raw_doc = open(sys.argv[1].replace('\\', '/'), 'rb').read()
encode_detector.feed(raw_doc)
if encode_detector.done:
    encode_detector.close()
    raw_doc = raw_doc.decode(encode_detector.result['encoding'], errors='ignore' ) # .encode('utf-8', 'ignore')
else:
    encode_detector.close()
    raw_doc = raw_doc.decode('utf-8', errors='ignore') 
doc3 = gensim.parsing.preprocess_string(raw_doc)
raw_doc = None
model = gensim.models.doc2vec.Doc2Vec.load(os.path.join(toolDirName,'data/doc2vec.model'))

# .doc2vec is better Similarity!
# .doc2vecは、隣接する単語の並びをnGram化しているので、文章としての類似度が自然に見える。
new_doc_vec3 = model.infer_vector(doc3)
similarl_docs = sorted(model.docvecs.most_similar([new_doc_vec3], topn=topN),  key=lambda item: -item[1])
print('doc2vec most_similar',len(similarl_docs))
for docName,similarl in similarl_docs:
        licName2 = license_alias.get(docName.lower(), docName)
        if licName2 !=  docName:
            print('{:3.5f}'.format(similarl), licName2, docName)
        else:
            print('{:3.5f}'.format(similarl), docName)

# # 上記では類似documentが見つからなかった場合に備え、類似単語を含むドキュメントも列挙する
dictionary1 = gensim.corpora.Dictionary.load(os.path.join(toolDirName,'data/id2word2.dict'))
lda_model =  gensim.models.ldamodel.LdaModel.load(os.path.join(toolDirName,'./data/lda_model'))
lda_index =   gensim.similarities.MatrixSimilarity.load(os.path.join(toolDirName,'./data/lda_index'))

vec_bow3= dictionary1.doc2bow(doc3)
vec_lda3 = lda_model[vec_bow3]
lda_sims3 = sorted([( docIndex,similarl) for  docIndex,similarl in  enumerate(lda_index[vec_lda3]) if similarl > similarl_low] , key=lambda item: -item[1]) 
# 単語の頻度のみで類似を観るldaは、緩いので、件数を絞る。
print('lda most_similar',len(lda_sims3))
for docIndex,similarl in lda_sims3[0:topN]:
    try:
        licName1 = model.docvecs.index_to_doctag(docIndex)
        licName2 = license_alias.get(licName1.lower(), licName1)
        if licName2 !=  docName:
            print('{:3.5f}'.format(similarl), licName2, licName1)
        else:
            print('{:3.5f}'.format(similarl), licName1)
        #issue 2091//  File "Anaconda3\lib\site-packages\gensim\models\keyedvectors.py", line 1517, in index_to_doctag
        #issue 2091// return self.ffset2doctag[candidate_offset]
        #issue 2091// AttributeError: 'Doc2VecKeyedVectors' object has no attribute 'ffset2doctag'
    except AttributeError as e:
        pass