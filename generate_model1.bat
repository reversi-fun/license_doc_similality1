del %~dp0\data\doc2vec.model
Python "%~dp0\doc_similality1_similar2.py"
del %~dp0\data\lic_graph.dot.svg
dot -Tsvg -O %~dp0\data\lic_graph.dot
Python "%~dp0\licenses_names.py"
