# モーショングラフィック（動画の動きの設計）

video.md の手順で作る動画に、**文字・図形・数字・遷移の動き**を足すときに読む。
道具は揃っているが、足すほど良くなるわけではない。動きは「見る順番」を作る道具で、飾りではない。

## 1. 原則（迷ったらここに戻る）
1. **1 シーン 1 主役**。主役の動き（見出しの登場・数字・線が伸びる）を 1 つ決め、他は控えめに従わせる
2. **話す順に出す**: 小見出し → 主張 → 主役（数字・図）→ 補足。同時に出さない
3. **入りは減速、出は加速**（ease-out で着地、ease-in で去る）。等速（linear）は機械的に見えるので使わない
4. **落ち着いてから 0.5 秒以上止める**。動き終わる前に次へ行かない（check が秒数を警告）
5. **遷移は 1〜2 種類に絞り、使い分けの理由を持つ**（例: 通常は wipe、章の切り替えだけ lightLeak）
6. **速さで性格が決まる**: 落ち着き＝長め・ばねなし／勢い＝短め・オーバーシュートあり。1 本の中で混ぜない → `motion` プリセット
7. **点滅は 1 秒に 3 回まで**（WCAG 2.3.1）。render が自動検査する
8. **文字は大きく**: 1080p で見出し 64px 以上、キネティックは 100px 以上が目安。細い書体・装飾書体を動かさない

## 2. プリセット（storyboard の `"motion"`）
| 名前 | 性格 | 入り | ばね | 標準の見出し効果 | 標準の遷移 | 向く用途 |
|---|---|---|---|---|---|---|
| `calm`（既定） | 落ち着き・信頼 | 20f / Carbon expressive entrance | なし | rise | fade 0.6s | 報告・科学・展示ループ |
| `lively` | 軽快・前向き | 16f / snap | 少し跳ねる | mask | wipe 0.5s | 製品紹介・社内告知 |
| `punchy` | 勢い・SNS | 11f / snap | よく跳ねる | slam | pushCut 0.4s | 冒頭の掴み・短尺 SNS |
緩急の値は IBM Carbon の expressive カーブ（入り `cubic-bezier(0,0,.3,1)`／出 `(.4,.14,1,1)`／標準 `(.4,.14,.3,1)`）と Remotion の `Easing.spring` を使う。拡大縮小は見た目が等速になる `perceptual-scale` で補正済み。

## 3. 文字の動き（`effect`）
見出し（title / text）に効く。文字の単位は BudouX の**文節**（日本語の自然な改行位置と同じ）で、語の途中で割れない。
| effect | 見え方 | 使いどころ |
|---|---|---|
| `rise` | 文節ごとに下からフェードイン | 迷ったらこれ。長めの主張 |
| `mask` | 文節が見えない枠の下からせり上がる | 見出し・章タイトル |
| `pop` | 文節が小さい所から弾んで出る | 短い言い切り（2 行以内） |
| `slam` | 大きい所から叩きつけるように着地 | 1〜2 語の強い言葉。多用しない |
| `blur` | ぼかしから焦点が合う | 静かな導入・余韻 |
| `type` | 1 文字ずつタイプ＋カーソル | コマンド・引用・ログ |
| `tracking` | 字間が広い所から締まる | 英字のロゴ・タイトル |
| `scramble` | 暗号が解けるように正しい文字へ | 「正確さ」「解読」の文脈 |
| `shimmer` | 着地後に光が一度走る | 締めの一言 |
強調の書き方（どの効果とも併用可）: `**アクセント色**`、`==マーカー==`、`__下線__`、`((丸囲み))`、`\n` で改行。マーカー類は文字が出てから手描き風に引かれる（@remotion/rough-notation）。**強調は 1 シーン 1 箇所**。

## 4. シーンの型
| type | 主役 | 主なキー |
|---|---|---|
| `kinetic` | 文字そのもの（1〜3 行・1 行 16 字以内） | `text` `effect` `by`(char/phrase/line) `align` `sub` `exit`(true で退場アニメ) `backdrop` |
| `stat` | 数字 1 つ（＋同じ意味の図） | `big` `unit` `title` `caption` `viz`(ring/bar/none) `value`(0–100) |
| `steps` | 線が伸び、届いた順に手順が出る（2–5 個） | `title` `items[{title,text}]` |
| `bars` | 横棒グラフ（2–7 本、1 本を強調） | `title` `items[{label,value}]` `unit` `highlight` `credit`（出典必須） |
| `lottie` | ライセンスの明確な Lottie アニメ | `lottie`(public 内の .json) `title` `side` `loop` `speed` |
| `title` / `end` / `globe` / `photo` | 既存（video.md）。見出しに `effect` が効く | |
背景 `backdrop`: `mesh`（色面がゆっくり漂う）・`grid`（方眼がゆっくり流れる）・`dots`（ドットの中を光が移動）・`rays`（上からの光芒）・`stars`・`plain`・画像パス。どれも文字より目立たない強さにしてある。

## 5. 遷移（`transition` / `overlay`）
storyboard 全体の既定と、シーンごとの上書き（そのシーンに**入る**遷移）。
```jsonc
"transition": { "type": "wipe", "seconds": 0.5, "direction": "from-left", "timing": "ease" }   // 全体
{ "type": "stat", "transition": { "type": "blurSlide", "seconds": 0.6 } }                     // このシーンへ
{ "type": "kinetic", "overlay": { "type": "lightLeak", "seconds": 1, "seed": 3 } }            // カット＋光漏れ
```
- どこでも動く: `none` `fade` `slide` `wipe` `flip` `clockWipe` `iris` `pushCut`
- Chrome 149 以上が必要（シェーダー。`video.py setup` が用意する）: `blurSlide` `crossZoom` `zoomInOut` `swap` `dissolve` `filmBurn` `zoomBlur` `linearBlur` `dreamyZoom` `ripple` `crosswarp` `bookFlip`
- 方向は物語に合わせる（進む＝右から左へ流す、戻る＝逆）。`timing`: `ease`（既定）/`linear`/`spring`
- `lightLeak` は画面全体が一瞬明るくなる。章の切り替えに 1〜2 回まで
- `motionBlur: true`（実験的）: 速い動きに残像を付ける。描画が 6 倍重く、半透明の光やマーカーが濃く出る不具合があるので、使ったら stills で必ず確認

## 6. 動きの参考カタログと素材（2026 年のバイブコーディング資源から、動画に効くものだけ）
Web 向けの動きのカタログは「どんな動きがあり得るか」の語彙として有用。ただしコードは CSS アニメ・Framer Motion・スクロール連動が前提で、**そのままでは動画に使えない**（コマ単位で決まらず、書き出すたびに変わる）。見た目と「緩急・順番・間」だけを参考にし、ここの部品（frame から計算）で作り直す。コードを写さないので、ライセンスが未表記のカタログも「見て学ぶ」用途には使える。

**動きの語彙（見て参考にする）**
| カタログ | ライセンス（確認済み） | 動画で効く動き → ここでの対応 |
|---|---|---|
| Magic UI (magicui.design) | MIT | Text Animate・Number Ticker・Word Rotate・Animated Shiny Text・Hyper Text → `rise`/`blur`・`big` のカウントアップ・`shimmer`・`scramble`。Dot Pattern・Animated Grid・Light Rays・Meteors → `backdrop: dots/grid/rays` |
| Motion Primitives (motion-primitives.com) | MIT | Text Effect（per char/word）・Text Shimmer・Animated Number・Border Trail → `by: char/phrase`・`shimmer`・`stat` |
| CSS Text Effects (text-effects.colorion.co) | MIT | Split-Flap・Cipher・Hi-Liter・Kinetic-Type → `scramble`・`==マーカー==`・`kinetic` |
| Kinetics (kinetics.colorion.co) | 表記なし（GitHub にも LICENSE 無し）→ **コードは使わず見るだけ** | ばね調整の感覚（stiffness/damping）・Odometer・Underline Draw・Progress Ring → `motion` プリセット・`__下線__`・`stat viz: ring` |
| Anime.js (animejs.com, v4) | MIT | Timeline・Stagger（位置・値・順序）・SVG の線描画とモーフ → `steps` の線・文節ごとの時間差（ここでは Remotion 側で同じ考え方を実装） |
| Aceternity UI (ui.aceternity.com) | サイトの規約に従う | 背景の光・スポットライト・グリッド → `backdrop` の発想元 |
| MicroKit・Circle Loaders・Gradient Buttons・Liquid Glass | 各サイトの表記に従う | UI の微細な動き。動画では小さすぎて伝わらないことが多い。使うなら 1 か所だけ |

**見た目の研究用（構図・色・書体を見る。画像やコードは流用しない）**: Refero Styles（製品のスタイルと書体）、Minimal Gallery、Component Gallery、Kage、AppShot Gallery。「このブランドっぽい動画」を頼まれたら、ここで近い雰囲気を探し、テーマと `motion` プリセットを選ぶ判断材料にする。DESIGNmd のような「エージェントが読める design.md」は、Slide Forge ではテーマ CSS と storyboard の `style` が同じ役割。

**そのまま素材として使えるもの**
- **3dicons（CC0・クレジット不要）**: 3D アイコン。`photo` の被写体や `backdrop` に。`video.py add film icon.png --license CC0 --creator 3dicons --source https://3dicons.co`
- **Kitbitz（CC0・2,000 点以上の手描きイラスト）**: `photo` / `lottie` 横の挿絵に。同様に `--license CC0 --source https://kitbitz.art`
- それ以外（Uiverse・21st.dev などのコンポーネント集）はコードの集まりで、動画の素材にはならない。スライド（HTML）側で部品の見た目を参考にする程度

**使わないもの**: スクロール連動・3D サイトの「フルビルドプロンプト」（scrolltide 等）は Web サイト制作向けで、時間軸で見せる動画とは設計が違う。

新しい効果を足すときは `src/Kinetic.tsx`（文字）・`src/Backdrop.tsx`（背景）・`src/MotionScenes.tsx`（シーン）に追加し、`det`（決定性）と `motion`（コマ撮り）を通す。

## 7. 検証
```bash
python3 $SF/scripts/video.py check film              # 読む時間（組み上がり＋読了＋0.5 秒）、遷移の種類数、シェーダー可否
python3 $SF/scripts/video.py stills film             # 各シーンが落ち着いた瞬間
python3 $SF/scripts/video.py motion film --scene 3   # そのシーンの 12 コマ（入り→保持→出）を 1 枚に
python3 $SF/scripts/video.py det film                # 同じコマが完全一致
python3 $SF/scripts/video.py render film --out x.mp4 # 書き出し＋点滅検査（1 秒 3 回まで）
```
`motion` のコマ撮りで見る所: 出る順番が話す順か／主役が 1 つか／跳ねすぎていないか／落ち着いてから十分止まっているか／遷移が文字を読み終える前に始まっていないか。

## 出典
- Remotion 公式 Agent Skills（remotion-dev/skills, 2026-09-25 更新: timing・transitions・text-highlights・light-leaks・motion-blur・effects）
- IBM Carbon Design System — Motion（duration・easing の値）
- WCAG 2.3.1 Three Flashes or Below Threshold
- Magic UI・Motion Primitives・Anime.js（MIT、GitHub の LICENSE で確認）、3dicons・Kitbitz（CC0、各サイトで確認）
- Kinetic typography の実務ガイド（落ち着いてから 0.5 秒以上表示、等速を避ける、細い書体を動かさない、reduced-motion 配慮）
