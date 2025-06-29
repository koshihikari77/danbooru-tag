@https://danbooru.donmai.us/wiki_pages/tag_groups 
このページのから連なるタググループの情報をデータ化したい

tag groupとtagは階層構造になっている
階層構造は以下の2種類
  1ページ内でhtmlとしてhタグやリストで階層構造になっている
  (例)
  h1 abc
  h2 bbb
    - 1
    - 2
    - 3
  ※この場合h1 <- h2 <- 1(2,3も)で階層構造
  項目がリンクになっておりその先も項目がある。リンクによる階層構造
  (例) tag group1 <- tag group2 <- tag group3 <- tag


これらを
  - tag group, tagの親子関係がわかるようにデータ化
  - tagから親のパスがわかる
  - tag groupから属しているtag(直接属しているtagだけでいい)

ようにしたい。

目的としては
- ある画像についているtagから人物によって変化するもの(目の色、髪の色、胸の大きさなど)を取り除いて別の人物にいれかえるみたいなことがしたい

Copyrights, artists, projects and media以下は無視していい
beautiflsoup4では403になるみたいなのでseleniumで

pybooruていうライブラリがあるらしい
スクレイピングは403になりがちなのでapiでなんとかなるなら

データ
- tag, tag groupは小文字にする
- 重複は削除
  - 小文字にした結果重複する場合
  - pathが複数あり複数登録される場合
- tagのしたにtagがリストになっているものがとれていない。こういうのはtagでもありtag groupでもあるあつかいにする。(例　areolae の下のlarge areolae)
- 文字にtag groupてはいってなくてもしたにリストがある場合はtag group扱い
  - したにリストがある -> tag group
  - したにリストがある,リンク, 名前にtag groupがはいっていない -> tag かつ tag group
  - したにリストがある,リンクではない, 名前にtag groupがはいっていない -> tag group
- tag or 見出し のしたにtag groupがある場合がある
  - breasts 
     - tag group:breasts
  みたいにtag groupがついてるだけならもとのtag(ここではbreasts)にまとめる

スクレイピング
- wikiのページ(https://danbooru.donmai.us/wiki_pages/tag_groups)じゃなくてpostのページ(https://danbooru.donmai.us/posts?tags=tag_groups)をスクレイピングすることにしよう
- postのページのリンクはwikiのページになってるけどpostのページに変換してスクレイピング
- 名前にList ofもTag groupも入ってないリンクはそれ以上追わない(リンク先にいかないようにしよう)
