#coding: UTF-8
#  http://stmind.hatenablog.com/?page=1384701545
from sklearn.metrics import classification_report
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
import numpy as np
import math
import os
import gensim
from gensim.parsing.preprocessing import preprocess_documents
import json
from operator import itemgetter

# licenseの分類情報を読み込み
f = open("./config/@licenseNotice.json", "r")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_notices = json.load(f)
# ファイルを閉じる
f.close()


# Loding a corpus, remove the line break, convert to lower case
docs = {}
corpus_dir = 'license-list-data-master/text'
for filename in os.listdir(corpus_dir):
    if '.txt' == filename[-4:]:
        name = filename[:-4]
        path = os.path.join(corpus_dir, filename)
        doc = open(path, encoding='utf-8').read().strip().lower()
        docs[name] = doc

names = docs.keys()
files = names

# ストップワードの除去, ステミング
print("\n---Corpus with Stopwords Removed---")

preprocessed_docs = {}
for name in names:
    preprocessed = gensim.parsing.preprocess_string(docs[name])
    preprocessed_docs[name] = preprocessed
    # print(name, ":", preprocessed)

# 辞書を作成
# 低頻度と高頻度のワードは除く
dictionary1 = gensim.corpora.Dictionary(preprocessed_docs.values())
unfiltered = dictionary1.token2id.keys()
dictionary1.filter_extremes(no_below=3, no_above=0.9,
    keep_tokens =  ["evil","Evil", "FUCK","fuck", "beer", "copyleft", '(c)', "donation", 
    "grant", "grants", "granted", "permitted", "permission", "use",
     "GPL","RMS" ] )
filtered = dictionary1.token2id.keys()
filtered_out = set(unfiltered) - set(filtered)
print("Save Dictionary...")
dct_txt = "data/id2word2.txt"
dictionary1.save_as_text(dct_txt)
print("  saved to %s\n" % dct_txt)

print("# BAG OF WORDS")
bow_docs = {}
for docname in files:
    # print(docname,  preprocessed_docs[name])
    bow_docs[docname] = dictionary1.doc2bow(preprocessed_docs[name])

# LSIにより次元削減
print("\n---LSI Model---")

lsi_docs = {}
num_topics = 32
lsi_model = gensim.models.LsiModel(bow_docs.values(),
                                   id2word=dictionary1.load_from_text(dct_txt),
                                   num_topics=num_topics)


def vec2dense(vec, num_terms):
    return list(gensim.matutils.corpus2dense([vec], num_terms=num_terms).T[0])


lsi_docs = {}
for name in names:
    vec = bow_docs[name]
    sparse = lsi_model[vec]
    dense = vec2dense(sparse, num_topics)
    lsi_docs[name] = sparse
    # print(name, ":", dense, vec)

print("\nTopics")
print(lsi_model.print_topics())

# コーパスを作成
corpus1 = [dictionary1.doc2bow(text) for text in  preprocessed_docs.values()]
#gensim.corpora.MmCorpus.serialize('data/cop.mm', [dictionary1.doc2bow(text) for text in preprocessed_docs.values()])

print ("\nLDA Topics")
lda = gensim.models.ldamodel.LdaModel(corpus=corpus1, num_topics= num_topics, id2word=dictionary1.load_from_text(dct_txt))
for i in range(num_topics):
    print('TOPIC:', i, '__', lda.print_topic(i))
# Normalize a vector

print("\n---Unit Vectorization---")
unit_vecs = {}
for name in names:
    vec = vec2dense(lsi_docs[name], num_topics)
    norm = math.sqrt(sum(num**2 for num in vec))
    unit_vec = [num / norm for num in vec]
    unit_vecs[name] = unit_vec
    # print(name, ":", unit_vec)

    # classification
print("\n---Classification---\n")
all_label_notifies = sorted(
    list(set([val for vals in license_notices.values() for val in vals])))
all_data = []
all_lavel = []
# [unit_vecs[name] for name in names if len(license_notices.get(name,[])) > 0 ]
for name, notfies in license_notices.items():
    if (len(notfies) > 0) and (name in unit_vecs.keys()):
        for  notify in notfies:
            all_data.append(unit_vecs[name])
            all_lavel.append(all_label_notifies.index(notify))

train_data, test_data, train_label, test_label = train_test_split(
    all_data, all_lavel , test_size=0.3)

# SVMの学習

classifier = SVC()
classifier.fit(train_data, train_label)

# 予測
predict_label = classifier.predict(test_data)
print(classification_report(test_label, predict_label ,  labels = np.arange(len(all_label_notifies)),target_names=all_label_notifies))
############################################################
#   'recall', 'true', average, warn_for)
#                                              precision    recall  f1-score   support

#                            Apache-1.1 Based       0.00      0.00      0.00   0
#                            Apache-2.0 based       0.00      0.00      0.00   0
#                             Apache-2.0 like       0.00      0.00      0.00   0
#                          BSD 3-clause Based       0.00      0.00      0.00   0
#                                   BSD_based       0.00      0.00      0.00   2
#                      BSD_by_Hewlett-Packard       0.00      0.00      0.00   0
#                                  CDDL_Based       0.00      0.00      0.00   0
#                                   CDDL_like       0.00      0.00      0.00   0
#              Canon Research_JJ2000_Partners       0.00      0.00      0.00   0
#                                      Cipher       0.00      0.00      0.00   1
#                                  Commercial       0.00      0.00      0.00   0
#                                    Donation       0.00      0.00      0.00   1
#                              Free_Doc_based       0.00      0.00      0.00  12
#                              GPL-v2.0 based       0.00      0.00      0.00   0
#                         GPL_incompatibility       0.00      0.00      0.00  23
#                   GPLv2&GPLv3_compatibility       0.00      0.00      0.00  13
# GPLv2&GPLv3_compatibility&Need_dual_license       0.00      0.00      0.00   0
#                         GPLv2_compatibility       0.00      0.00      0.00   0
#                         GPLv3_compatibility       0.00      0.00      0.00   1
#                      Java API dual-licensed       0.00      0.00      0.00   0
#                                  LGPL based       0.00      0.00      0.00   0
#                                 LGPL or BSD       0.00      0.00      0.00   0
#                              LGPL-2.1 based       0.00      0.00      0.00   0
#                                  LGPL_based       0.00      0.00      0.00   0
#                                     MIT_based       0.00      0.00      0.00   7
#                                    MIT_like       0.00      0.00      0.00   0
#                                    MPL_like       0.00      0.00      0.00   0
#                               NonCommercial       0.00      0.00      0.00   4
#                                     NonFree       0.00      0.00      0.00  10
#                       NonFree&NonCommercial       0.00      0.00      0.00   0
#                       Partial_public_domain       0.00      0.00      0.00   1
#                          Patent_Reciprocity       0.27      1.00      0.42  39
#                           Tanuki_Commercial       0.00      0.00      0.00   0
#                             UNICODE_license       0.00      0.00      0.00   0
#                                                Viral       0.00      0.00      0.00   4
#                                    copyLeft       0.00      0.00      0.00   2
#                                    not_Evil       0.00      0.00      0.00   0
#                                 osiApproved       0.00      0.00      0.00  27
#                                 avg / total       0.07      0.27      0.11 147
#
# http://stmind.hatenablog.com/?page=1384701545
# https://qiita.com/icoxfog417/items/7c944cb29dd7cdf5e2b1
# http://kento1109.hatenablog.com/entry/2017/11/15/230909
# https://qiita.com/asian373asian/items/1be1bec7f2297b8326cf
