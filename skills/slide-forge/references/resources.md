# 外部リソース集（デザイン参照・動きの語彙・素材）

2026 年に「バイブコーディング」向けとして評価の高い 29 の資源を、Slide Forge での使い道ごとに整理したもの。
**スライド（deck.html）が主、動画は従**。ライセンスが明確な OSS・CC0 は実際に組み込み（§5）、それ以外は判断の材料として使う。

## 0. 使い方の大原則
1. **まずライセンスで 2 つに分ける**。MIT / CC0 など条件が明記されたものは**実際に組み込む**（ユーザーが「活かして」と言うのはこれ。参照だけに留めると期待外れになる）。ライセンス表記がないもの・他社の作品集（ギャラリーのスクリーンショット、他社サイトの画像・ロゴ）は**見るだけ**
2. **使うときの条件を守る**。MIT は著作権表示と許諾文を成果物に含める（§5.5）。CC0 は条件なしだが出典は credits.json に記録する
3. **見るだけのものは、考え方を移す**。構図・余白・書体・色だけ持ち帰り、既存の部品かデッキ CSS（トークンのみ）で作り直す
4. **取得経路**: サイト本体・画像 CDN はシェルから遮断されやすいが、**GitHub（git clone）と npm は通ることが多い**。OSS の作品集はまずリポジトリから取る（§5）。どちらも無理ならユーザーに保存・添付を頼む
5. **日本の素材サイトは自動取得しない**（§6）。規約で AI への取り込みを禁じていることがある

## 1. 参照: 構図・スタイルを決めるとき（手順 3 テーマ選定 / 5 制作）
| 資源 | 何が見られるか | スライドでの使い道 |
|---|---|---|
| Refero Styles (styles.refero.design) | 実製品 2,000 以上のスタイルと書体の組み合わせ | 「〇〇社っぽく」「SaaS 風に」と言われたとき、近いスタイルを見つけて**テーマ選び・`tokens`（色）・見出しの字面**の判断に使う |
| Minimal Gallery (minimal.gallery) | 厳選された余白の多いサイト | 余白・重心・1 画面 1 メッセージの感覚合わせ。`swiss` / `washi` の調整時 |
| Kage (kage.design) | 実 UI の参考をプロンプトの言葉に対応づけ | 「こういう雰囲気」をデザイン指示の言葉にするとき（design.md のテーマ説明を書く・独自テーマを作る） |
| Component Gallery (component.gallery) | 同じ UI 部品を各社のデザインシステムがどう解いたか 2,600 例 | カード・タブ・タイムライン・表など、**部品の見せ方の比較**。layouts.md の部品を選び直すとき |
| DESIGNmd (designmd.ai) | エージェントが読める Markdown 形式のデザインシステム | Slide Forge ではテーマ CSS 冒頭の `@theme/@mood/@font` と design.md §7 が同じ役割。ユーザーの design.md を受け取ったら、それを**独自テーマ（トークン）に写す**入力にする |
| AppShot Gallery (appshot.gallery) | モバイルアプリの実画面 | アプリ紹介スライドの**画面モック**の構図（端末フレーム・吹き出しの付け方）の参考。実アプリ画面は自社のものだけ載せる |
| Navbar Gallery / Footer Design / CTA Gallery / 404s | ナビ・フッター・CTA・エラーページの実例 | スライドでは主に **CTA（最後の一枚）** の参考: 行動を 1 つに絞る、ボタン状の強調、短い動詞。ナビ・フッターはデッキのフッター表記の簡潔さの参考程度 |
| scrolltide.co | 3D・スクロール連動サイトの完全なデザインブリーフ 200 以上 | スクロールはスライドに無いが、**ブリーフの書き方**（目的・雰囲気・構図・動き・色を一続きで指定）は、ブリーフ（手順 1）とテーマ説明の書き方の参考になる |
| VibePrompt (vibeprompts.dev) | ダッシュボード・LP 向けの既製プロンプト | 数字だらけのスライド（KPI・ダッシュボード風）を作るとき、情報の優先順位の付け方の参考。プロンプトはそのまま使わず、outline.md の主張に合わせて削る |

## 2. 動きの語彙: どんな動きがあり得るか（手順 5 の motion.md と併読）
MIT のもの（Magic UI・Motion Primitives・Anime.js）は既存の属性で代用できる場合でも、**見せたい効果そのものが部品にあるなら移植して使ってよい**（手順は §5）。
| 資源 | ライセンス | スライドでの対応（既存の部品で作る） |
|---|---|---|
| Magic UI (magicui.design) | MIT | Number Ticker → `data-count`／Text Animate・Blur Fade → `data-anim="up"` `blur` `chars` と `data-stagger`／Highlighter → `data-anim="mark"`／Animated Beam・線 → `data-anim="draw"`（SVG の線描画）／Dot Pattern・Grid → テーマの背景 |
| Motion Primitives (motion-primitives.com) | MIT | Text Effect（文字・単語ごと）→ `data-anim="chars"` / `data-stagger`／Animated Number → `data-count`／Transition Panel → `data-morph`（マジックムーブ） |
| Aceternity UI (ui.aceternity.com) | サイトの規約に従う | スポットライト・グラデーションの光 → 表紙の背景演出の発想元（デッキ CSS で控えめに） |
| Kinetics (kinetics.colorion.co) | 表記なし → **見るだけ** | ばねの効いた小さな反応。スライドでは「クリックで出す `data-step` の着地感」の調整の参考 |
| CSS Text Effects (text-effects.colorion.co) | MIT | 見出しの字の効果（マーカーは `data-anim="mark"`、分割表示は `chars`）。**1 デッキ 1 か所**、表紙か締めだけ |
| Anime.js (animejs.com) | MIT | タイムライン・時間差（stagger）・SVG の線とモーフの考え方 → `data-step` の順番設計と線描画 |
| MicroKit UI (microkit.co)・Circle Loaders・Gradient Buttons | 各サイトの表記に従う | UI の微細な動き。発表スライドでは小さすぎて伝わらない。**使わないのが基本** |
| Liquid Glass (glass.samasante.com) | 各サイトの表記に従う | ガラス風の屈折。文字のコントラストが落ちやすい（check.py の contrast / text-on-image に注意）。使うなら写真の上のカード 1 枚だけ |

**コンポーネント集**（shadcn/ui・21st.dev・Uiverse・UIAble・mapcn）:
- Uiverse: **全作品 MIT で HTML+CSS 単体**。ローダー・ボタンはそのまま載せられる（§5.2）
- shadcn/ui: 余白・角丸・境界線の「上品な標準」の参考（`swiss` テーマの調整）
- 21st.dev: MCP 経由の部品レジストリ。Slide Forge では使わない（HTML を自前で持つため）
- mapcn: 地図の見せ方（マーカー・ルート・吹き出し）の参考。スライドに地図を載せるときは、地図タイルの許諾（OpenStreetMap なら © OpenStreetMap contributors）を credits に記録する

## 3. 素材: そのまま載せてよいもの（手順 4 ビジュアル調達）
| 資源 | ライセンス（サイトで確認済み） | 使い方 |
|---|---|---|
| 3dicons (3dicons.co) | **CC0**（商用可・クレジット不要） | 立体アイコン。表紙や章扉のアクセント、`split` の図版に。手元に保存して `assets.py add img/rocket.png --license CC0 --creator 3dicons --source https://3dicons.co` |
| Kitbitz (kitbitz.art) | **CC0**（2,000 点以上の手描きイラスト） | 人物・物の手描きイラスト。やわらかい題材（研修・社内向け・子ども向け）に。同様に `--license CC0 --source https://kitbitz.art` |
- 1 デッキでアイコンやイラストの**画風を 1 つに揃える**（3dicons と Tabler 線アイコンを混ぜない）
- 3dicons は GitHub（realvjy/3dicons, CC0）の `static/` に約 60 点の PNG がある（§5.3）。CDN（digitaloceanspaces / r2.dev）とサイトは遮断されやすい
- Kitbitz はサイトからのダウンロードが必要。ユーザーに保存して添付してもらうか、ブラウザツールで取得する

## 4. 動画で使うとき
動画（Remotion）側の対応表は [motion-graphics.md](motion-graphics.md) §6。考え方は同じ（見た目だけ参考、コマ単位で作り直す、CC0 素材は `video.py add --license CC0`）。

## 5. OSS を実際に組み込む手順（2026-09 のセッションで検証済み）
```bash
mkdir -p ~/oss && cd ~/oss
git clone --depth 1 --filter=blob:limit=2m https://github.com/magicuidesign/magicui.git     # MIT
git clone --depth 1 --filter=blob:limit=2m https://github.com/uiverse-io/galaxy.git         # MIT（全作品）
git clone --depth 1 --filter=blob:limit=2m https://github.com/ibelick/motion-primitives.git # MIT
git clone --depth 1 --filter=blob:limit=2m https://github.com/realvjy/3dicons.git           # CC0
npm pack animejs && tar xzf animejs-*.tgz        # MIT → package/dist/bundles/anime.umd.min.js（約 120KB, グローバル window.anime）
```
取り込む前に各リポジトリの LICENSE を `head` で確認する。

### 5.1 Magic UI / Motion Primitives（React → 素の HTML/CSS に移植）
- 部品: `magicui/apps/www/registry/magicui/*.tsx`。**keyframes は別ファイル** `magicui/apps/www/styles/globals.css`（`@keyframes orbit / marquee / ripple / aurora / meteor / shine` など）
- 移植しやすい（CSS だけで済む）: Orbiting Circles・Marquee・Border Beam（`offset-path: rect()`）・Meteors・Ripple・Aurora Text・Shine Border・Animated Shiny Text。Motion Primitives は `components/core/`（Text Shimmer など）
- 移植しにくい（WebGL・React 状態が本体）: Retro Grid・Globe・Particles など → 使わない
- 移植のコツ: Tailwind のユーティリティを CSS に書き下し、色はできるだけテーマトークンに置き換える。乱数で配置する部品（Meteors）は**生成スクリプトで固定値に**する（検証のたびに変わらないように）。クラス名は `mu-` などの接頭辞で衝突を避ける
- 無限ループの背景演出は 1 デッキ数枚まで（Meteors は言い切りの 1 枚だけ、など）

### 5.2 Uiverse（HTML+CSS をそのまま）
- `galaxy/<カテゴリ>/<作者>_<名前>.html`（loaders 718・Buttons 1,231・Patterns 103 ほか）。CSS 冒頭に `/* From Uiverse.io by <作者> */` があるので**消さない**
- 選び方: 外部画像・`@import`・`url(` を含まない 4.5KB 未満に絞り、数十個を一覧描画して目で選ぶ（小さすぎる・意味不明なものが多い）。Patterns は大きさを持つ親が必要で、単体描画だと真っ白になる
- 載せ方: **iframe の srcdoc に隔離**する（クラス名 `.loader` `.btn` などがデッキと衝突しない）。`body{display:grid;place-items:center;zoom:1.6}` で拡大、背景は transparent。カードに「by 作者名」を 24px 以上で添える
- ホバーで動くボタンは発表中にマウスを乗せれば原作どおり動く

### 5.3 3dicons（CC0 の立体アイコン）
- `3dicons/static/*.png`。**他社ロゴ（Figma・Blender・Photoshop・XD・Sketch・C4D）と宣伝バナーが混ざっている**ので除外する。使えるのは吹き出し・本・ハート・虫眼鏡・いいね・歯車など
- 解像度が小さい（116〜293px）。**表示は原寸の 1.2 倍まで**（超えると check が low-res）。大きく見せたいときは 293px の吹き出しなどを選ぶ
- 記録: `assets.py add img/3d-x.png --license CC0 --creator "3dicons (Vijay Verma)" --source https://github.com/realvjy/3dicons`
- 画風を揃える（グラデーション系・金属系を混ぜない。線アイコンとも混ぜない）

### 5.4 Anime.js をデッキで動かす
- `<script>` は**最後の `<section>` の後ろ**に置く（build が本体に残す。先頭に書いたものは v1.4 から自動で末尾に移される）
- スライド表示のたびに `document` へ `deck:change`（`detail: {index, step}`）が飛ぶ。`step === 0` のときに再生する
- 最初の表示には `deck:change` が来ないことがあるので、`load` 後に現在のスライドで 1 回呼ぶ
- `prefers-reduced-motion` なら再生しない。**動く前の状態でも破綻しない初期値**を置く（例: ルート上を進む点は終点に置いておく。原点 0,0 のままだと静止画で左上に点が残る）
- 使いどころ: `stagger(…, {grid, from:'center'})` の波、`svg.createDrawable` の線描画、`createMotionPath` で線の上を進む点

### 5.5 ライセンス表記（MIT の条件）
- 本体に「使った部品と作者」の表スライドを 1 枚（作品集・ライセンス・著作者）
- **許諾文の全文**を最後の section の後ろに `<script type="text/plain" id="oss-licenses">…</script>` で同梱する（見えないが配布物に含まれる）
- CC0 の画像だけなら build の自動クレジットスライドは不要（deck-config `"credits": "off"`）。CC BY がある場合は `auto` のまま

## 6. 日本のフリー素材サイト（自動取得しない）
| サイト | 規約の要点（2026-09 確認） | 扱い |
|---|---|---|
| ソコスト (soco-st.com) | 商用可・クレジット不要・点数制限なし・色やサイズの加工可（顔パーツの改変は不可）。直リンク禁止。**AI 学習・画像生成の参照、生成 AI へのアップロードで別の画像を作ることは禁止** | ユーザーが自分でダウンロードして添付した場合のみ、**そのまま配置**（サイズ・色・動き）。それを元に絵を描く・生成するのは不可。Claude から自動取得しない（サイトもシェルから遮断される）。気になる場合は運営に確認を勧める |
| いらすとや | 商用は点数制限あり等、規約が個別 | ユーザーが用意したものを `assets.py add … --license "…" --source-url …` |
- 記録例: `assets.py add img/x.svg --license "ソコスト利用規約" --source-url https://soco-st.com/guide`（クレジット表示は不要なので `"credits": "off"` でよい）
