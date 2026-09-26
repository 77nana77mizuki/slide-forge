# レイアウト & コンポーネント カタログ

完全な実例は `assets/examples/sample.src.html`（16 枚・全レイアウト・全アニメーション）。迷ったらそこからコピーする。
写真・アイコンの配置パターン（`media-bg`, `frame`, `photo-card`, `icon-row`, `ico`）は visuals.md §6。

## 目次
1. 基本ルール（ステージ・余白・禁止事項）
2. 内容 → レイアウトの選び方
3. レイアウト別スニペット（L-title 〜 L-image）
4. コンポーネント（points / cards / stats / bars / donut / timeline / flow / compare / quote / code / table）
5. 修飾クラス・トークン
6. 独自レイアウトを作るとき（L-free）

---

## 1. 基本ルール
- ステージは **1920×1080 固定**。px で設計してよい（画面に合わせて全体が拡縮される）。レスポンシブ（メディアクエリで並べ替え）は禁止。
- スライドは `<section class="slide L-xxx">`。表示切替は runtime が行う。**`display:none` でスライドを隠さない**。
- 余白（`--pad-x:136px`, `--pad-y:112px`）の内側に収める。はみ出させたい装飾は `.bg` か `.bleed` クラスで明示。
- 文字サイズ下限: 本文 28px、注釈・出典 20px（check.py が 20px 未満をエラーにする）。
- 1 スライドの見出しは 1 つ（`h2.headline` か `.hero` / `.statement`）。
- 色は必ずトークン（`var(--accent)` など）。直書きの色はテーマ切替で破綻する。文字色に accent を使うときは `var(--accent-ink)`（背景・線は `--accent`）。
- 画像は相対パスで書けば build が base64 で同梱する（8MB 超は除く）。`alt` 必須。

## 2. 内容 → レイアウト
| 伝えたいこと | レイアウト | 補足 |
|---|---|---|
| 表紙 | L-title | `data-chrome="off"` |
| 章の区切り | L-section | `invert` を付けると反転色 |
| 一言で言い切れる主張 | L-statement | 最強のレイアウト。迷ったらこれ |
| 3〜4 個の要点 | L-bullets | `points` / `points numbered` / `points big` |
| 文章＋図や画像 | L-split | `wide-left` / `wide-right` |
| 並列の概念 3〜4 個 | L-cards | `--cols` で列数 |
| 印象づけたい数字 | L-stats | 1〜4 個。`data-count` でカウントアップ |
| 量の比較 | L-chart | bars（横）/ cols-chart（縦）/ donut |
| 時系列・手順 | L-timeline / L-flow | flow は `data-step` で 1 段ずつ |
| 対比（前後・案A/B） | L-compare | 右側 `.after` が強調色 |
| 引用・格言 | L-quote | `invert` と相性が良い |
| コード説明 | L-code | `.ln.hl` で行ハイライト |
| 表 | L-table | 5 行×4 列程度まで。超えたら reading 密度か分割 |
| 写真を全面に | L-image | `.overlay` にキャプション |
| 締め・お願い | L-closing | 行動を促す一文 |

## 3. レイアウト別スニペット

### L-title
```html
<section class="slide L-title" data-chrome="off">
  <div class="kicker" data-anim="fade">Engineering Strategy</div>
  <h1 class="hero" data-anim="chars">来期は「品質を<br>仕組みで守る」</h1>
  <p class="lede" data-anim="up">技術部 全体会議</p>
  <div class="meta" data-anim="fade"><span>2026.10.01</span><span>山田 太郎</span></div>
</section>
```
### L-section
```html
<section class="slide L-section invert" data-transition="wipe">
  <div class="sec-no" data-anim="from-left">02</div>
  <h2 data-anim="up">仕組み</h2>
</section>
```
### L-statement
```html
<section class="slide L-statement">            <!-- center を足すと中央揃え -->
  <div class="kicker" data-anim="fade">Principle</div>
  <p class="statement" data-anim="up">見出しで話が通れば、<span data-anim="mark" data-delay="900">資料はもう半分できている</span>。</p>
</section>
```
### L-bullets
```html
<section class="slide L-bullets">
  <div class="head"><div class="kicker" data-anim="fade">Agenda</div>
    <h2 class="headline" data-anim="up">今日お伝えする 3 つのこと</h2></div>
  <div class="body">
    <ol class="points numbered big" data-stagger="up"><li>…</li><li>…</li><li>…</li></ol>
  </div>
</section>
```
補足行: `<li>要点<span class="sub">補足説明</span></li>`

### L-split
```html
<section class="slide L-split wide-right">
  <div class="head"><h2 class="headline" data-anim="up">…</h2></div>
  <div class="col" data-anim="from-left"><ul class="points">…</ul></div>
  <div class="col" data-anim="from-right" data-delay="200">
    <div class="frame" style="height:560px"><img src="img/screen.png" alt="…"></div>
  </div>
</section>
```
### L-cards
```html
<div class="cards" style="--cols:3" data-stagger="up">
  <div class="card"><div class="tag">01</div><h3>見出し</h3><p>説明（2 行まで）</p></div>
  <div class="card hl">…</div>                  <!-- 強調は 1 枚だけ -->
</div>
```
### L-stats
```html
<div class="stats" style="--cols:3" data-stagger="up">
  <div class="stat hl"><div class="value" data-count>58<span class="unit">%</span></div><div class="label">設計起因の手戻り</div></div>
</div>
```
`data-count` は要素内の最初の数字をカウントアップ（小数・桁区切り対応、`data-count-from` で開始値）。

### L-chart
```html
<div class="bars">                                   <!-- --v は 0〜1 の比率 -->
  <div class="bar hl" style="--v:.95"><span class="k">A 案</span><div class="track"><div class="fill"></div></div><span class="v" data-count>95%</span></div>
</div>
<div class="cols-chart">                             <!-- 縦棒 -->
  <div class="col-bar hl" style="--v:.8"><span class="v">80</span><div class="fill"></div><span class="k">2026</span></div>
</div>
<div class="donut" style="--v:68"><span>68%</span></div>   <!-- --v は 0〜100 -->
```
棒は左から順に自動で伸びる。凡例より**直接ラベル**、強調したい 1 本だけ `hl`。複雑なグラフはインライン SVG（`data-anim="draw"` で線が描かれる）。

### L-timeline / L-flow
```html
<div class="timeline grow" style="--cols:4;align-content:center" data-stagger="up" data-stagger-gap="160">
  <div class="t"><div class="when">2026 Q1</div><h3>…</h3><p>…</p></div>
</div>
<div class="flow grow" style="align-items:center">
  <div class="node" data-step><h3>収集</h3><p>…</p></div>
  <div class="arrow" data-step></div>
  <div class="node hl" data-step><h3>検証</h3><p>…</p></div>
</div>
```
flow のノードは 4 つまで（それ以上は 2 枚に分ける）。ノード内の説明は 12 字程度。

### L-compare
```html
<div class="compare">
  <div class="side" data-anim="from-left"><div class="label">いま</div><h3>…</h3><ul class="points">…</ul></div>
  <div class="side after" data-anim="from-right" data-delay="350"><div class="label">これから</div><h3>…</h3><ul class="points">…</ul></div>
</div>
```
### L-quote
```html
<section class="slide L-quote invert">
  <blockquote class="quote" data-anim="blur">…</blockquote>
  <p class="quote-by" data-anim="fade">— 発言者、出典</p>
</section>
```
### L-code
```html
<pre class="code"><span class="ln">…</span><span class="ln hl">強調行</span><span class="ln dim">薄い行</span></pre>
```
構文色: `.k`(キーワード) `.s`(文字列) `.f`(関数/属性) `.n`(数値) `.c`(コメント)。1 行 60 字・15 行まで（はみ出すと check がエラー）。

### L-table
```html
<table class="tbl"><thead><tr><th>項目</th><th class="n">数値</th></tr></thead>
<tbody><tr><td>…</td><td class="n">1,200</td></tr><tr class="hl">…</tr></tbody></table>
```
### L-image
```html
<section class="slide L-image">
  <img src="img/hero.jpg" alt="…">
  <div class="overlay"><h2 class="headline">…</h2><p class="caption">…</p></div>
</section>
```

## 4. 共通パーツ
| クラス | 用途 |
|---|---|
| `.kicker` | 見出し上の小さなラベル（英字・章名） |
| `.headline` / `.hero` / `.statement` | 見出し（中・特大・主張） |
| `.lede` | リード文（1〜2 文） |
| `.mark` | マーカー強調（静的）。動かすなら `data-anim="mark"` |
| `.accent` / `.muted` / `.small` / `.num` | 色・サイズ・数字書体 |
| `.source` | 出典（スライド左下に固定） |
| `.pill` `.frame` `.rule` | タグ・画像枠・区切り線 |
| `.grid-2` `.grid-3` `.row` `.stack` `.grow` `.center` | 汎用レイアウト |

## 5. スライド修飾
| 属性・クラス | 効果 |
|---|---|
| `class="invert"` | テーマの反転配色（章扉・引用に） |
| `class="accent-bg"` | アクセント色の背景（1 デッキ 1〜2 枚まで） |
| `data-chrome="off"` | ページ番号・フッター・進捗バーを隠す |
| `data-transition="…"` | このスライドへの遷移（motion.md 参照） |
| `data-auto="off"` | 自動の時間差をやめ、全要素を同時に出す |
| `data-step-mode="focus"` | 新しいステップが出ると前のステップを薄くする |

## 6. 独自レイアウト（L-free）
カタログに合わないときは `L-free` + デッキ CSS（`<style>`）で組む。ルール:
- グリッドは 1920×1080 の px で。`--pad-x` / `--pad-y` を守る。
- テーマトークンだけで色を指定（`--bg --fg --muted --accent --accent-ink --surface --surface-2 --line`）。
- 図解はインライン SVG を推奨（`viewBox` を使い、`stroke="currentColor"` や `var(--accent)` で配色）。
- 文字と重なってはいけない装飾図形（CSS で描いたカード・イラスト等）には `class="solid"` か CSS で `--solid: 1` を付ける。check.py が文字との衝突・はみ出しを検出する（`img` は自動で対象）。
- 作ったら必ず check.py で重なり・はみ出しを確認し、スクリーンショットを見る。
- **予約済みのクラス名を自作 CSS に使わない**: `.bg`（全面の背景レイヤー＝position:absolute; inset:0 になる）・`.bleed`・`.frame`・`.card`・`.track`・`.stat` など。色見本を `.sw.bg` と書いて全面に広がり消えた例がある → `s-bg` のように接頭辞を付ける
- **わざとはみ出す帯・背景演出**（流れる帯、流れ星、波紋）は、はみ出す要素を `.bleed` の中に置く（check の clip 判定から外れる）。ループ用に複製した中身には `aria-hidden="true"`（文字量の判定から外れる）。一覧として読ませない文字の塊は `data-density-skip`
- 小さい画像（原寸 300px 未満のアイコンなど）は原寸の 1.2 倍までで表示する（`low-res` 警告）
- 表紙の装飾アイコンは見出しの右端から十分離す（`text-over-graphic`）。長い見出しは最終行の句点まで伸びる
