# モーション（アニメーション）設計ガイド

## 目次
1. 原則 — 動きは「どこを見るか」の案内
2. 語彙: data-anim / data-stagger / data-step / data-morph / data-count
3. タイミングの決まり
4. スライド遷移 (View Transitions)
5. レシピ集
6. やってはいけないこと
7. 外部ライブラリ（Anime.js など）で動かす
8. 確認方法

---

## 1. 原則
1. **話す順に出す** — 聴衆は出た瞬間に読む。まだ話していない情報を先に見せない（`data-step`）。
2. **主役の動きは 1 スライド 1 つ** — 数字のカウントアップ、グラフの伸長、マーカー、モーフのどれか 1 つを主役に。他は控えめな fade/up。
3. **動きに意味を持たせる** — 左→右は時間・流れ、下→上は成長・積み上げ、ワイプは「切り替わり」、モーフは「同じものが続いている」。
4. **一貫性** — 同じ種類の要素は同じ動き。見出しは常に `up`、キッカーは `fade`、など。
5. **reduced motion を尊重** — OS で「視差効果を減らす」が有効な場合、runtime が自動で最終状態を即表示する（追加作業不要）。

## 2. 語彙
| 属性 | 値 | 説明 |
|---|---|---|
| `data-anim` | `up` `down` `from-left` `from-right` `fade` `scale` `zoom` `pop` `blur` `wipe` `wipe-up` | 入場アニメーション |
| | `chars` | 1 文字ずつ（表紙の短い見出しだけに） |
| | `mark` | インラインのマーカーが引かれる（強調語に） |
| | `draw` | インライン SVG の線が描かれる（図解・折れ線） |
| `data-delay` | ms | 自動順序を無視して開始を指定（スライド入場からの時間） |
| `data-dur` | ms | 長さ（既定 700ms） |
| `data-stagger` | anim 名 | 子要素に同じ動きを時間差で付与（`data-stagger-gap` で間隔） |
| `data-step` | 空 or 数値 | クリックで出る要素。同じ数値は同時に出る |
| `data-step-mode="focus"` | （section か親に） | 新しい項目が出ると前の項目が薄くなる |
| `data-morph` | キー | 連続するスライドで同じキーの要素が移動・変形（マジックムーブ） |
| `data-count` | 空 or 目標値 | 数字のカウントアップ（`data-count-from`, `data-count-dur`） |
| `data-fit` | — | 枠からはみ出す文字を自動縮小（最後の安全網。常用しない） |

**自動シーケンス**: `data-delay` を書かなければ、スライド内の `data-anim` 要素は文書順に 110ms ずつずれて出る（最初は 140ms 後）。だから通常は delay を書かなくてよい。

## 3. タイミングの決まり
| 用途 | 長さ | 備考 |
|---|---|---|
| 小さな要素（ラベル、行） | 400–600ms | |
| 見出し・カード | 600–800ms | 既定 700ms |
| グラフ・カウント | 1100–1600ms | runtime の既定値 |
| 時間差 (stagger) | 60–160ms | 既定 90ms。5 個以上は 60ms に |
| スライド遷移 | 450–800ms | morph は 780ms |
- イージングは減速型（`--ease-out` = expo-out）。等速 (linear) とバウンスの多用は安っぽく見える。
- スライドに入ってから全要素が揃うまで **1.5 秒以内**。長いと話し始められない。

## 4. スライド遷移
deck-config の `"transition"` が既定、スライド単位で `data-transition` で上書き。
| 値 | 印象 | 使いどころ |
|---|---|---|
| `fade` | 静か・上品 | 既定。迷ったらこれ |
| `slide` | 前進感（戻る時は逆方向） | 手順・ストーリーの進行 |
| `rise` | 積み上げ | 結論に向かう終盤 |
| `zoom` | 深掘り | 詳細に入る時 |
| `wipe` | 場面転換 | 章扉（L-section）専用にすると効く |
| `morph` | 連続性 | `data-morph` 要素を持つ連続スライド |
| `none` | 即時 | 連続する図の差分比較 |
ルール: デッキの遷移は **2 種類まで**（既定 + 章扉用）。毎枚違う遷移は素人っぽい。

## 5. レシピ
**数字を印象づける**
```html
<div class="stat hl"><div class="value" data-count>1,284<span class="unit">件</span></div>…</div>
```
**話しながら 1 項目ずつ（前の項目は薄く）**
```html
<ol class="points numbered" data-step-mode="focus"><li data-step>…</li><li data-step>…</li></ol>
```
**キーワードを最後に強調**
```html
<p class="statement" data-anim="up">…<span data-anim="mark" data-delay="900">ここが核心</span>。</p>
```
**マジックムーブ（前のスライドの要素が次のスライドへ移動）**
```html
<section class="slide" data-transition="morph"> … <div class="badge" data-morph="kpi">98%</div> … </section>
<section class="slide" data-transition="morph"> … <div class="badge big" data-morph="kpi">98%</div> … </section>
```
キーは各スライド内で一意。モーフ要素自身には `data-anim` を付けない（移動が入場アニメーションの代わり）。

**線を描く図解**
```html
<svg viewBox="0 0 800 300" data-anim="draw" width="800">
  <path d="M0 250 L200 180 L400 200 L600 80 L800 40" fill="none" stroke="var(--accent)" stroke-width="6"/>
</svg>
```
**グラフ**: `.bars` / `.cols-chart` / `.donut` はスライド入場時（または親の data-anim 入場時）に自動で伸びる。追加の属性は不要。

## 6. やってはいけないこと
- 全要素に違う動きを付ける／1 枚に 15 以上の動き（build が警告）
- 1 スライド 7 クリック以上（build が警告 → 分割）
- 本文の長い段落に `chars`
- 回転・点滅・バウンスを内容と無関係に使う
- 遷移を毎枚変える
- `transform`/`opacity`/`filter`/`clip-path` 以外（width, top, margin など）をアニメーションさせる（カクつく）

## 7. 外部ライブラリ（Anime.js など）で動かす
属性で足りない動き（中心から広がる波、線の上を進む点）は Anime.js（MIT）を同梱してよい。置き場所・`deck:change` イベント・初期値の決まりは resources.md §5.4。**動く前の静止状態でも破綻しないこと**（check のスクリーンショットと reduced motion で見える状態）。確認は `--motion N` のコマ撮りで必ず行う。

## 8. 確認方法
- `python scripts/check.py deck.html --motion 5` → 5 枚目の入場を 0/120/300/550/900/1500/2600ms とステップごとに撮影し `motion-05-strip.png` にまとめる。**画像を見て**順番と揃うタイミングを確認する。
- 実際の動きを通しで見る/共有する: `python scripts/record.py deck.html` → webm（ffmpeg があれば mp4 も）。
