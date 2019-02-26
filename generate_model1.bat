del %~dp0\data\doc2vec.model
Python "%~dp0\doc_similality1_similar2.py"
del %~dp0\data\lic_graph.dot.svg
"C:\Program Files (x86)\Graphviz2.38\bin\dot" -Tsvg -O %~dp0\data\lic_graph.dot
