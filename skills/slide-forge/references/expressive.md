# 表現の拡張（v1.7）— グラフ・図・ズーム・コード・比較・地図・文字・3D

実例: `assets/examples/fx/fx.src.html`（16 枚。下の 10 種すべて）。迷ったらそこからコピーする。
どれも **「話す順に出す」「主役の動きは 1 つ」** の原則は変わらない（motion.md §1）。1 スライドに 2 種類以上を重ねない。

## 目次
1. 注釈付きグラフ（`data-mock="chart"`）とグラフの変形
2. ズームキャンバス（`.zoom-view`・`L-zoom`）
3. 手描きの注釈（`data-annotate`）
4. コードの変化（`data-codemove`）
5. データが流れる構成図・シーケンス図（`arch` / `seq`）
6. ベントーグリッド（`L-bento` / `.bento`）
7. 前後比較スライダー（`.ba-slider`）
8. 日本地図（`data-mock="japan"`）
9. キネティック文字（`data-anim="mask|words|type|scramble|slam|tracking"`）
10. 3D（`data-3d="globe|model|shape"`）
11. 共通の仕組み・検証・落とし穴

---

## 1. 注釈付きグラフ
データから直接描く。**グラフに結論を書き込む**（目標線・吹き出し・期間帯・強調）のが目的。数値の凡例読みをさせない。
```html
<script type="application/json" data-mock="chart">
{ "type": "bar", "font": 24, "w": 64, "h": 20, "unit": "%",
  "labels": ["4月","5月","6月","7月","8月","9月"],
  "series": [ {"name": "再配達率", "values": [12.1,12.8,13.5,14.2,18.4,16.9]} ],
  "highlight": ["8月"], "max": 24,
  "annotations": [
    {"type": "target", "value": 10, "label": "目標 10%"},
    {"type": "point", "at": "8月", "label": "猛暑で在宅率が低下", "dx": -7, "dy": -2.2, "step": true} ] }
</script>
```
| キー | 内容 |
|---|---|
| `type` | `bar`（縦棒）/ `hbar`（横棒・長いラベル向き）/ `line` / `area` / `scatter`（`points: [[x, y, "名前"]]`, `xlabel`, `xunit`） |
| `w` `h` `font` | 大きさ（em × font px）。**font は 22 以上**（目盛りは 0.85em、20px 未満にはならない） |
| `highlight` | 棒: 指定したラベルだけ色付き、他は灰色（「どこを見るか」を決める） |
| `sort` `top` | 棒: 並べ替え（`desc`/`asc`）と上位 N 件 |
| `series_steps` | 2 本目以降の系列をクリックで 1 本ずつ（系列 k は `data-step="k"`） |
| `annotations` | `target`（目標線）/ `band`（`from`〜`to` の期間帯）/ `point`（系列の点を丸で囲んで吹き出し。`dx` `dy` で吹き出し位置）/ `note`（`at`+`value` の位置に吹き出し）。`"step": true` か数値でクリック表示 |
| `values` | 値ラベルを出すか（既定: 棒 12 本以下なら出す） |

**グラフの変形（チャートモーフ）**: 同じ `id` と `"morph": true` のグラフを連続するスライドに置き、`data-transition="morph"` を付ける。棒と値ラベルが同じ要素として滑るので「並べ替えた」「上位だけ残した」「値が変わった」が伝わる（例: 1 枚目は地域順 → 2 枚目は `sort: desc, top: 4, highlight`）。

## 2. ズームキャンバス（Prezi 風）
大きな 1 枚のボード（既定 3840×2160）に領域を並べ、クリックごとにカメラが寄る。**全体像 → 部分**を往復する話に使う（工程・地図・システム全景）。
```html
<section class="slide L-zoom" data-chrome="off">
  <div class="zoom-view">
    <div class="zoom-canvas" style="width:3840px;height:2160px">
      <div class="zoom-region" data-zoom="1" style="left:300px;top:760px;width:850px;height:800px">
        <span class="zoom-no">01</span><h3>受付</h3><p>…</p>
        <p class="zoom-detail">寄ったときだけ見える詳細</p>
      </div>
      … data-zoom="2", "3" …
    </div>
  </div>
</section>
```
- `data-zoom` の番号順に寄る（クリック数 = 領域数）。スライドに入った直後は全体図。領域どうしの移動は途中で少し引く（`data-zoom-arc="off"` で直線）
- `.zoom-view` の属性: `data-zoom-end="overview"`（最後にもう 1 クリックで全体へ戻る）、`data-zoom-pad`（余白率）、`data-zoom-dur`（ms）、`data-zoom-export="last"`（PDF を最後の寄りにする。既定は全体図）
- 領域の中は普通の HTML。文字は**寄ったときの大きさ**で設計する（全体図では小さく見えるのが正しい。check は tiny-text を免除）
- `L-zoom` は全面キャンバス。`L-free` の中に `.zoom-view` を置けば枠付きの窓になる
- 領域間の線は `<svg>` をキャンバスに置き `class="zoom-link"` の path で描く

## 3. 手描きの注釈（rough-notation 風）
見出しや本文の語に、手で描いたような丸・下線・囲み・蛍光ペンを引く。**聴衆の目を 1 語に止める**ときだけ。
```html
<h2 class="headline">再配達は <span data-annotate="circle" data-annotate-step>8 月</span> に跳ね上がった</h2>
```
| 種類 | 用途 |
|---|---|
| `underline` | 結論の語 | 
| `circle` | 数字・1 語を囲む |
| `box` | 用語・キーワード |
| `highlight` | 蛍光ペン（文字の後ろに引かれる） |
| `strike` / `cross` | 旧案・やめること |
| `bracket` | 句の両端に括弧 |
- `data-annotate-step`（空 or 番号）でクリック時に描く。無ければ入場 0.9 秒後（`data-annotate-delay`）
- 色は `data-annotate-color="#…"`（既定はアクセント）。揺れは文字列から決まるので毎回同じ形（動画・PDF でも一致）
- 1 行に収まる短い語句に付ける（折り返す語句には付けない）。1 スライド 1〜2 か所まで

## 4. コードの変化（Shiki Magic Move 風）
同じコードの版を順に並べると、クリックごとに**変わらないトークンは滑って移動し、増えた部分だけが現れる**。差分説明・リファクタリング・API の拡張に。
```html
<div class="code codemove" data-codemove data-lang="ts" data-file="delivery.ts">
<pre data-v>…版 1…</pre>
<pre data-v data-hl="4">…版 2（4 行目を強調）…</pre>
<pre data-v data-hl="1,5-6" data-focus="5-6">…版 3（5–6 行以外を薄く）…</pre>
</div>
```
- 色分けは自動（`data-lang`: js/ts/py/sql/go/sh）。`<pre>` の中は `&lt;` などでエスケープして書く
- 高さは一番長い版に合わせて確保される（行数が増えても枠が跳ねない）
- 1 版の差分は 1〜3 行まで。全部変わるなら別スライド

## 5. データが流れる構成図・シーケンス図
**構成図（`arch`）** — ノードをグリッドに置くと、線は自動で直線／L 字に引かれ、**線の上を光の粒（データ）が流れる**。
```json
{ "font": 22, "cell": [15, 6.4],
  "nodes": [ {"id": "api", "label": "受付 API", "sub": "REST", "icon": "tabler:api", "x": 1, "y": 0, "hl": true},
             {"id": "db", "label": "注文 DB", "icon": "tabler:database", "x": 2, "y": 0, "kind": "db"},
             {"id": "map", "label": "地図サービス", "kind": "ext", "x": 3, "y": 1, "step": 2} ],
  "edges": [ {"from": "api", "to": "db", "label": "保存"},
             {"from": "db", "to": "map", "dashed": true, "flow": false, "step": 2} ] }
```
- `kind`: `box`（既定）/ `db` / `user`（丸い）/ `ext`（外部・破線）。`hl: true` で強調。`span` で横幅 2 マス以上
- 線: `label`、`dashed`、`flow: false`（粒を流さない）、`step`（クリックで出す）。往復の線は自動で少しずらす
- 粒は表示中のスライドだけで動き、PDF・reduced motion では出ない

**シーケンス図（`seq`）** — 登場者と、上から順のメッセージ。**メッセージは既定で 1 クリック 1 本**（`"step": false` で最初から表示）。`reply: true` は破線の戻り、`from == to` は自分への処理（ループ矢印）。

## 6. ベントーグリッド
大小のタイルで「主役 1 つ＋補足」を見せる。`--c` / `--r` で占めるマス数。
```html
<section class="slide L-bento">
  <h2 class="headline">刷新で変わる 5 つのこと</h2>
  <div class="bento" style="--cols:4" data-stagger="up">
    <div class="accent beam" style="--c:2;--r:2"><span class="b-kicker">再配達</span><span class="b-num" data-count>-40<small>%</small></span>
      <p class="b-text">…</p><i class="b-art" data-icon="tabler:truck-delivery"></i></div>
    <div><span class="b-kicker">通知</span><p class="b-title">到着 30 分前に通知</p></div>
    …
  </div>
</section>
```
- タイルの修飾: `.accent`（アクセント塗り）/ `.dark`（反転配色）/ `.beam`（縁を光が回る。Magic UI の Border Beam〔MIT〕の考え方）
- 中身の部品: `.b-kicker` `.b-title` `.b-num` `.b-text` `.b-art`（右下の大きな薄いアイコン）`.b-media`（上端まで広がる画像）`.b-foot`
- タイルは 5〜7 個まで。主役は 1 つ（2×2）。`.beam` も主役だけ

## 7. 前後比較スライダー
2 枚（画像・画面イメージ・任意の HTML）を重ね、境目をドラッグ／クリックで動かす。**Before → After の差を同じ枠で**見せる。
```html
<div class="ba-slider" data-compare="50" data-stops="88,12" data-labels="現行,新画面">
  <div data-density-skip>…Before（例: data-mock="app"）…</div>
  <div>…After…</div>
</div>
```
- 入場時に左端から `data-compare`（%）まで掃く（`data-sweep="off"` で無効）。`data-stops` の値へクリックごとに移動（値 = After が始まる位置。小さいほど After が多く見える）
- 発表中はマウスでドラッグできる（ドラッグはページ送りにならない）
- 2 枚は**同じ大きさ**にする（画面イメージなら width と widget の高さを揃える）。PDF は最後の位置
- 既存の `.compare`（左右 2 カラムの比較）とは別物

## 8. 日本地図（タイル地図）
47 都道府県を同じ大きさのマスで並べる。面積に引っ張られず、**件数の比較・拠点の位置**を見せられる。
```json
{ "font": 22, "tile": 2.7, "unit": "件", "levels": 5,
  "values": {"東京": 4210, "大阪": 2630, "福岡": 1560},
  "highlight": ["東京", "福岡"],
  "pins": [ {"pref": "福岡", "text": "拠点ハブ", "side": "bottom", "step": 1} ],
  "title": "都道府県別 再配達件数（9 月）" }
```
- 値は `levels` 段階の濃さ（アクセント色）。文字色はマスの濃さから自動で読みやすい方を選ぶ。凡例は左上
- 名前は「東京」「東京都」どちらでも可。`pins` は吹き出し（`side`: top/bottom/left/right）
- 地理的な形が必要な話（海岸線・距離）には向かない。その場合は画像か 3D の地球儀

## 9. キネティック文字（動画の文字効果をスライドへ）
| 値 | 動き | 向く場所 |
|---|---|---|
| `mask` | 行ごとに下から「せり上がる」（マスク） | 表紙・章扉の見出し |
| `words` | 単語ずつぼかしから現れる（日本語は形態素で分割） | リード文・問い |
| `type` | タイプライター（カーソル付き） | 締めの一文・コマンド |
| `scramble` | ランダムな文字が確定していく | 数値・コード・「計測値」 |
| `slam` | 大きく叩きつけて着地 | 1 語の主張 |
| `tracking` | 字間が広い状態から締まる | キッカー・英字の小見出し |
- どれも `data-delay` / `data-step` と組み合わせられる。1 スライドに 1 つ（`slam` + `scramble` のような主従の組合せまで）
- `type` の速さ `--type-gap`、`words` の間隔 `--word-gap` を style で変更可。長文には使わない（2 行まで）

## 10. 3D（three.js）
デッキに `data-3d` があるときだけ three.js（MIT, r186 ＋ GLTFLoader, 約 790KB）が同梱される。**表示中のスライドだけ描画**し、PDF では 1 コマを静止画で出す。
```html
<div class="globe" style="height:760px" data-3d="globe" data-focus="30,125" data-distance="4.1"
     data-points='[[33.59,130.40,"福岡"],[37.57,126.98,"ソウル"]]' data-arcs='[[0,1]]'></div>
<div style="height:620px" data-3d="model" data-src="model.glb" data-tint="accent"></div>
<div style="height:600px" data-3d="shape" data-shape="knot"></div>
```
- `globe`: 陸地はドット（Natural Earth 1:110m〔パブリックドメイン〕から作った 240×120 のマスク）。`data-points` は `[緯度, 経度, "ラベル"]`、`data-arcs` は点の番号の組（弧が伸び、光が往復）。`data-focus="緯度,経度"` を正面に、`data-spin="off"` で揺れを止める
- `model`: `.glb`/`.gltf` を `data-src` に（ビルド時に埋め込み）。`data-tint="accent"` でテーマ色の単色に、`data-spin`（rad/秒）`data-yaw` `data-pitch`（度）`data-scale`。**モデルのライセンスを credits.json に記録**（自作は `--own`、Poly Pizza/Sketchfab は作品ごとの CC ライセンス）
- `shape`: 装飾用の立体（`knot` / `ico` / `torus` / `sphere`）。背景の賑やかしに使いすぎない
- 色は CSS トークン（--accent / --fg / --muted / --surface）から取る。要素には必ず高さを与える
- WebGL が使えない環境では「3D preview unavailable」と出る。中に代替の `<img>` を置いてもよい

## 11. 共通の仕組み・検証・落とし穴
- 実装は `assets/runtime/slides-fx.js`（slides.js より前に読み込まれる）。クリックに連動する状態（ズーム・比較・コード）は、見えない**ステップマーカー**（`<i class="sf-mark" data-step>`）で数えるので、`data-step` の番号付けと混ぜて使える（ズームは `data-zoom-step`、コード版は `<pre data-step>` で番号を指定可）
- `?export`（PDF・check.py）は最終状態: コードは最後の版、比較は最後の位置、ズームは全体図、3D は静止 1 コマ、粒は非表示
- 動きの確認は `check.py --motion N`（ズーム・コード・比較はステップごとのコマで確認できる）。reduced motion では全て最終状態
- グラフ・図の文字は `--mk-font` 基準の絶対位置（テーマのフォントが変わっても位置はずれない）。文字が小さいと感じたら `font` を上げて `w`/`cell` を下げる
- クラス名の衝突に注意: 既存の `.compare` `.bar` `.hl` などと同じ名前を自作 CSS に付けない
