# OSS license document clustering tool

1. setups
1.1 requirements
  * OS: Windows7 or Windows10
  * install Graphviz version 2.38 or later(for windows). (It run in generate_model1.bat only)
  * install Anaconda3
  * install Python3 modules:
     * gensim
     * sklearn
     * numpy
     * html5lib
  * update Python3 modules:
     * itemgetter, csv,fileinput,glob,io,json,urllib,xml

1.2 update data
    * download ./license-list-data-master from https://github.com/spdx/license-list-data
    * download ./FSF_texts  from https://www.gnu.org/licenses/license-list.html by using https://wking.github.io/fsf-api/ via get_fsf_license_text.py.
       ` Python ./get_fsf_license_text.py`
    * download ./OSI_texts from https://opensource.org by using get_OSI_license_text.py.
       ` Python ./get_OSI_license_text.py `

2. commands
2.1　ディレクトリからライセンス一覧を作成するコマンド
      ` FindAllLicensesInfo.bat many-oss-mixed_liceses_directory output-directory`

2.2　一つのファイル中のライセンス名を調べるコマンド
      `whatLicenseName　one-oss-license-text-file-name`

2.3 ライセンスの標本ファイルの追加後、機械学習データを更新するコマンド
      ` cd <this tools directory>`
      ` generate_model1.bat`

3. sample run
3.1 one oss-license text files similal license Names listing.
 
      `>whatLicenseName.bat own_texts\node_modules\protractor\node_modules\minimatch\LICENSE" `
      `
### doc2vec most_similar 32
    0.78657 research/node_modules/protractor/node_modules/minimatch/LICENSE
    0.78231 OSI/MIT License
    0.76353 research/pleiades-2018-12-java-win-64bit-jre_20181224/pleiades/eclipse/plugins/org.eclipse.m2e.maven.runtime.slf4j.simple_1.10.0.20181127-2120/about_files/slf4j-simple-LICENSE
    0.76173 research/pleiades-2018-12-java-win-64bit-jre_20181224/pleiades/eclipse/dropins/QuickJUnit/eclipse/plugins/org.mockito_1.8.5/mockito-license
    0.75950 Approved/MIT by contributers LICENSE
    0.75926 research/node_modules/protractor/LICENSE
    0.75711 Approved/MIT + COPYRIGHT License
    0.75562 research/node_modules/protractor/node_modules/mime-db/LICENSE
    0.75428 research/cucumber-sandwich.jar#/LICENSE
    0.75368 FSF/JSON
    0.75248 research/node_modules/protractor/node_modules/mime-types/LICENSE
    0.75240 Approved/MIT
    0.74460 Approved/MIT License(2).md
    0.74431 Approved/MIT + copyright LICENSE (4)
    0.74288 spdx/MIT
    0.73598 spdx/JSON
    0.73068 Approved/MIT LICENSE
    0.72749 Approved/MIT + X11 LICENSE
    0.72748 Approved/Expat
    0.72522 FSF/Expat
    0.72462 Approved/MIT License.md
    0.71862 spdx/MIT-0
    0.71149 spdx/MIT-feh
    0.71122 Approved/MIT for qhull benjamin Nortier
    0.70755 spdx/X11
    0.70636 FSF/X11License
    0.70634 OSI/NCSA Open Source License
    0.70434 research/cucumber-sandwich.jar#/objenesis-license
    0.70321 Approved/MIT by contributers LICENSE(1)
    0.69962 research/pleiades-2018-12-java-win-64bit-jre_20181224/pleiades/eclipse/dropins/EclipseRunner/eclipse/features/com.eclipserunner.feature_1.3.4/LICENSE
    0.69898 Approved/MIT + own products license
    0.69796 research/node_modules/protractor/node_modules/lodash/LICENSE
    `
-----------------------------------------------------------------------------
    `
### lda most_similar 316
    1.00000 spdx/Adobe-2006
    1.00000 spdx/Bison-exception-2.2
    1.00000 spdx/BitTorrent-1.0
    1.00000 spdx/BitTorrent-1.1
    1.00000 spdx/Bootloader-exception
    1.00000 spdx/Borceux
    1.00000 spdx/BSD-1-Clause
    1.00000 spdx/BSD-2-Clause-FreeBSD
    1.00000 spdx/BSD-2-Clause-NetBSD
    1.00000 spdx/BSD-2-Clause-Patent
    1.00000 spdx/BSD-2-Clause
    1.00000 spdx/BSD-3-Clause-Attribution
    1.00000 spdx/BSD-3-Clause-Clear
    1.00000 spdx/BSD-3-Clause-LBNL
    1.00000 spdx/BSD-3-Clause-No-Nuclear-License
    1.00000 spdx/BSD-4-Clause
    1.00000 spdx/CPAL-1.0
    1.00000 spdx/dvipdfm
    1.00000 spdx/GPL-1.0-or-later
    1.00000 spdx/GPL-3.0-only
    1.00000 spdx/ICU
    1.00000 spdx/Intel-ACPI
    1.00000 spdx/LGPL-2.0-or-later
    1.00000 spdx/LGPLLR
    1.00000 spdx/LPPL-1.2
    1.00000 spdx/LPPL-1.3a
    1.00000 spdx/MakeIndex
    1.00000 spdx/mif-exception
    1.00000 spdx/MirOS
    1.00000 spdx/MPL-1.1
    1.00000 spdx/MPL-2.0
    1.00000 spdx/MS-RL
    --- End of similal license names ---
`

3.2 many one oss-licenses concatinated text files similal license Names listing.
      ` whatLicenseName.bat own_texts\elasticsearch-6.2.3\NOTICE.txt`

#      doc2vec most_similar 32
      0.93149 research/elasticsearch-6.2.3/NOTICE
      0.92931 Approved/GPL-3.0 + LGPL-2.1 + MPL-2.0 + CC0-1.0 + Unicode + ICU + BSD-2-Clause + ANTLR-PD + Apache-2.0 + EPL-1.0 + DL-1.0 + CPL-1.0 + MIT + mecab-ipadic-2.7.0-20070801 + HdrHistogram Licensed NOTICE
      0.49900 Approved/LGPL-3.0 + Apaache-2.0 + BSD-3-Clause for PMD InfoEther
      0.49761 research/elasticsearch-6.2.3/lib/lucene-spatial-7.2.1.jar#/META-INF/LICE
      ---- omit some lines
#     lda most_similar 105
      0.99960 research/elasticsearch-6.2.3/modules/reindex/httpcore-4.4.5.jar#/META-INF/NOTICE
      0.99806 Approved/GPL-2.0 + MIT license NOTICE.js
      0.91766 Approved/Apache-2.0 + BSD-3-Clause + MIT NOTICE
      0.90385 Approved/-See EXCEPTION NOTICE
      0.90385 Approved/0BSD + 1 provided by Auther Lucent in Python license
      0.90385 Approved/ACDL-1.0
      0.90385 Approved/Apache licensed NOTICE
      0.90385 Approved/Apache-1.1 in comments(2)
      0.90385 Approved/Apache-2.0 + BSD 3-Clause
      0.90385 Approved/Apache-2.0 + BSD-2-Clause + BSD-3-Clause + LGPL-2.1 + CC-BY-SA-4.0 + mecab Notice
      0.90385 Approved/Apache-2.0 + NIST AES NOTICE
      0.90385 Approved/MIT for 3 Authers LICENSE.md

      In above case  `lda most_similar' is better.



   
