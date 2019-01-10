#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os
import gensim
from gensim.parsing.preprocessing import preprocess_documents
from gensim import models
from gensim.models.doc2vec import LabeledSentence
from gensim.models.doc2vec import TaggedDocument
import re
import json

# licenseの分類情報を読み込み
f = open("./config/@licenseNotice.json", "r")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_notices = json.load(f)
# ファイルを閉じる
f.close()
pickUp_token = re.compile(r'[^w][Pp]atent')
pickUp_dict = {}
# Loding a corpus, remove the line break, convert to lower case
def corpus_load(corpus_dir,prefix,pickUp_token,pickUp_dict):
    docs = {}
    for filename in os.listdir(corpus_dir):
        try:
            if '.txt' == filename[-4:]:
                name = prefix + '/' +  filename[:-4]
                path = os.path.join(corpus_dir, filename)
                # .strip().lower()
                raw_doc = open(path, encoding='utf-8').read()
                if pickUp_token.search(raw_doc):
                    pickUp_dict[name] = 'Patent'
                docs[name] = gensim.parsing.preprocess_string(raw_doc)
        except UnicodeDecodeError:
            print("SKIP " + filename)
    return docs

preprocessed_docs = corpus_load('./license-list-data-master/text', 'spdx',pickUp_token,pickUp_dict)
preprocessed_docs.update(corpus_load('./own_text', 'research',pickUp_token,pickUp_dict))
# f = open('data/docNames.txt', 'w')
# for docName, doc in preprocessed_docs.items():
#     f.write("{},{}\n".format(docName, len(doc)))
# f.close()

model = gensim.models.doc2vec.Doc2Vec(dm=0, vector_size=300, window=17, min_count=1)
if not os.path.isfile('./data/doc2vec.model'):
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
        training_docs.append(TaggedDocument(words=doc, tags=(
            [docname] ))) #  + license_notices.get(name, [])
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
else:
    # モデルのロード(モデルが用意してあれば、ここからで良い)
    model = gensim.models.doc2vec.Doc2Vec.load('./data/doc2vec.model')

# 類似度をサンプル表示
print(model.docvecs.most_similar('spdx/GPL-3.0-or-later', topn=14))
print(model.docvecs.most_similar('spdx/LGPL-2.0-only', topn=14))
print(model.docvecs.most_similar('spdx/Sleepycat', topn=14))
print(model.docvecs.most_similar('spdx/BSD-Protection', topn=14))
print(model.docvecs.most_similar('spdx/EPL-1.0', topn=14))
print(model.docvecs.most_similar('spdx/EPL-2.0', topn=14))
print(model.docvecs.most_similar('spdx/CC-BY-NC-SA-1.0', topn=14))
print(model.docvecs.most_similar('spdx/SISSL-1.2', topn=14)) # ('spdx/CDDL-1.0', 0.42703720927238464),
# 選択条件における類似度の下限は、上記出力のsimilarlの値を参考とする
similarl_lower = 0.5

docs_similar_tree = {} # 該当ドキュメントに類似した、短いドキュメント
for docName, doc in preprocessed_docs.items():
    similar_docs = model.docvecs.most_similar(docName, topn=6) # 少数に限定した、短いドキュメントに限定しないと、dotコマンドがメモリ不足となる
    # if  (docName == 'research/MS-RL') or  (docName == 'spdx/MS-RL'):
    #     print('similar_docs', docName,similar_docs )
    # member_count = 0
    # for nearName , similarl in similar_docs:
    #     if nearName not in docs_similar_tree:
    #         docs_similar_tree[nearName] = []
    #     if  (nearName in preprocessed_docs ):
    #         if  ( len(doc) >= len(preprocessed_docs[nearName]) ) and (similarl > similarl_lower) : # 先祖的ライセンスを選ぶ
    #             docs_similar_tree[nearName].append((docName,similarl, len(doc) - len(preprocessed_docs[nearName])))
    #             member_count = member_count + 1
    # if  member_count <= 0: # 先祖が一つも見つからなかった場合、最も似た派生ライセンスを選ぶ
    similar_docs_top = sorted(similar_docs, key=lambda x:(-x[1], x[0]))
    if docName not in docs_similar_tree:
        docs_similar_tree[docName] = []
    for index, (nearName , similarl) in enumerate(similar_docs_top):
            if (index <= 1) or (similarl > similarl_lower) :
                if  ( len(doc) <= len(preprocessed_docs[nearName]) ): 
                    if nearName not in docs_similar_tree:
                       docs_similar_tree[nearName] = []
                    docs_similar_tree[nearName].append((docName,similarl, len(preprocessed_docs[nearName]) - len(doc))) # 先祖的ライセンスとして登録
                else:
                    docs_similar_tree[docName].append((nearName,similarl,  len(doc) - len(preprocessed_docs[nearName]) )) # 子孫的ライセンスとして登録

print('docs_similar_tree.length', len(docs_similar_tree))
# 関連ドキュメントをconcatする
def  tree_related_docs(docs_similar_tree, past_docs, cur_docNames,tree_related_docs_debug):
    related_docs = []
    if (len(cur_docNames) > 0):
        for related_docName in cur_docNames:
            related_docs.append(related_docName[0]) ## 循環参照でも除外リストに追加するが、以降は検索対象外とする
            if all(related_docName[0] != item for item in past_docs):
                if related_docName[0] in docs_similar_tree:
                    related_docs.extend(tree_related_docs(docs_similar_tree, past_docs + [related_docName[0]],  docs_similar_tree[related_docName[0]], tree_related_docs_debug))
    # if tree_related_docs_debug:
    #     print( 'tree_related_docs', past_docs, cur_docNames, related_docs )
    return related_docs

def get_uniq_names(docs_similar):
    seen = []
    return [x for x in docs_similar if (all(x[0] != s[0] for s in seen)) and not seen.append(x)]

for nearName, docs_similar in docs_similar_tree.items():
    docs_similar_tree[nearName] = get_uniq_names(docs_similar)

for nearName, docs_similar in docs_similar_tree.items():
    related_docs = []
    for related_docName in docs_similar:
        if  nearName != related_docName[0]:
            next_related_docs = docs_similar_tree.get(related_docName[0], [])
            if  any(nearName == item[0] for item in next_related_docs) and (related_docName[0] > nearName) : ## 循環参照を除外対象に加える
                related_docs.append(related_docName[0]) 
            else:
                related_docs.extend(tree_related_docs(docs_similar_tree, [nearName, related_docName[0]] , docs_similar_tree.get(related_docName[0], []), False))
    docs_similar_tree[nearName] = [uniq_doc for uniq_doc in docs_similar if  all(item != uniq_doc[0] for item in related_docs)]
    # if  tree_related_docs_debug:
    #   print('updated docs_similar_tree[nearName] ', docs_similar_tree[nearName], docs_similar)

docs_related_tree = {} # 該当ドキュメントから派生した、ドキュメントの一覧
for nearName, docs_similar in docs_similar_tree.items():
    for docName, similarl, len_diff in docs_similar:
        if docName not in docs_related_tree:
            docs_related_tree[docName] = []
        docs_related_tree[docName].append((nearName,similarl, len_diff))

for docName, similar_docs_names  in docs_related_tree.items():
      docs_related_tree[docName] = get_uniq_names(similar_docs_names) # unit

tail_rank_docs = [] # 最も長いドキュメント
for nearName, docs_similar in docs_similar_tree.items():
    if len(docs_related_tree.get(nearName,[])) <= 0:
        related_docs = tree_related_docs(docs_similar_tree, [], docs_similar_tree.get(nearName,[]) , False)
        tail_rank_docs.append((nearName, len(related_docs), related_docs))

tail_rank_docs = sorted(tail_rank_docs, key=lambda x:(x[1], x[0]))
grouped_doc_names = {}
for index,(nearName,doc_count, related_docs) in  enumerate(tail_rank_docs):
    uniq_docs = [nearName] + [doc_name for doc_name in related_docs if doc_name not in  grouped_doc_names]
    tail_rank_docs[index] = (nearName,doc_count, uniq_docs) #  (キュメント名、 関連ドキュメントの数 （len(uniq_docs)に非ず）、ドキュメント）
    for doc_name in uniq_docs:
        grouped_doc_names[doc_name] = index

tail_rank_docs = sorted(tail_rank_docs, key=lambda x:(len(x[2]), x[1],  x[0]))

root_rank_docs = [] # 最も短いドキュメント
for docName, near_doc_name in docs_related_tree.items():
    if len(docs_similar_tree.get(docName,[])) <= 0:
        root_rank_docs.append(docName)

dot = open('data/lic_graph.dot', 'w')
dot.write('digraph LicenseGraph {\n')
dot.write('  newrank = true;\n')
dot.write('  ratio = "auto" ;\n')
# dot.write('  mincross = 2.0 ;\n')
dot.write(' graph [layout="dot", rankdir=LR, overlap=false]\n')
dot.write(' node [shape=box, width=1];\n')
dot.write(' edge [style=solid, color=darkgoldenrod, width=1];\n')

dot.write('{rank=same "' +'" "'.join(root_rank_docs) + '" }\n')
# dot.write('{rank=same "' +'" "'.join(tail_rank_docs) + '" }\n')
for index,(nearName,doc_count, related_docs) in  enumerate(tail_rank_docs):
    dot.write('    subgraph cluster_' + str(index) + ' { style=dashed; color=blue;\n')
    dot.write('        label="' + related_docs[0]+ ' groups count=' + str(doc_count) +  '";\n')
    dot.write('        "' +'";  "'.join(related_docs) + '"; \n')
    pickUp_docs = [docName for docName in related_docs if  len(pickUp_dict.get(docName, '')) > 0]
    if len(pickUp_docs) > 0:
        dot.write('        subgraph cluster_' + str(index) + '_Patents { style="dotted,filled"; color=magenta; fillcolor=lightpink;\n')
        dot.write('            label="' + related_docs[0]+ ' Patent token includes  groups count=' + str(len(pickUp_docs)) +  '";\n')
        dot.write('            "' +'";  "'.join(pickUp_docs) + '"; \n')
        dot.write('        }\n')
    dot.write('    }\n')

for docName, similar_docs_names  in docs_related_tree.items():
    nitcies_items = license_notices.get(docName[5:], []) +  license_notices.get(docName[9:], []) #research/
    if len(nitcies_items) > 0:
        nitcies_text = '\\n' + ','.join(nitcies_items)
    else:
        nitcies_text = ''
    if docName[0:5] != 'spdx/':
        doc_color = ',color=red'
    else:
        doc_color=''
    dot.write('   "' + docName + '"  [label="' + docName + nitcies_text + '"'  + doc_color + '];\n')
    for nearName, similarl, len_diff in similar_docs_names:
         dot.write('      "' +docName   + '" -> "' + nearName  + "\" [label=\"{0:.3f}{1:+d}\"];\n".format(round(similarl,3), len_diff ))

dot.write('}\n')
dot.close()
