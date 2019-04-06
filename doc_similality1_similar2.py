#coding: UTF-8
# http://tadaoyamaoka.hatenablog.com/entry/2017/04/29/122128 学習済みモデルを使用して文の類似度を測る
#  http://stmind.hatenablog.com/?page=1384701545
import os,io
import math
import csv
import glob
import gensim
from gensim.parsing.preprocessing import preprocess_documents
from gensim import models
from gensim.models.doc2vec import LabeledSentence
from gensim.models.doc2vec import TaggedDocument
from gensim import corpora, similarities
import re
import json
from chardet.universaldetector import UniversalDetector  # https://chardet.readthedocs.io/en/latest/usage.html#example-using-the-detect-function
from licenses_names import load_license_alias  # current module
from licenses_names import save_license_alias  # current module
from licenses_names import licenseSortOrder  # current module

# licenseの条文の類似性によって分類したライセンスの別名を読み込む
license_alias =  load_license_alias()
if  license_alias:
    pass
else:
    license_alias = {}

# SPDXのlicenseの分類情報を読み込み
license_notices = {'':[]}
f = open("./license-list-data-master/json/licenses.json", "r",  encoding="utf-8")
spdx_licenseData = json.load(f)
f.close()
for spdxData in spdx_licenseData['licenses']:
    if len(license_alias.get('spdx/' + spdxData['licenseId'].lower(),'')) <= 0:
        license_alias['spdx/' + spdxData['licenseId'].lower()] =  'spdx/' + spdxData['licenseId']
    if len(license_alias.get(spdxData['licenseId'].lower(),'')) <= 0:
        license_alias[spdxData['licenseId'].lower()] =  'spdx/' + spdxData['licenseId']
    if len(license_alias.get(spdxData['name'].lower(),'')) <= 0:
        license_alias[spdxData['name'].lower()] =  'spdx/' + spdxData['licenseId']
    if spdxData['isOsiApproved']:
        license_notices[ 'spdx/' + spdxData['licenseId'].lower()] = ['OsiApproved']

f = open("./license-list-data-master/json/exceptions.json", "r",  encoding="utf-8")
spdx_licenseData = json.load(f)
f.close()
for spdxData in spdx_licenseData['exceptions']:
    if len(license_alias.get('spdx/' + spdxData['licenseExceptionId'].lower(),'')) <= 0:
        license_alias['spdx/' + spdxData['licenseExceptionId'].lower()] =  'spdx/' + spdxData['licenseExceptionId']
    if len(license_alias.get(spdxData['licenseExceptionId'].lower(),'')) <= 0:
        license_alias[spdxData['licenseExceptionId'].lower()] =  'spdx/' + spdxData['licenseExceptionId']
    if len(license_alias.get(spdxData['name'].lower(),'')) <= 0:
        license_alias[spdxData['name'].lower()] =  'spdx/' + spdxData['licenseExceptionId']

# FSFのlicenseの分類情報を読み込み
# https://directory.fsf.org/wiki/Free_Software_Directory:SPDX_Group
# https://github.com/wking/fsf-apiからGPLとの互換性に関する情報を転記する
# https://wking.github.io/fsf-api/licenses-full.json
f = open("./config/FSF-licenses-full.json", "r",  encoding="utf-8")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
# ファイルを閉じる
f.close()
for licName,licMetaData in license_metaData['licenses'].items():
    license_notices['FSF/' + licName] = licMetaData.get('tags', [])
    if len(license_alias.get(licMetaData['name'].lower(),'')) <= 0:
        license_alias[licMetaData['name'].lower()] = 'FSF/' + licName
    if (len(licMetaData.get('identifiers',{})) > 0) and (len(licMetaData['identifiers'].get('spdx',[])) > 0):
        license_alias[('FSF/' + licName).lower()] = 'spdx/' + min(licMetaData['identifiers']['spdx'])
        if len( license_alias.get(licMetaData['name'], '')) <= 0:
              license_alias[licMetaData['name'].lower()] = 'spdx/' + min(licMetaData['identifiers']['spdx'])
        for spdxId in licMetaData['identifiers']['spdx']:
             license_notices['spdx/' + spdxId] = license_notices.get('spdx/' + spdxId, []) + licMetaData.get('tags', [])

# OSIのlicenseの分類情報を読み込み
f = open("./config/OSI-licenses-full.json", "r",  encoding="utf-8")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
# ファイルを閉じる
f.close()
for licName,licMetaData in license_metaData.items():
    license_notices['OSI/' + licName] = ['OsiApproved']
    license_alias[('OSI/' + licName).lower()] = 'spdx/' + licMetaData['id']
    if len(license_alias.get(licName.lower(),'')) <= 0:
        license_alias[licName.lower()] = 'spdx/' + licMetaData['id']

# calculate-Linux-のlicenseの分類情報を読み込み
f = open("./config/calculate-Linux-licenses-full.json", "r",  encoding="utf_8_sig")
# jsonデータを読み込んだファイルオブジェクトからPythonデータを作成
license_metaData = json.load(f)
# ファイルを閉じる
f.close()
for licName,licMetaData in license_metaData.items():
    license_alias[(licMetaData['url']).lower()] = 'calculate-Linux/' + licName
        
pickUp_token = re.compile(r'[^w][Pp]atent')
pickUp_dict = {}
# Loding a corpus, remove the line break, convert to lower case
# encodingの検出ツールを使う。
encode_detector = UniversalDetector()
def corpus_load(corpus_dir,prefix,pickUp_token,pickUp_dict):
    docs = {}
    for filename in glob.glob(corpus_dir + '/**', recursive=True):
        filePattern = (filename[len(corpus_dir)+1:] if filename.startswith(corpus_dir) else filename).replace('/', '\\')
        try:
          if  os.path.isfile(filename)  and (os.path.getsize(filename) < 2048000) and all([not filename.endswith(suffix) for suffix in ['.bin', '.class', '.exe', '.dll', '.zip', '.jar', '.tz', '.properties', '.MF', 'pom.xml','.gif','.png', '.sha1']]) \
             and (prefix != 'research'  \
                or any([licenseName in filename for licenseName in ['license','LICENSE', 'licence' , 'LICENCE', 'notice', 'NOTICE', 'nitify', 'NOTIFY',  'Notices', 'THIRD-PARTY', 'ThirdParty' ,'readme','copy','contribut',  'pom']])
                or re.match(r'(?:legal|license.?)[\\\/].+?[\.](?:md|txt|html)$', filePattern, re.IGNORECASE)
                ): 
            if '.txt' == filename[-4:]:
                name = prefix + '/' +  filename[len(corpus_dir) + 1:-4]
            else:
                name = prefix + '/' +  filename[len(corpus_dir) + 1:]
            name = name.replace('\\', '/')
            encode_detector.reset()
            raw_doc = open(filename, 'rb').read()
            encode_detector.feed(raw_doc)
            if encode_detector.done:
                encode_detector.close()
                raw_doc = raw_doc.decode(encode_detector.result['encoding'], errors='ignore' ) # .encode('utf-8', 'ignore')
            else:
                encode_detector.close()
                raw_doc = raw_doc.decode('utf-8', errors='ignore' )
            parsed_words = gensim.parsing.preprocess_string(raw_doc)
            if (len(parsed_words) > 4) or (name.startswith('Approved/-')):
                docs[name] = parsed_words
                print('loaded ', name)
                if pickUp_token.search(raw_doc):
                    pickUp_dict[name] = 'Patent'
        # expect TypeError:
        #    print("SKIP " + filename, encode_detector)
        except UnicodeDecodeError:
            print("SKIP " + filename, encode_detector)
    return docs

preprocessed_docs = corpus_load('./license-list-data-master/text', 'spdx',pickUp_token,pickUp_dict)
preprocessed_docs.update(corpus_load('./OSI_texts', 'OSI',pickUp_token,pickUp_dict))
preprocessed_docs.update(corpus_load('./FSF_texts', 'FSF',pickUp_token,pickUp_dict))
preprocessed_docs.update(corpus_load('./calculate-Linux_texts', 'calculate-Linux',pickUp_token,pickUp_dict))
preprocessed_docs.update(corpus_load('./Approved_texts', 'Approved',pickUp_token,pickUp_dict))
preprocessed_docs.update(corpus_load('./Considered_texts', 'Considered',pickUp_token,pickUp_dict))
preprocessed_docs.update(corpus_load('./own_texts', 'research',pickUp_token,pickUp_dict))
f = open('data/docNames.txt', 'w',  encoding="utf-8")
for docName, doc in preprocessed_docs.items():
    f.write("{},{}\n".format(docName, len(doc)))
f.close()

model = gensim.models.doc2vec.Doc2Vec(dm=0, vector_size=300, window=17, min_count=1)
if not os.path.isfile('./data/doc2vec.model'):
    # 低頻度と高頻度のワードは除く
    dictionary1 = gensim.corpora.Dictionary(preprocessed_docs.values())  # 辞書作成
    unfiltered = dictionary1.token2id.keys()
    dictionary1.filter_extremes(no_below=2,  # 二回以下しか出現しない単語は無視し
                            no_above=0.9,  # 全部の文章の90パーセント以上に出現したワードは一般的すぎるワードとして無視
                            keep_tokens=["evil", "Evil", "FUCK", "fuck", "beer", "copyleft", '(c)', "donation", "ALL", "ANY", "AND", "OR", "prease", "see", "base", "initial",
                                           "grant", "grants", "granted", "permitted", "permission", "Permissive", "use", "sublicense", "distribute",
                                         "GPL", "RMS", "ISC", "X"])
    filtered = dictionary1.token2id.keys()
    filtered_out = set(unfiltered) - set(filtered)
    # 作成した辞書をファイルに保存
    print("Save Dictionary...")
    dct_txt = "data/id2word2.txt"
    dictionary1.save_as_text(dct_txt)
    dct_dict = "data/id2word2.dict"
    dictionary1.save('data/id2word2.dict')
    print("  saved to %s\n" % dct_txt)
    # コーパスを作成
    corpus1 = [dictionary1.doc2bow(text) for text in preprocessed_docs.values()]
    gensim.corpora.MmCorpus.serialize('data/cop.mm', corpus1)

    print("\n# BAG OF WORDS")
    bow_docs = {}
    for docname, doc in preprocessed_docs.items():
        # print(docname, doc)
        bow_docs[docname] = dictionary1.doc2bow(doc)

    # LSIにより次元削減
    print("\n---LSI Model---")
    num_topics = 33
    # lsiモデルのみtfidfコーパスが必要なため一部作成順序が変わっています。
    tfidf_model = models.TfidfModel(corpus1)
    tfidf_corpus = tfidf_model[corpus1]
    lsi_model = models.LsiModel(tfidf_corpus, id2word=dictionary1, num_topics= num_topics)
    # lsi_model = gensim.models.LsiModel(bow_docs.values(),id2word=dictionary1, num_topics=num_topics)
    lsi_model.save('./data/lsi.model')
    lsi_index = similarities.MatrixSimilarity(lsi_model[tfidf_corpus])
    # ※インデックス化は非常に時間がかかるため、毎回実施すべきでない
    # インデックスの保存
    print('lsi_index', lsi_index)
    lsi_index.save('./data/lsiModels.index')
    lsi_docs = {}
    for docname in preprocessed_docs.keys():
        vec = bow_docs[docname]
        sparse = lsi_model[vec]
        # vec2dense(sparse, num_topics)
        dense = list(gensim.matutils.corpus2dense([sparse], num_terms=num_topics).T[0])
        lsi_docs[docname] = sparse
        print(docname, ":", dense)
    # print("\nLSI Topics")
    # for lsiTopic in lsi_model.get_topics():
    #     print(lsiTopic, "\n")
    # https://hivecolor.com/id/88
    lda_model = gensim.models.ldamodel.LdaModel(corpus=corpus1, num_topics=num_topics, id2word=dictionary1)
    # print("\nLDA Topics")
    # print('topics: {}'.format(lda_model.show_topics(num_topics=num_topics, num_words=20)))
    # for i in range(num_topics):
    #     print('TOPIC:', i, '__', lda_model.print_topic(i))
    lda_model.save('./data/lda_model')
    lda_index = similarities.MatrixSimilarity(lda_model[corpus1])
    lda_index.save('./data/lda_index')

    print('sample LSI topic', lsi_model[bow_docs['spdx/GPL-3.0-or-later']])

     # https://www.programcreek.com/python/example/88175/gensim.similarities.MatrixSimilarity
    #########################################
    # training
    training_docs = []
    for docname, doc in preprocessed_docs.items():
        doc_alias = license_alias.get(docName.lower(),docName)
        if doc_alias == docName:
            tags =  [docname]
        else:
            tags =  [docname, doc_alias]
        if docname in  license_notices:
            tags.extend(license_notices[docname])
        training_docs.append(TaggedDocument(words=doc, tags=tags))
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
    dictionary1 = gensim.corpora.Dictionary.load('data/id2word2.dict')
    model = gensim.models.doc2vec.Doc2Vec.load('./data/doc2vec.model')
    lsi_model = gensim.models.LsiModel.load('./data/lsi.model')
    lsi_index = similarities.MatrixSimilarity.load('./data/lsiModels.index')
    lda_model =  gensim.models.ldamodel.LdaModel.load('./data/lda_model')
    lda_index =   similarities.MatrixSimilarity.load('./data/lda_index')

# 類似度をサンプル表示
print(model.docvecs.most_similar('spdx/GPL-3.0-or-later', topn=14))
print(model.docvecs.most_similar('spdx/LGPL-2.0-only', topn=14))
print(model.docvecs.most_similar('spdx/Sleepycat', topn=14))
print(model.docvecs.most_similar('spdx/BSD-Protection', topn=14))
print(model.docvecs.most_similar('spdx/EPL-1.0', topn=14))
print(model.docvecs.most_similar('spdx/EPL-2.0', topn=14))
print(model.docvecs.most_similar('spdx/MPL-2.0', topn=14))
print(model.docvecs.most_similar('spdx/CC-BY-NC-SA-1.0', topn=14))
print(model.docvecs.most_similar('spdx/Sleepycat', topn=14))
print(model.docvecs.most_similar('spdx/SISSL-1.2', topn=14)) # ('spdx/CDDL-1.0', 0.42703720927238464),
print('Approved/Oculus_VR_Rift_SDK_License', model.docvecs.most_similar('Approved/Oculus_VR_Rift_SDK_License', topn=14))
print(model.docvecs.most_similar('spdx/Sleepycat', topn=14))
print(model['spdx/Sleepycat'])


doc3 = open('Approved_texts/Oculus_VR_Rift_SDK_License.txt', encoding='utf-8').read()
vec_bow3= dictionary1.doc2bow(doc3.lower().split())
vec_lsi3 = lsi_model[vec_bow3] # convert the query to LSI space
print('Approved_texts/Oculus_VR_Rift_SDK_License.txt', 'vec3','lsi-model',len(vec_lsi3),vec_lsi3)
vec_lda3 = lda_model[vec_bow3]
print('Approved_texts/Oculus_VR_Rift_SDK_License.txt', 'vec3','lda-model',len(vec_lda3), vec_lda3)
lda_sims3 = lda_index[vec_lda3]
lda_sims3 = sorted(enumerate(lda_sims3), key=lambda item: -item[1])
print('Approved_texts/Oculus_VR_Rift_SDK_License.txt', 'sim3','lda-index',len(lda_sims3))
for i,similarl3 in lda_sims3[0:14]:
    print(u'lda類似度=' + str(similarl3) + ':[' + str(i) +  '] ' + list(preprocessed_docs.keys())[i])

new_doc_vec3 = model.infer_vector(doc3)
print('Approved_texts', model.docvecs.most_similar([new_doc_vec3], topn=14))
# 選択条件における類似度の下限は、上記出力のsimilarlの値を参考とする
similarl_lower = 0.5 # 類似していると見なす閾値
similarl_extend = 0.35 # 孤立しそうなdocumentについて、類似していると見なす閾値
similarl_upper = 0.95 # 同一条文と見なす閾値

docs_similar_tree = {} # 該当ドキュメントに類似した、短いドキュメント
same_text_groups_seq = {} # 同一条文と見なすドキュメントのグループ番号
same_text_groups_seq_num = 0
same_text_groups_names = {} # 上記グルーピングの転置
# 別名情報によるグループ化
for docName, doc in preprocessed_docs.items():
    nearName = license_alias.get(docName.lower(),'')
    if len(nearName) > 0:
        if nearName not in preprocessed_docs:
            if  (nearName + '+'  in preprocessed_docs):
                 nearName = nearName + '+'
            elif (nearName + '-or-later'  in preprocessed_docs):
                 nearName = nearName + '-or-later'
            elif (nearName + '-only'  in preprocessed_docs):
                 nearName = nearName + '-only'
            else:
                nearName = '' # textが無いlicense名は、取り消す
    if len(nearName) > 0:
        same_text_groups_seq_num  += 1
        cur_groups_seq_num = min([same_text_groups_seq.get(docName,same_text_groups_seq_num ), same_text_groups_seq.get(nearName,same_text_groups_seq_num )])
        same_text_groups_seq[docName] = cur_groups_seq_num
        if  cur_groups_seq_num == same_text_groups_seq_num:
                    same_text_groups_names[cur_groups_seq_num] = []
        else:
                    same_text_groups_seq[nearName] = cur_groups_seq_num
        if docName not in  same_text_groups_names[cur_groups_seq_num]:
                    same_text_groups_names[cur_groups_seq_num].append(docName)
        if nearName not in  same_text_groups_names[cur_groups_seq_num]:
                    same_text_groups_names[cur_groups_seq_num].append(nearName)
# 文書内容の類似性によるクループ化または隣接マトトリックス作成
for docName, doc in preprocessed_docs.items():
    if docName not in docs_similar_tree:
        docs_similar_tree[docName] = []
    # 少数に限定した、短いドキュメントに限定しないと、dotコマンドがメモリ不足となる
    similar_docs_top = sorted(model.docvecs.most_similar(docName, topn=8), key=lambda x:(-x[1], x[0]))
    similarl_count = 0
    for index, (nearName , similarl) in enumerate(similar_docs_top):
        if nearName in preprocessed_docs:
            similarl_upper_words = math.ceil((1.0 - similarl_upper) * (len(doc) + len(preprocessed_docs[nearName])) / 2 / 8)  #1words in 100words
            if  (similarl > similarl_upper) and ((0 - similarl_upper_words) <= (len(doc) - len(preprocessed_docs[nearName])) <= similarl_upper_words) : # 同一条文である
                same_text_groups_seq_num  += 1
                cur_groups_seq_num = min([same_text_groups_seq.get(docName,same_text_groups_seq_num ), same_text_groups_seq.get(nearName,same_text_groups_seq_num )])
                same_text_groups_seq[docName] = cur_groups_seq_num
                if  cur_groups_seq_num == same_text_groups_seq_num:
                    same_text_groups_names[cur_groups_seq_num] = []
                else:
                    same_text_groups_seq[nearName] = cur_groups_seq_num
                if docName not in  same_text_groups_names[cur_groups_seq_num]:
                    same_text_groups_names[cur_groups_seq_num].append(docName)
                if nearName not in  same_text_groups_names[cur_groups_seq_num]:
                    same_text_groups_names[cur_groups_seq_num].append(nearName)
            elif  (similarl >= similarl_lower) : # 同一ではないが、似ている条文である
                similarl_count += 1
                if  ( len(doc) <= len(preprocessed_docs[nearName]) ): 
                    if nearName not in docs_similar_tree:
                       docs_similar_tree[nearName] = []
                    docs_similar_tree[nearName].append((docName,similarl, len(preprocessed_docs[nearName]) - len(doc))) # 子孫的ライセンスとして登録
                else:
                    docs_similar_tree[docName].append((nearName,similarl,  len(doc) - len(preprocessed_docs[nearName]) )) # 先祖的ライセンスとして登録
        else:
            print('WARNNING : most_similarで、 preprocessed_docsに含まれないドキュメント名が見つかった ' +  nearName + ' -- for --\t' + docName)
    if  similarl_count <= 0: # 先祖的or子孫的ライセンスが一つも見つかっていない場合、条件を緩めて登録
       for index, (nearName , similarl) in enumerate(similar_docs_top):
         if  (similarl_lower > similarl > similarl_extend ) and (nearName in preprocessed_docs): # 多重登録を避ける為の除外条件
                if  ( len(doc) <= len(preprocessed_docs[nearName]) ): 
                    if nearName not in docs_similar_tree:
                       docs_similar_tree[nearName] = []
                    docs_similar_tree[nearName].append((docName,similarl, len(preprocessed_docs[nearName]) - len(doc))) # 子孫的ライセンスとして登録
                else:
                    docs_similar_tree[docName].append((nearName,similarl,  len(doc) - len(preprocessed_docs[nearName]) )) # 先祖的ライセンスとして登録
                similarl_count += 1
                if similarl_count > 0:
                    break

print('docs_similar_tree.length', len(docs_similar_tree))
# 関連ドキュメントをconcatする。　類似ドキュメントの合流が多い場合を想定し、再帰的な深さ優先ではなく、横探索する。
def  tree_related_docs(docs_similar_tree, past_docs, cur_docNames,tree_related_docs_debug):
    related_docs = []
    if (len(cur_docNames) > 0):
        current_level_docNames = [cur_docname[0]  for cur_docname in cur_docNames  ] # if all(cur_docname[0] != item for item in past_docs)
        loopCount = 0
        while len(current_level_docNames) > 0:
            loopCount = loopCount + 1
            if loopCount > 100:
                tree_related_docs_debug = True
            if tree_related_docs_debug:
               print( 'tree_related_docs-current_level_docNames', current_level_docNames, related_docs )
            next_level_docNames = []
            for current_level_docName in current_level_docNames:
                if tree_related_docs_debug:
                    print( 'tree_related_docs-docs_similar_tree[current_level_docName] ', current_level_docName, docs_similar_tree[current_level_docName] )
                for  next_level_docName in docs_similar_tree[current_level_docName]:
                    if tree_related_docs_debug:
                       print( 'tree_related_docs-next_level_docName ', next_level_docName )
                    if (next_level_docName[0] not in past_docs) and (next_level_docName[0] not in  related_docs) and (next_level_docName[0] not in next_level_docNames):
                         next_level_docNames.append(next_level_docName[0])
            related_docs.extend(next_level_docNames)
            if tree_related_docs_debug:
               print( 'tree_related_docs-next_level_docNames', next_level_docNames, related_docs )
            current_level_docNames = next_level_docNames
    if tree_related_docs_debug:
         print( 'tree_related_docs returns', past_docs, cur_docNames, related_docs )
    return related_docs

def get_uniq_names(docs_similar):
    seen = []
    return [x for x in docs_similar if (all(x[0] != s[0] for s in seen)) and not seen.append(x)]

for nearName, docs_similar in docs_similar_tree.items():
    docs_similar_tree[nearName] = get_uniq_names(docs_similar)

# 同一条文のlicence documentをグループをマージする
more_mearge_need = True
more_mearge_counter = 0
same_text_groups_seq_num  += 1
while more_mearge_need and (more_mearge_counter <30):
    more_mearge_counter += 1
    more_mearge_need = False
    for cur_groups_seq_num, cur_groups_names  in same_text_groups_names.items(): # 番号順にマージ
        cur_groups_seq_list = [same_text_groups_seq.get(related_docName,same_text_groups_seq_num) for related_docName in cur_groups_names]
        if len(cur_groups_seq_list) > 1:
            min_groups_seq = min(cur_groups_seq_list)
            max_groups_seq = max(cur_groups_seq_list)
            if  min_groups_seq < max_groups_seq:
              merge_groups_names = cur_groups_names
              for related_docName_seq in cur_groups_seq_list:
                  if related_docName_seq < same_text_groups_seq_num:
                       merge_groups_names.extend(same_text_groups_names[related_docName_seq])
                       same_text_groups_names[related_docName_seq] = []
              merge_groups_names = list(set(merge_groups_names))
              same_text_groups_names[min_groups_seq] = merge_groups_names
              for related_docName in merge_groups_names:
                  same_text_groups_seq[related_docName] = min_groups_seq
              more_mearge_need = True

# 同一条文のlicence documentをグループのマージ結果の索引を再作成する
same_text_groups_names = {}
grouped_doc_names = {}
for cur_groups_name, cur_groups_seq_num in same_text_groups_seq.items(): # 番号順に転地
      if  cur_groups_seq_num not in same_text_groups_names:
          same_text_groups_names[cur_groups_seq_num] = []
      same_text_groups_names[cur_groups_seq_num].append(cur_groups_name)
      grouped_doc_names[cur_groups_name] = 0 - cur_groups_seq_num

for cur_seq_num, cur_group_names in  same_text_groups_names.items():
    cur_group_names = sorted(cur_group_names, key=lambda item: ([v for k,v in licenseSortOrder.items() if item.startswith(k + '/')][0], item))
    same_text_groups_names[cur_seq_num] =  cur_group_names
    if  len(cur_group_names) > 1:
        for licName in  cur_group_names[1:]:
            license_alias[licName.lower()] = cur_group_names[0]

save_license_alias(license_alias)

# 単段の関係が多段の関係から導出できる冗長な関係を削除する
for nearName, docs_similar in docs_similar_tree.items():
    tree_related_docs_debug = False # (nearName == 'spdx/OGL-UK-2.0') # False # (len(docs_similar) > 10)
    if  tree_related_docs_debug:
        print('docs_similar before',nearName,len(docs_similar))
    related_docs = []
    for related_docName,similarl, len_dif  in docs_similar:
        if  same_text_groups_seq.get(nearName,-1) == same_text_groups_seq.get(related_docName,-2) :
            related_docs.append( related_docName)
        elif (related_docName > nearName) and any(nearName == item[0] for item in docs_similar_tree[related_docName]): # 相互参照は除外する
            related_docs.append( related_docName) #  
        else:
            related_docs.extend(tree_related_docs(docs_similar_tree, [nearName, related_docName] , [(related_docName,similarl, len_dif)], tree_related_docs_debug))
    docs_similar_tree[nearName] = get_uniq_names([uniq_doc for uniq_doc in docs_similar if (uniq_doc[0] not in related_docs)])
    if  tree_related_docs_debug:
       print('updated docs_similar_tree[nearName] ', docs_similar_tree[nearName], docs_similar,  related_docs)
print('docs_similar_tree size=', len(docs_similar_tree))

docs_related_tree = {} # 該当ドキュメントから派生した、ドキュメントの一覧
for nearName, docs_similar in docs_similar_tree.items():
    if nearName not in docs_related_tree:
       docs_related_tree[nearName] = []
    for docName, similarl, len_diff in docs_similar:
        if docName not in docs_related_tree:
            docs_related_tree[docName] = []
        docs_related_tree[docName].append((nearName,similarl, len_diff))

for docName, similar_docs_names  in docs_related_tree.items():
      docs_related_tree[docName] = get_uniq_names(similar_docs_names) # unit
print('docs_related_tree size=', len(docs_related_tree))

tail_rank_docs = [] # 最も長いドキュメント
for nearName, docs_similar in docs_similar_tree.items():
    if (len(docs_related_tree.get(nearName,[])) <= 0) and (same_text_groups_seq.get(nearName,0) > 0):
        related_docs = [docName for docName in  tree_related_docs(docs_similar_tree, [], docs_similar_tree.get(nearName,[]) , False) if docName not in same_text_groups_seq] 
        tail_rank_docs.append((nearName, len(related_docs), related_docs))

tail_rank_docs = sorted(tail_rank_docs, key=lambda x:(x[1], x[0]))
for index,(nearName,doc_count, related_docs) in  enumerate(tail_rank_docs):
    if nearName not in grouped_doc_names:
        uniq_docs = [nearName]
    else:
        uniq_docs = []
    uniq_docs.extend([doc_name for doc_name in related_docs if doc_name not in  grouped_doc_names])
    tail_rank_docs[index] = (nearName,doc_count, uniq_docs) #  (キュメント名、 関連ドキュメントの数 （len(uniq_docs)に非ず）、ドキュメント）

tail_rank_docs = sorted(tail_rank_docs, key=lambda x:(len(x[2]), x[1],  x[0]))
print('tail_rank_docs size=', len(tail_rank_docs))

root_rank_docs = [] # 最も短いドキュメント
for docName, near_doc_name in docs_related_tree.items():
    if (len(docs_similar_tree.get(docName,[])) <= 0) and ((len(near_doc_name) > 0) or (docName not in same_text_groups_seq)):
        root_rank_docs.append(docName)

print('root_rank_docs size=', len(root_rank_docs))

dot = open('data/lic_graph.dot', 'w',  encoding="utf-8")
dot.write('digraph LicenseGraph {\n')
dot.write('  newrank = true;\n')
dot.write('  ratio = "auto" ;\n')
# dot.write('  mincross = 2.0 ;\n')
# layout="dot"にすると、下記エラーで、fgraphivizで描画できなかった！！
# Approved/SmartBear - On PremSoftware Licensing Terms of Use 1
# libpath/.\shortest.c:324: triangulation failed
# libpath/.\shortest.c:192: source point not in any triangle
# Error: in routesplines, Pshortestpath failed
# layout="sfdpにすると、subgrraphの罫線が表示されない
dot.write(' graph [layout="fdp", rankdir=LR, overlap=false]\n')
dot.write(' node [shape=box, width=1];\n')
dot.write(' edge [style=solid, color=darkgoldenrod, width=1];\n')

dot.write('{rank=same "' +'" "'.join(root_rank_docs) + '" }\n')
# dot.write('{rank=same "' +'" "'.join(tail_rank_docs) + '" }\n')
for gruop_seq, related_docs in same_text_groups_names.items(): # 同一条文のグループを出力
  if len(related_docs) > 1:
      dot.write('    subgraph cluster_same_texts_' + str(gruop_seq) + ' { style=dashed;\n')
      if  len(pickUp_dict.get(related_docs[0], '')) > 0:
          dot.write('        color=magenta; fillcolor=lightpink;\n')
      else:
          dot.write('        color=blue;\n')
      dot.write('        label="' + related_docs[0]+ ' similarl groups count=' + str( len(related_docs)) +  '";\n')
  for docName in related_docs:
          if docName !=  related_docs[0]:
              similarl = model.docvecs.similarity(related_docs[0],docName)
              if similarl >= similarl_upper:
                  edge_color = "color=lightblue, fontcolor=lightblue,"
              elif similarl >= similarl_lower:
                 edge_color =  "color=lightpink, fontcolor=lightpink,"
              else:
                 edge_color =  "color=red, fontcolor=crimson,style=bold," # ドキュメント内容が似ていない
              dot.write('      "' + related_docs[0]   + '" -> "' + docName  +
               "\" [constraint=false,dir=both," +  edge_color + " label=\"{0:.3f}{1:+d}\"];\n".format(round(similarl,3),
                  len(preprocessed_docs[docName]) - len(preprocessed_docs[related_docs[0]])))
          notcies_items = license_notices.get(license_alias.get(docName.lower(),''), []) +  license_notices.get(docName[9:], []) #research/
          if len(notcies_items) > 0:
              notcies_text = '\\n' + ','.join(notcies_items)
          else:
              notcies_text = ''
          if  len(pickUp_dict.get(docName, '')) > 0:
             doc_color = ',color=magenta, style=filled, fillcolor=lightpink;'
          elif docName[0:9] == 'research/':
             doc_color = ',color=red'
          else:
             doc_color=''
          dot.write('   "' + docName + '"  [label="' + docName + notcies_text + '"'  + doc_color + '];\n')
  if len(related_docs) > 1:
      dot.write('    }\n')

# for index,(nearName,doc_count, related_docs) in  enumerate(tail_rank_docs): # 関連ドキュメントのグループを出力
#   subgrouped_docs = [docName for docName in related_docs if  (docName not in  grouped_doc_names)]
#   if len(subgrouped_docs) > 1:
#     dot.write('    subgraph cluster_' + str(index) + ' { style=dashed; color=azure3; fontcolor=antiquewhite3;\n')
#     dot.write('        label="' + subgrouped_docs[0]+ ' related groups count=' + str(doc_count) +  '";\n')
#     for docName in  subgrouped_docs:
#             grouped_doc_names[docName] = index
#             notcies_items = license_notices.get(license_alias.get(docName.lower(),''),[]) +  license_notices.get(docName[9:], []) #research/
#             if len(notcies_items) > 0:
#                 notcies_text = '\\n' + ','.join(notcies_items)
#             else:
#                 notcies_text = ''
#             if  len(pickUp_dict.get(docName, '')) > 0:
#                  doc_color = ',color=magenta, style=filled, fillcolor=lightpink;'
#             elif docName[0:5] != 'spdx/':
#                 doc_color = ',color=red'
#             else:
#                 doc_color=''
#             dot.write('   "' + docName + '"  [label="' + docName + notcies_text + '"'  + doc_color + '];\n')
#     dot.write('    }\n')
for docName, similar_docs_names  in docs_related_tree.items():
    if (docName not in  grouped_doc_names): #  dot.nodeは、subgraphと排他的に出力。
        notcies_items = license_notices.get(license_alias.get(docName.lower(),''), []) +  license_notices.get(docName[9:], []) #Approved/ research/
        if len(notcies_items) > 0:
            notcies_text = '\\n' + ','.join(notcies_items)
        else:
            notcies_text = ''
        if  len(pickUp_dict.get(docName, '')) > 0:
             doc_color = ',color=magenta, style=filled, fillcolor=lightpink;'
        elif docName[0:5] != 'spdx/':
            doc_color = ',color=red'
        else:
            doc_color=''
        dot.write('   "' + docName + '"  [label="' + docName + notcies_text + '"'  + doc_color + '];\n')
    for nearName, similarl, len_diff in similar_docs_names:
         dot.write('      "' +docName   + '" -> "' + nearName  + "\" [label=\"{0:.3f}{1:+d}\",fontcolor=chocolate];\n".format(round(similarl,3), len_diff ))

dot.write('}\n')
dot.close()
