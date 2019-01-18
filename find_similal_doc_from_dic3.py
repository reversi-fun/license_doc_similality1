#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os
import sys
import gensim
from gensim import models

import fileinput
print(sys.argv[1])
raw_doc = open(sys.argv[1].replace('\\', '/'), encoding='utf-8').read()
doc3 = gensim.parsing.preprocess_string(raw_doc)
model = gensim.models.doc2vec.Doc2Vec.load('./data/doc2vec.model')
new_doc_vec3 = model.infer_vector(doc3)
print(model.docvecs.most_similar([new_doc_vec3], topn=32))