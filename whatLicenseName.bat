@rem 一つのファイルを入力として、類似するテキストのライセンス名を、類似度の高い順に出力するコマンド
@rem usage : whatLicenseName ライセンスのファイルパス
Python "%~dp0\find_similal_doc_from_dic3.py"  %*

