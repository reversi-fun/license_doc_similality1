#coding: UTF-8
#  http://stmind.hatenablog.com/?page=1384701545
import os
import gensim
from gensim.parsing.preprocessing import preprocess_documents
from gensim import models
from gensim.models.doc2vec import LabeledSentence
from gensim.models.doc2vec import TaggedDocument
import json
# licenseの分類情報を読み込み
f = open("./config/@licenseNotice.json", "r")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_notices = json.load(f)
# ファイルを閉じる
f.close()

# Loding a corpus, remove the line break, convert to lower case


def corpus_load(corpus_dir):
    docs = {}
    for filename in os.listdir(corpus_dir):
        try:
            if '.txt' == filename[-4:]:
                name = filename[:-4]
                path = os.path.join(corpus_dir, filename)
                # .strip().lower()
                raw_doc = open(path, encoding='utf-8').read()
                docs[name] = gensim.parsing.preprocess_string(raw_doc)
        except UnicodeDecodeError:
            print("SKIP " + filename)
    return docs


preprocessed_docs = corpus_load('./license-list-data-master/text')
# preprocessed_docs.update(corpus_load('./license-list-data-master/own_text'))

# 低頻度と高頻度のワードは除く
dictionary1 = gensim.corpora.Dictionary(preprocessed_docs.values())  # 辞書作成
unfiltered = dictionary1.token2id.keys()
dictionary1.filter_extremes(no_below=2,  # 二回以下しか出現しない単語は無視し
                            no_above=0.9,  # 全部の文章の90パーセント以上に出現したワードは一般的すぎるワードとして無視
                            keep_tokens=["evil", "Evil", "FUCK", "fuck", "beer", "copyleft", '(c)', "donation",
                                           "grant", "grants", "granted", "permitted", "permission", "use",
                                         "GPL", "RMS"])
filtered = dictionary1.token2id.keys()
filtered_out = set(unfiltered) - set(filtered)
print("Save Dictionary...")
dct_txt = "data/id2word2.txt"
dictionary1.save_as_text(dct_txt)
print("  saved to %s\n" % dct_txt)

# コーパスを作成
corpus1 = [dictionary1.doc2bow(text) for text in preprocessed_docs.values()]
gensim.corpora.MmCorpus.serialize(
    'data/cop.mm', [dictionary1.doc2bow(text) for text in preprocessed_docs.values()])

print("\n# BAG OF WORDS")
bow_docs = {}
for docname, doc in preprocessed_docs.items():
    # print(docname, doc)
    bow_docs[docname] = dictionary1.doc2bow(doc)

# LSIにより次元削減
print("\n---LSI Model---")
num_topics = 33
lsi_model = gensim.models.LsiModel(bow_docs.values(),
                                   id2word=dictionary1.load_from_text(dct_txt),
                                   num_topics=num_topics)

lsi_docs = {}
for docname in preprocessed_docs.keys():
    vec = bow_docs[docname]
    sparse = lsi_model[vec]
    # vec2dense(sparse, num_topics)
    dense = list(gensim.matutils.corpus2dense(
        [sparse], num_terms=num_topics).T[0])
    lsi_docs[docname] = sparse
    print(docname, ":", dense, vec)

print("\nLSI Topics")
for lsiTopic in lsi_model.get_topics():
    print(lsiTopic, "\n")

print("\nLDA Topics")
lda = gensim.models.ldamodel.LdaModel(
    corpus=corpus1, num_topics=num_topics, id2word=dictionary1.load_from_text(dct_txt))

for i in range(num_topics):
    print('TOPIC:', i, '__', lda.print_topic(i))

print([coherence[1] for coherence in lda.top_topics(corpus=corpus1)])

print("\ncoherence")
cm = gensim.models.CoherenceModel(lda, corpus=corpus1, coherence='u_mass')
for coherence in cm.get_coherence_per_topic():
    print(coherence)
##############################

#########################################
# training
training_docs = []
for docname, doc in preprocessed_docs.items():
    training_docs.append(TaggedDocument(words=doc, tags=(
        [docname] + license_notices.get(docname, []))))

# model = models.Doc2Vec(training_docs, dm=0, vector_size=300, window=15, alpha=.025,  min_alpha=.025, min_count=1, sample=1e-6)
model = models.Doc2Vec(training_docs, dm=0)
print(model)

print('\n訓練開始')
for epoch in range(20):
    print('Epoch: {}'.format(epoch + 1))
    model.train(training_docs, total_examples=model.corpus_count,
                epochs=model.epochs)
    model.alpha -= (0.025 - 0.0001) / 19
    model.min_alpha = model.alpha

model.save('./data/doc2vec.model')

#################################################################
# licenseの分類情報を読み込み
f = open("./config/@licenseNotice.json", "r")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_notices = json.load(f)
# ファイルを閉じる
f.close()

# classification
print("\n---Classification---\n")
all_label_notifies = sorted(
    list(set([val for vals in license_notices.values() for val in vals])))
all_data = []
all_lavel = []
for name, notfies in license_notices.items():
    if (len(notfies) > 0) and (name in unit_vecs.keys()):
        for notify in notfies:
            all_data.append(unit_vecs[name])
            all_lavel.append(all_label_notifies.index(notify))

train_data, test_data, train_label, test_label = train_test_split(
    all_data, all_lavel, test_size=0.3)

# SVMの学習

classifier = SVC()
classifier.fit(train_data, train_label)

# 予測
predict_label = classifier.predict(test_data)
print(classification_report(test_label, predict_label,  labels=np.arange(
    len(all_label_notifies)), target_names=all_label_notifies))
############################################################
