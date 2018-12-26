#coding: UTF-8
#  http://stmind.hatenablog.com/?page=1384701545
import os
import gensim
from gensim.parsing.preprocessing import preprocess_documents
from gensim import models
from gensim.models.doc2vec import LabeledSentence
from gensim.models.doc2vec import TaggedDocument
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
def corpus_load(corpus_dir,prefix):
    docs = {}
    for filename in os.listdir(corpus_dir):
        try:
            if '.txt' == filename[-4:]:
                name = prefix + '/' +  filename[:-4]
                path = os.path.join(corpus_dir, filename)
                # .strip().lower()
                raw_doc = open(path, encoding='utf-8').read()
                docs[name] = gensim.parsing.preprocess_string(raw_doc)
        except UnicodeDecodeError:
            print("SKIP " + filename)
    return docs


preprocessed_docs = corpus_load('./license-list-data-master/text', 'spdx')
preprocessed_docs.update(corpus_load('./own_text', 'research'))

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

#########################################
# training
training_docs = []
for docname, doc in preprocessed_docs.items():
    training_docs.append(TaggedDocument(words=doc, tags=(
        [docname] + license_notices.get(docname, []))))

# model = models.Doc2Vec(training_docs, dm=0, vector_size=300, window=15, alpha=.025,  min_alpha=.025, min_count=1, sample=1e-6)
model = gensim.models.Doc2Vec(training_docs, dm=0)
print(model)

print('\n訓練開始')
for epoch in range(20):
    print('Epoch: {}'.format(epoch + 1))
    model.train(training_docs, total_examples=model.corpus_count,
                epochs=model.epochs)
    model.alpha -= (0.025 - 0.0001) / 19
    model.min_alpha = model.alpha

model.save('./data/doc2vec.model')

print(model.docvecs.most_similar('spdx/IBM-pibs', topn=4))
print(model.docvecs.most_similar('spdx/MITNFA', topn=4))
print(model.docvecs.most_similar('spdx/MIT-feh', topn=4))
print(model.docvecs.most_similar('spdx/MIT-0', topn=4))
print(model.docvecs.most_similar('spdx/MIT', topn=4))
print(model.docvecs.most_similar('spdx/MIT-advertising', topn=4))
print(model.docvecs.most_similar('spdx/X11', topn=4))
print(model.docvecs.most_similar('spdx/deprecated_StandardML-NJ', topn=4))
print(model.docvecs.most_similar('spdx/CC0-1.0', topn=20))
print(model.docvecs.most_similar('spdx/SGI-B-2.0', topn=4))
print(model.docvecs.most_similar('spdx/GPL-3.0-or-later', topn=14))
print(model.docvecs.most_similar('spdx/SPL-1.0', topn=14))
print(model.docvecs.most_similar('spdx/WTFPL', topn=14))
print(model.docvecs.most_similar('research/SystemC_Open_Source_License', topn=4))
print(model.docvecs.most_similar('research/ACDL-1.0', topn=4))
print(model.docvecs.most_similar('research/X11', topn=4))



# docs = corpus_load('./license-list-data-master/own_text')
# for name,doc in docs.items():
#       print(name, model.docvecs.most_similar(doc, topn=4))
# http://ryotakatoh.hatenablog.com/entry/2015/10/29/015502 LDAによる文書の類似度測定

