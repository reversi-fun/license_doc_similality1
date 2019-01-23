#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os
import sys
import gensim
# from gensim import models

import fileinput

topN = 32
similarl_low = 0.5

print(sys.argv[1])
doc3 = gensim.parsing.preprocess_string(open(sys.argv[1].replace('\\', '/'), encoding='utf-8').read())
model = gensim.models.doc2vec.Doc2Vec.load('./data/doc2vec.model')

# .doc2vec is better Similarity!
# .doc2vecは、隣接する単語の並びをnGram化しているので、文章としての類似度が自然に見える。
new_doc_vec3 = model.infer_vector(doc3)
similarl_docs = sorted(model.docvecs.most_similar([new_doc_vec3], topn=topN),  key=lambda item: -item[1])
print('doc2vec most_similar',len(similarl_docs))
for docName,similarl in similarl_docs:
    print('{:3.5f}'.format(similarl), docName)

# # 上記では類似documentが見つからなかった場合に備え、類似単語を含むドキュメントも列挙する
dictionary1 = gensim.corpora.Dictionary.load('data/id2word2.dict')
lda_model =  gensim.models.ldamodel.LdaModel.load('./data/lda_model')
lda_index =   gensim.similarities.MatrixSimilarity.load('./data/lda_index')

vec_bow3= dictionary1.doc2bow(doc3)
vec_lda3 = lda_model[vec_bow3]
lda_sims3 = sorted([( docIndex,similarl) for  docIndex,similarl in  enumerate(lda_index[vec_lda3]) if similarl > similarl_low] , key=lambda item: -item[1]) 
# 単語の頻度のみで類似を観るldaは、緩いので、件数を絞る。
print('lda most_similar',len(lda_sims3))
for docIndex,similarl in lda_sims3[0:topN]:
    print('{:3.5f}'.format(similarl), model.docvecs.index_to_doctag(docIndex))
    #issue 2091//  File "F:\Anaconda3\lib\site-packages\gensim\models\keyedvectors.py", line 1517, in index_to_doctag
    #issue 2091// return self.ffset2doctag[candidate_offset]
    #issue 2091// AttributeError: 'Doc2VecKeyedVectors' object has no attribute 'ffset2doctag'