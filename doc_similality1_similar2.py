#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
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

f = open('data/docNames.txt', 'w')
for docName, doc in preprocessed_docs.items():
    f.write("{},{}\n".format(docName, len(doc)))

f.close()


# 低頻度と高頻度のワードは除く
dictionary1 = gensim.corpora.Dictionary(preprocessed_docs.values())  # 辞書作成
unfiltered = dictionary1.token2id.keys()
dictionary1.filter_extremes(no_below=2,  # 二回以下しか出現しない単語は無視し
                            no_above=0.9,  # 全部の文章の90パーセント以上に出現したワードは一般的すぎるワードとして無視
                            keep_tokens=["evil", "Evil", "FUCK", "fuck", "beer", "copyleft", '(c)', "donation",
                                           "grant", "grants", "granted", "permitted", "permission", "Permissive", "use", "sublicense", "distribute",
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
    name = docname[5:] if docname[0:5] == "spdx/" else  docname[9:]  if docname[0:9] == 'research/'  else docname
    print(docname, name, license_notices.get(name, []))
    training_docs.append(TaggedDocument(words=doc, tags=(
        [docname] ))) #  + license_notices.get(name, [])

model = gensim.models.doc2vec.Doc2Vec(dm=0, vector_size=300, window=17, min_count=1)
model.build_vocab(training_docs)
# model = models.Doc2Vec(training_docs, dm=0, vector_size=300, window=15, alpha=.025,  min_alpha=.025, min_count=1, sample=1e-6)
# model = gensim.models.Doc2Vec(training_docs, dm=0)
print(model)

print('\n訓練開始')
for epoch in range(20):
    print('Epoch: {}'.format(epoch + 1))
    model.train(training_docs, total_examples=model.corpus_count,
                epochs=model.epochs)
    model.alpha -= (0.025 - 0.0001) / 19
    model.min_alpha = model.alpha

model.save('./data/doc2vec.model')

dot = open('data/lic_graph.dot', 'w')
dot.write('digraph LicenseGraph {\n')
dot.write('  newrank = true;\n')
dot.write('  ratio = "auto" ;\n')
# dot.write('  mincross = 2.0 ;\n')
dot.write(' graph [layout="sfdp", rankdir=TB, overlap=false, ranksep=10.0,  nodesep=10.0, margin = 5.5,  concentrate=true]\n')
dot.write(' node [shape=box, width=1];\n')
dot.write(' edge [color=darkgoldenrod, width=1];\n')

license_cluster = {}
for licName, lic_ClsterNames in license_notices.items():
    if len(lic_ClsterNames) > 0:
        nearName = ''
        if  ('spdx/' + licName )  in preprocessed_docs:
            nearName = ('spdx/' + licName)
        elif  ('research/' + licName )  in preprocessed_docs:
             nearName = ('research/' + licName)
        else:
             nearName = '' ## licName
        if len(nearName) > 0:
            for lic_ClsterName in lic_ClsterNames:
                if  (lic_ClsterName not in license_cluster):
                    license_cluster[lic_ClsterName] = []
                license_cluster[lic_ClsterName].append(nearName)

## license clastering nodes
## Error: node "spdx/AFL-3.0" is contained in two non-comparable clusters 2" and "cluster_1"
clusterIndex = 0
for lic_ClsterName, nearNames in  license_cluster.items():
    clusterIndex = clusterIndex + 1
    dot.write('   "' + lic_ClsterName + '"  [label="' + lic_ClsterName + '" , shape=egg, style="dotted,filled", fontcolor=navyblue, color=blue];\n')
    # dot.write('  subgraph  cluster_' + str(clusterIndex) + '{ \n')
    # dot.write('      label = "' +lic_ClsterName + '";\n')
    # dot.write('     style=dashed;	color=blue; \n')
    for nearName in nearNames:
        dot.write('      "' + lic_ClsterName + '" -> "' + nearName  + '"  [dir=none, style=dotted, color=blue];\n')
        # dot.write('       "' + nearName + '" ;\n' )
    # dot.write('  }\n')

for docName, doc in preprocessed_docs.items():
    dot.write('   "' + docName + '"  [label="' + docName + '"];\n')
    similar_docs = model.docvecs.most_similar(docName, topn=5)
    moreShort = 0
    for nearName , similarl in similar_docs:
       if  (nearName in preprocessed_docs ) and  (len(preprocessed_docs[nearName]) <  len(doc)) :
         moreShort = moreShort + 1
         dot.write('      "' + nearName + '" -> "' + docName  + "\" [style=solid,label=\"{0:.3f}\"];\n".format(round(similarl,3) ))
    if moreShort <= 0:
        for nearName , similarl in similar_docs:
             dot.write('      "' + docName + '" -> "' + nearName  +  "\" [style=solid,label=\"{0:.3f}\" ];\n".format(round(similarl,3) ))

dot.write('}\n')
dot.close()

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
print(model.docvecs.most_similar('spdx/SPL-1.0', topn=4))
print(model.docvecs.most_similar('spdx/WTFPL', topn=4))
print(model.docvecs.most_similar('research/ACDL-1.0', topn=4))
print(model.docvecs)
for token in ['Patent_Reciprocity', 'NonCommercial', 'GPL_incompatibility', 'GPLv2&GPLv3_compatibility',
 'BSD_based', 'MIT_based','Cipher', 'NonFree', 'not_Evil']:
    similar_docs = model.docvecs.most_similar(token, topn=14)
    for name , similarl in similar_docs:
      print(token, name,similarl)


print("MPL_like but MIT_base", model.docvecs.most_similar(positive=["MPL_like"], negative=["MIT_based"]))


# docs = corpus_load('./license-list-data-master/own_text')
# for name,doc in docs.items():
#       print(name, model.docvecs.most_similar(doc, topn=4))
# http://ryotakatoh.hatenablog.com/entry/2015/10/29/015502 LDAによる文書の類似度測定

