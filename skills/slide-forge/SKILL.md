---
name: slide-forge
description: Builds animated, single-file HTML presentation decks (16:9, keyboard/presenter/overview/PDF/video) with a story-first workflow — outline with claim headlines, visual theme previews, free-licence photo/illustration/icon sourcing with automatic credits, layout+motion components, and automated rendering QA (overflow, overlap, contrast incl. text on photos, density) plus screenshot review. Use when the user asks for slides, a presentation, a deck, a talk, a pitch, スライド, プレゼン資料, 発表資料, 登壇資料, HTMLスライド, or wants to convert notes/documents/PPTX into an animated web presentation, or to fix/improve an existing Slide Forge deck. Draws annotated charts that morph between slides, Prezi-style zoom canvases, hand-drawn annotations, code that animates between versions, architecture/sequence diagrams with flowing data, bento grids, before/after sliders, Japan prefecture maps, kinetic text and three.js 3D (globe/model) inside slides. Also makes short MP4s with Remotion × three.js from a storyboard — 3D globes, photos, and motion graphics (kinetic typography, stat rings, drawn steps, bar charts, Lottie, 20 transitions, light leaks) — use for 動画, 映像, モーショングラフィック, ティザー, オープニング映像, SNS 用動画.
---

# Slide Forge — 伝わるアニメーション付き HTML スライド

`SF` = この SKILL.md があるディレクトリ。スクリプトは `python3 $SF/scripts/<name>.py` で実行する（読まずに実行してよい。`--help` あり）。

## 前提（初回のみ）
```bash
pip install playwright pillow && python3 -m playwright install chromium
```
Node/npm があればオフライン用フォント埋め込みのフォールバックにも使われる（任意）。

## 核となる考え方
1. **1 スライド 1 メッセージ。見出しは主張で書く**（トピック名ではなく結論）。
2. **構成 → 見た目 → 動き → 検証** の順。見た目から始めると中身が薄くなる。
3. **動きは視線の案内**。話す順に出す。主役の動きは 1 スライド 1 つ。
4. **自動検証 + 目視**。check.py がエラー 0、かつスクリーンショットを自分の目で見てから納品。
5. **画像は必要なところにだけ、許諾を確認して**。飾りの写真より図解・アイコン・余白。
6. **事実は作らない**。数字・引用・固有名詞はユーザー資料か検索で確認したものだけ。仮の数字は「（例）」と明記。

## ワークフロー
このチェックリストをタスクリストに写して進める:
```
- [ ] 0. モード判定
- [ ] 1. ブリーフ（聴衆・ゴール・時間・密度）
- [ ] 2. アウトライン（outline.md → outline.py check → ユーザー確認）
- [ ] 3. テーマ選定（themes.py preview → ユーザー選択）
- [ ] 4. ビジュアル調達（必要なスライドだけ: 写真・イラスト・アイコン → credits.json）
- [ ] 5. 制作（outline.py scaffold → 各スライドをデザイン → build.py）
- [ ] 6. 検証ループ（check.py エラー0 → contact sheet 目視 → motion 確認 → 必要なら reviewer）
- [ ] 7. 納品（HTML ＋ 必要に応じ PDF / 動画、操作説明）
```

### 0. モード判定
- **新規**: 話題だけ／メモ／資料（文書・URL・PPTX）から作る → 1 へ
- **PPTX 変換**: `python3 $SF/scripts/extract_pptx.py in.pptx -o work/` で本文・ノート・画像と outline.md の下書きを得て → 2 へ（内容はそのまま、構成は改善提案してよい）
- **既存デッキの修正**: `deck.src.html` を編集 → 4 の build から。修正後も必ず 5 を通す
- **書き出しだけ**: 6 へ
- **映像作品（短い動画）**: 3D・奥行き・スケールが見せ場の 30〜90 秒の MP4 → 下の「動画」節へ（1・2・4 はスライドと同じ考え方で行い、5〜7 を動画用の手順に置き換える）。スライドをそのまま動画にしたいだけなら 7 の `record.py`

### 1. ブリーフ
足りない情報だけを **1 回にまとめて** 聞く（質問 UI があればそれで）。聞けない／ユーザーが不在なら推測し、推測したことを最初に明示して進める。
- 聴衆（誰に）／ゴール（終わった後に何をしてほしいか）／時間（分）／密度: `speaker`（話して見せる）か `reading`（配布・読ませる）
- 素材があれば全部読む。数字や事実が必要で素材に無ければ検索して出典を控える。

### 2. アウトライン
[references/narrative.md](references/narrative.md) を読んで `outline.md` を書く（形式は同ファイル §7、例は `assets/examples/outline.example.md`）。
Claude Code で `slide-storyteller` エージェントが使えるなら、ブリーフと素材のパスを渡して任せてよい。
```bash
python3 $SF/scripts/outline.py check outline.md     # ゴーストデッキ表示 + ルール検査。エラー 0 まで直す
```
表示された**見出し一覧（ゴーストデッキ）をユーザーに見せて OK をもらう**。作り直しが一番安い段階なので、ここで合意を取る（ユーザー不在なら進めて、後で変更可能と伝える）。

### 3. テーマ選定
[references/design.md](references/design.md) §1–2 を読む。ユーザーが指定済みならスキップ。
```bash
python3 $SF/scripts/themes.py preview --title "<実タイトル>" --subtitle "<実サブ>" \
  --points "<要点1>,<要点2>,<要点3>" --themes swiss,blueprint,signal --out previews/
```
`previews/gallery.png` を見せて選んでもらう（安全枠 1＋用途向け 1＋意外性 1）。「〇〇風に」など参照先があるときは [references/resources.md](references/resources.md) §1（Refero Styles・Minimal Gallery など）で雰囲気を確かめてから選ぶ。色だけ変えたい要望は deck-config の `tokens` で対応。

### 4. ビジュアル調達
[references/visuals.md](references/visuals.md) を読む。**入れるかどうかの判断が先**（抽象概念に雰囲気写真は置かない。写真は全体の 2〜3 割まで。アイコンは 1 セットに揃える）。
Claude Code で `slide-art-director` エージェントが使えるなら、outline.md・テーマ・ブリーフを渡して任せてよい。自分でやる場合（deck フォルダで実行）:
```bash
python3 $SF/scripts/assets.py search "<英語の具体的なクエリ>" --kind photo --orientation landscape   # → sheet.png を Read で見て選ぶ
python3 $SF/scripts/assets.py pick <cand_dir> <#> --as img/hero.jpg --crop 16:9 [--treat duotone --theme <theme>]
python3 $SF/scripts/assets.py icon "shield check" --sheet                                           # アイコンを見比べる
```
- outline.md に `bg:`（背景写真）/ `image:`（split・L-image）/ カード箇条の先頭に `tabler:xxx |` を書けば scaffold が組む。
- ユーザー提供の画像・社内フォルダは `--sources local:<dir>` か `assets.py add <path> --own`。
- **OSS・CC0 は実際に組み込む**: Magic UI・Motion Primitives・Uiverse・Anime.js（MIT）、3dicons（CC0）は GitHub / npm から取得でき（サイト本体は遮断されがち）、許諾文と作者を残せばそのまま使える。ユーザーが「活かして」と言ったら参照だけで済ませない。手順・落とし穴は [references/resources.md](references/resources.md) §5。ライセンス表記のないギャラリー（Refero・Minimal Gallery・Kinetics など）は見るだけ
- 日本のフリー素材（ソコスト・いらすとや）は Claude から自動取得しない。ユーザーがダウンロードして添付したものを、そのまま配置する（ソコストは規約で AI での画像生成への利用を禁止）。resources.md §6
- ライセンスは `credits.json` に自動記録され、build がクレジット（必須のものはキャプション＋末尾のクレジットスライド）を付ける。Google 画像検索や出所不明の画像は使わない。
- ネットワークが無ければ、ユーザー素材・アイコン・図解・CC0 の GitHub 素材で組む。写真が要る場面は PIL/SVG で自作の絵を描いて `--own` で記録してもよい（無理に写真を入れない）。

### 5. 制作
```bash
python3 $SF/scripts/outline.py scaffold outline.md -o deck.src.html   # 叩き台（テーマは outline の theme: か deck-config で）
```
叩き台は最低限。ここからが本番: [references/layouts.md](references/layouts.md) と [references/motion.md](references/motion.md) を読み、スライドごとに
- 内容に最適なレイアウト・コンポーネントを選び直す（数字→stats、対比→compare、手順→flow/timeline、言い切り→statement）
- 主役の動きを 1 つ決め、話す順に `data-step` を置く
- `<aside class="notes">` に話す台詞
- データベースの構造や、出力される Excel ファイルの見た目（新旧比較つき）を見せるなら `data-mock="er"` / `data-mock="sheet"` に JSON を書く（layouts.md §7、実例 `assets/examples/mock/`）。新旧の突き合わせと色分けは `diff` が自動で行う
- Web アプリやスマホの画面イメージ（ブラウザの枠・メニュー・グラフや一覧のパネル）に、立場ごとの要望を引き出し線で重ねるなら `data-mock="app"`（layouts.md §8、実例 `assets/examples/mock/app.src.html`）
- 表現を一段上げたいときは [references/expressive.md](references/expressive.md)（実例 `assets/examples/fx/fx.src.html`）: 結論を書き込んだグラフと並べ替えモーフ（`data-mock="chart"`）、全体→部分に寄るズームキャンバス（`L-zoom`）、手描きの丸・下線（`data-annotate`）、版ごとにトークンが滑るコード（`data-codemove`）、データの粒が流れる構成図／シーケンス図（`arch` / `seq`）、ベントー（`L-bento`）、前後比較スライダー（`.ba-slider`）、日本のタイル地図（`japan`）、キネティック文字（`mask` `words` `type` `scramble` `slam` `tracking`）、3D の地球儀・モデル（`data-3d`）。**1 スライド 1 種類**
完全な実例: `assets/examples/sample.src.html`（全レイアウト・全モーション）。
```bash
python3 $SF/scripts/build.py deck.src.html              # → deck.html（単一ファイル）。静的 lint も表示
python3 $SF/scripts/build.py deck.src.html --watch      # 編集しながら自動再ビルド
```
ソースの約束: 先頭に `<script type="application/json" id="deck-config">{"title","theme","lang","transition","footer","density","tokens"}</script>`、任意で `<style>`、あとは `<section class="slide L-…">` の並び。**生成物 deck.html ではなく deck.src.html を編集する。**

### 6. 検証ループ（省略禁止）
[references/qa.md](references/qa.md) の指摘コード表を見ながら直す。
```bash
python3 $SF/scripts/check.py deck.html --out qa/            # エラーがあれば終了コード 1
python3 $SF/scripts/check.py deck.html --out qa/ --motion 5 # 5枚目の動きをコマ撮り → qa/motion-05-strip.png
```
1. エラー 0 まで: 直す → build → check を繰り返す
2. **`qa/contact-sheet-*.png` を Read で開いて全スライドを目視**（重心、余白、改行位置、強調の数、単調さ）。気になる所を直して再チェック
3. 主役の動きがあるスライド 1〜2 枚の `--motion` ストリップを目視
4. 重要な発表（社外・役員・登壇）: `slide-reviewer` エージェントに deck.html のパスと ブリーフを渡し、**作り手と独立した**採点と修正リストをもらう → must を反映して 1 に戻る

### 7. 納品
- 成果物: `deck.html`（これ 1 つで動く）。当日オフラインの可能性があれば `build.py --fonts embed` で再ビルド（使用文字だけのフォントを埋め込む）
- 必要に応じ: `python3 $SF/scripts/export.py deck.html`（ベクター PDF・文字選択可）、`--png dir`、`python3 $SF/scripts/record.py deck.html`（自動再生動画 webm/mp4）
- previews/ などの作業ファイルは削除。qa/ は残してもよい
- ユーザーへの説明は短く: ファイル、枚数とテーマ、操作キー（→/Space 進む・← 戻る・**S 発表者ビュー**・**O 一覧**・F 全画面・**E で文字を直接編集→Ctrl+S 保存**・? ヘルプ）、次の一手を 1 つ

## 動画（Remotion × three.js）
[references/video.md](references/video.md) を読む。文字・数字・手順・グラフ・遷移の動きを入れるなら [references/motion-graphics.md](references/motion-graphics.md) も読む。**Remotion は個人・3 人以下の会社・非営利は無料、それ以外の企業利用は有料ライセンス**（企業案件なら一言伝える）。Node/npm が必要。
```bash
python3 $SF/scripts/video.py setup                                   # 初回のみ（ランタイム＋Chrome 149）
python3 $SF/scripts/video.py new film --theme signal --motion lively # storyboard.json の雛形（色・フォント・動きの性格）
python3 $SF/scripts/video.py add film img/*.jpg                      # 素材 → public/media（許諾を credits.json に）
python3 $SF/scripts/video.py check film                              # → エラー 0（読む時間・遷移の種類・出典も）
python3 $SF/scripts/video.py stills film                             # film/out/sheet.png を Read で目視 → 直す
python3 $SF/scripts/video.py motion film --scene N                   # 主役の動きがあるシーンを 12 コマで目視
python3 $SF/scripts/video.py det film                                # 決定性チェック
python3 $SF/scripts/video.py render film --out <name>.mp4            # 本番（点滅検査つき）。<name>-sheet.png も目視
```
シーンは `title` / `globe` / `photo` / `kinetic` / `stat` / `steps` / `bars` / `lottie` / `end`。1 シーン 1 主張・1 主役、話す順に出す、遷移は 1〜2 種類。動きは必ず frame から計算（時計・乱数禁止）。

## 判断に迷ったら
- 文字が入らない → 削る・分ける。文字を小さくしない（20px 未満はエラー）
- 箇条書きが続く → 形を変える（stats / compare / flow / statement）
- 動きを足したくなる → 本当に視線の案内になるか。ならないなら足さない
- 独自の見た目が必要 → `L-free` ＋デッキ CSS（トークンのみ使用）→ 必ず check と目視
- 写真の上の文字が読みにくい（`text-on-image`）→ スクリムの向きを文字側へ（`media-bg right/bottom/full`）か `--treat darken` で再 pick
- 合う写真が無い → 写真をやめる（アイコン・図解・statement）
- ブランド色 → `tokens`。新テーマ → design.md §7
- 自作 CSS のクラス名 → 予約名（`.bg` `.bleed` `.frame` `.card` など）を避け、接頭辞を付ける（layouts.md §6）
- わざとはみ出す帯・背景演出 → `.bleed` の中に置く。ループ用の複製は `aria-hidden="true"`
- 属性で足りない動き → Anime.js を最後の section の後ろに同梱し `deck:change` で再生（resources.md §5.4）。動く前の状態も破綻させない
- 作業フォルダ → 絶対パスで作る（`~` はホームで、作業ディレクトリと違うことがある）
- システムの画面・帳票・データ構造を見せたい → スクリーンショットの代わりに mock（`er` / `sheet` / `app`）で描く。文字が小さくなるなら 2 枚に分ける
- 棒グラフ・折れ線を載せる → 手書き HTML より `data-mock="chart"`。**目標線・吹き出し・強調で結論をグラフに書き込む**。並べ替えは同じ id のグラフを 2 枚並べてモーフ
- 全体像と細部を行き来する説明 → スライドを分けるより `L-zoom`。システムの流れ → `arch`（粒が流れる）。やりとりの順番 → `seq`
- 新旧の画面・写真の比較 → `.ba-slider`（同じ大きさの 2 枚）。地域別の数字 → `japan`

## ファイル
| パス | 内容 | 読むタイミング |
|---|---|---|
| references/narrative.md | 構成・見出し・密度・outline 形式 | 2 |
| references/design.md | テーマ・AI slop 回避・日本語組版・独自テーマ | 3（独自テーマ時も） |
| references/visuals.md | 画像を入れる判断・検索・選定・加工・配置・ライセンス | 4 |
| references/layouts.md | レイアウト/部品カタログとスニペット | 5 |
| references/motion.md | アニメーション語彙・原則・レシピ | 5 |
| references/expressive.md | 注釈付きグラフ・モーフ・ズーム・手描き注釈・コードの変化・構成図・ベントー・比較スライダー・日本地図・キネティック文字・3D | 5（表現を強めたいとき） |
| references/qa.md | 指摘コード→直し方、レビュールーブリック、納品チェック | 6 |
| references/resources.md | 外部リソース 29 件の使い分け、OSS（MIT/CC0）を実際に組み込む手順、日本の素材サイトの規約 | 3・4・5 |
| references/video.md | 動画: 手順・絶対ルール・storyboard 仕様・素材・トラブル | 動画 |
| references/motion-graphics.md | 動きの原則・プリセット・文字効果・シーン型・遷移・検証 | 動画で動きを設計するとき |
| assets/examples/sample.src.html | 16 枚の完全な実例 | 5 |
| assets/examples/fx/fx.src.html | v1.7 の表現 10 種の実例（16 枚） | 5 |
| assets/examples/outline.example.md | outline.md の実例 | 2 |
| assets/runtime/ | ランタイム（build が自動で同梱。通常は触らない） | — |
| assets/themes/*.css | 7 テーマ | 独自テーマ作成時 |
| assets/video-template/ | 動画の雛形（Remotion プロジェクト・太陽系とモーションの storyboard 例） | 動画（video.py new が複製） |
| scripts/ | outline / themes / assets / build / check / export / record / extract_pptx / fonts / video / mock（er・sheet・app・chart・arch・seq・japan） | 実行する |
