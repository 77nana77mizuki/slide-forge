# ビジュアル（写真・イラスト・アイコン）調達ガイド

## 目次
1. 画像を入れるかどうかの判断（入れない勇気）
2. 種類の選び方: 写真 / イラスト / アイコン / 図解 / なし
3. 検索のコツ（クエリの作り方）
4. 候補の選び方（コンタクトシートを見るときの基準）
5. 加工（トリミング・テーマ色処理）
6. 配置パターン（HTML スニペット）
7. ライセンスとクレジット（ルール）
8. assets.py コマンド早見表

---

## 1. 入れるかどうか
画像は「**言葉だけでは伝わらない具体性**」を足すときだけ入れる。飾りのための画像は情報を薄める。
| 入れる | 入れない |
|---|---|
| 実物・現場・製品・画面を見せると早い（「このライン」「新しい画面」） | 抽象概念（「信頼」「成長」「協力」）の雰囲気写真 → アイコンか図解、または何も置かない |
| 表紙・章扉・締めで場の空気を作る（1 デッキ 2〜4 枚が目安） | 数字・比較 → グラフ（L-stats / L-chart） |
| 人・場所・出来事の「実在感」が説得力になる | 手順・構造 → flow / timeline / SVG 図解 |
| 並列の概念をアイコンで見分けやすくする（cards / icon-row） | 余白を埋めたいだけ |
目安: speaker デッキで写真を使うスライドは全体の 2〜3 割まで。アイコンは 1 スライド内でセット（同じアイコンセット・同じ太さ）で揃える。

## 2. 種類の選び方
| 伝えたいこと | 種類 | 取り方 |
|---|---|---|
| 実在の物・場所・人の雰囲気 | 写真 | `assets.py search "..." --kind photo` |
| 概念を親しみやすく（子ども・地域・研修） | イラスト | `--kind illustration`（Pixabay は日本語検索可） |
| 並列項目の見分け、機能一覧 | アイコン | `<i class="ico" data-icon="tabler:robot">` |
| 仕組み・流れ・構造 | 図解 | flow / timeline / インライン SVG（画像検索しない） |
| 自社の製品・社員・拠点 | 自社素材 | `--sources local:<社内フォルダ>` かユーザー提供 → `assets.py add` |
| 宇宙・探査・地球観測 | NASA 公式画像 | `--sources nasa`（キー不要。出典に NASA を明記、NASA ロゴは使わない、推奨・提携を匂わせない） |
| 実在の特定の人物・ロゴ・製品写真 | 使わない（ユーザー提供か公式プレス素材で許諾を確認できた場合のみ `fetch`） | — |

アイコンセットの選び分け: `tabler`（線・万能。既定）/ `lucide`（線・細め）/ `ph`（Phosphor、太さ違いあり）/ `material-symbols`（Google 系 UI）/ `fluent-emoji-flat`（カラフル。pop テーマ向け）。
名前は英語。探す: `assets.py icon "shield check" --sheet` → 画像を見て選ぶ。一覧サイト: https://icon-sets.iconify.design/

## 3. 検索のコツ
- **英語の具体的な名詞**で（Openverse / Wikimedia / Unsplash / Pexels は英語が強い）。日本語でよいのは Pixabay と local のタグ。
  - ✗「DX 推進」「効率化」 → ◯ "factory robot arm", "engineers reviewing blueprint"
- 構図の言葉を足す: `wide`, `close-up`, `aerial`, `minimal`, `copy space`, `from above`
- 雰囲気・色の言葉: `night`, `warm light`, `blue tone`（テーマに合わせる）
- 1 回でダメなら言い換えて 2〜3 回。それでも無ければ**写真をやめて**アイコン・図解・statement に切り替える（無理に入れない）。

## 4. 候補の選び方（sheet.png を必ず見る）
- 主張と一致しているか（写っているものを 1 行で説明し、見出しと矛盾しないか）
- **文字を置く余白**があるか（背景に使うなら左か下が空いているもの）
- 画像内に文字・透かし・ロゴ・ブランド名が入っていない
- 識別できる人物の顔が大きく写るものは避ける（肖像・誤解の懸念）。人物写真は後ろ姿・手元・遠景が無難
- 解像度: 全面背景は幅 1920px 以上、半分の枠なら 1000px 以上（check.py が `low-res` で警告）
- 色調がテーマと喧嘩しない（無理なら `--treat duotone` / `tint` で揃える）
- 1 デッキ内でトーン（明るさ・彩度・写真/イラストの別）を揃える
- `⚠attrib` 表示はクレジット必須（CC BY 等）。使ってよいが、クレジットが画像に載る

## 5. 加工
```bash
assets.py pick <cand_dir> <#> --as img/hero.jpg --crop 16:9                 # 全面背景
assets.py pick <cand_dir> <#> --as img/side.jpg --crop 4:5 --focus 0.5,0.35 # 縦長の枠。顔・空を残すなら focus を上に
assets.py pick <cand_dir> <#> --as img/bg.jpg --crop 16:9 --treat duotone --theme signal  # テーマ色の 2 階調
```
| --treat | 使いどころ |
|---|---|
| `none` | 製品・現場を正確に見せたいとき（既定） |
| `duotone` | 複数写真のトーン統一、表紙・章扉の雰囲気づくり |
| `darken` | 白文字を重ねる背景（`--strength 0.5`） |
| `tint` | 控えめにテーマ色へ寄せる |
| `mono` | 過去・記録の文脈 |
| `blur` | 背景としてだけ使う（内容は読ませない） |
ND（改変禁止）ライセンスは加工できない（スクリプトが止める）。

## 6. 配置パターン
**背景写真＋文字**（どのレイアウトでも可。文字の側にスクリム＝半透明の帯が自動で入る）
```html
<section class="slide L-title" data-chrome="off">
  <div class="media-bg"><img src="img/hero.jpg" alt="…"></div>        <!-- 左に文字。右に文字なら class="media-bg right"、下なら "bottom"、全面なら "full" -->
  <div class="kicker">…</div><h1 class="hero">…</h1>
</section>
```
**半分に写真**
```html
<div class="col"><div class="frame" style="height:640px"><img class="photo" src="img/side.jpg" alt="…"></div></div>
```
**黒背景の写真（宇宙・夜景・舞台）をダークテーマに溶け込ませる**: スライド直下の外側ラッパーに `class="screen"`（例 `<div class="screen" style="position:absolute;…"><img …></div>`）。スクリーン合成で黒が消え背景に溶ける。アニメーション付き要素の内側に付けても効かない。円形に切り抜くと写真の黒い縁が残るので不要

**全面写真で一言**: L-image（layouts.md）。**写真カード**:
```html
<div class="card photo-card"><img src="img/a.jpg" alt="…"><div class="body"><h3>…</h3><p>…</p></div></div>
```
**アイコン**（色はテーマのアクセント、大きさは font-size）
```html
<div class="icon-row" style="--cols:3" data-stagger="up">
  <div><i class="ico" data-icon="tabler:robot"></i><h3>搬送を自動化</h3><p>…</p></div>
</div>
<div class="card"><i class="ico" data-icon="tabler:shield-check"></i><h3>…</h3></div>
<p>本文中にも <i class="ico accent" data-icon="tabler:check"></i> 使える</p>
```
outline.md では `bg: img/x.jpg`（背景）、`image: img/x.jpg`（split / L-image）、カードの箇条を `tabler:robot | 見出し | 説明` と書けば scaffold が組む。

## 7. ライセンスとクレジット（ルール）
- 使ってよいのは: CC0 / パブリックドメイン / CC BY / CC BY-SA / Unsplash・Pexels・Pixabay ライセンス / NASA 画像（出典表記・ロゴ不使用） / オープンソースのアイコン / ユーザー自身の素材。
- 企業・作品の公式画像（ゲーム・アニメ・キャラクター・ロゴ等）は、その権利者が利用を明示的に認めた範囲（例: 公式の利用ガイドライン）でユーザーが自分で用意したものだけ。Claude がネットから集めない。
- **NC（非営利）は既定で除外**（業務利用は商用扱いのことが多い）。個人・非営利の場合のみ `--allow-nc`。
- **Google 画像検索や任意のサイトから拾った画像は使わない**。Web で見つけた画像は、出典ページでライセンスを確認できた場合だけ `assets.py fetch … --license … --creator … --source-url …`。
- すべての画像は `credits.json` に記録される。build が:
  - クレジット必須（CC BY 等）の画像に**キャプションを自動表示**（右上）
  - 第三者素材があれば**クレジットスライドを末尾に自動追加**（改変内容も明記＝CC BY の要件）
  - 記録のない画像・非営利ライセンスの画像を**警告**
  - deck-config `"credits"`: `auto`（既定）/ `slide`（末尾のみ）/ `inline`（キャプションのみ）/ `off`
- BY-SA を加工した画像を配布する場合は同じライセンスで出す必要がある（発表だけなら問題になりにくい）。
- いらすとや等の日本の素材サイトは API がなく規約も個別（例: 商用は点数制限あり）。ユーザーが自分でダウンロードしたものを `assets.py add img/x.png --license "..." --source-url …` で記録する。
- ライセンス表記は各サービスの現行規約が正。迷ったらユーザーに確認し、無理に使わない。

## 8. assets.py 早見表
```bash
assets.py search "<英語クエリ>" [--kind photo|illustration|vector] [--orientation landscape|portrait|square]
                               [--sources openverse,wikimedia,pixabay,unsplash,pexels,local:DIR] [--allow-nc]
assets.py pick <cand_dir> <#> --as img/x.jpg [--crop 16:9] [--focus x,y] [--treat duotone --theme <name>]
assets.py icon <word> [<word>…] [--sets tabler,lucide] [--sheet] [--save]
assets.py add <path> --own | --license "CC BY 4.0" --creator … --source-url …
assets.py fetch <url> --as img/x.jpg --license … --creator … --source-url …
assets.py credits deck.src.html          # 使用画像とライセンスの一覧・記録漏れ
```
キーなしで使えるのは Openverse・Wikimedia Commons・アイコン。写真の質を上げたいときは無料の API キーを環境変数に設定:
`PIXABAY_API_KEY` / `UNSPLASH_ACCESS_KEY` / `PEXELS_API_KEY`。ネットワークが無い／遮断されている場合（Openverse・Wikimedia・NASA がすべて 403 など）は、ユーザー提供の画像・local ソース・アイコン（npm 経由）・図解で進める。さらに:
- **CC0 素材は GitHub から**: 3dicons などは `git clone` で取れることが多い（resources.md §5）
- **写真の代わりに自作の絵**: 夜空・山並み・抽象的な背景などは Python（PIL）や SVG でその場で描き、`assets.py add img/x.jpg --own` で記録する。スライド上では「オリジナル」と正直に書く（実写のふりをしない）
