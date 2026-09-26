# 動画（Remotion × three.js）

スライドとは別に、**30〜90 秒の短い映像**（告知・ティザー・SNS・展示ループ・スライドの冒頭に流す映像）を作るとき用。
React でシーンを書き、three.js で 3D を描き、Remotion がフレーム単位で MP4 に書き出す。編集するのは基本的に `storyboard.json` だけ。

> **使う前に確認（ライセンス）**: Remotion は無料で使えるのは「個人／従業員 3 人以下の営利組織／非営利組織／評価目的」。それ以外の企業の業務利用は Company License が必要（remotion.pro）。企業の案件と分かったら、ユーザーに一言伝える。three.js・React は MIT。

## 0. いつ動画にするか
- 向く: 見せ場が「動き・奥行き・スケール」にあるもの（宇宙・地形・製品の 3D・数字の推移）、発表前の掴み、無音で流す展示やSNS
- 向かない: 読ませたい説明・細かい表・インタラクション → スライド（deck.html）の方がよい。**スライドの `record.py` 動画は「スライドをそのまま録画」、こちらは「映像作品」**と使い分ける
- 長さの目安: 1 シーン 3.5〜5 秒 × 6〜10 シーン。1 シーン 1 主張（スライドと同じ）

## 1. 手順
```bash
python3 $SF/scripts/video.py setup                                  # 初回のみ（npm で ~1 分。共有ランタイム＋Chrome 149 を ~/.cache に）
python3 $SF/scripts/video.py new film --theme signal --motion lively # 雛形 + テーマの色・フォント + 動きの性格（例: 太陽系ツアー）
python3 $SF/scripts/video.py add film img/*.jpg                     # 素材を public/media へ（sidecar .json / credits.json から許諾を記録）
#   storyboard.json を書き換える（§3）
python3 $SF/scripts/video.py check film                             # 必須項目・ファイル・見出し長・読む時間・クレジット
python3 $SF/scripts/video.py stills film                            # 各シーン 1 枚 → film/out/sheet.png を Read で目視
python3 $SF/scripts/video.py motion film --scene 2                  # 1 シーンの動きを 12 コマで確認（motion-graphics.md §7）
python3 $SF/scripts/video.py det film                               # 決定性（同じフレームを 2 回描いて完全一致）
python3 $SF/scripts/video.py render film --draft                    # 半分の解像度で通し確認（速い）
python3 $SF/scripts/video.py render film --out tour.mp4             # 本番 1080p。out/tour-sheet.png も目視。点滅検査つき
```
素材は slide の assets.py で探して pick したものをそのまま `add` できる（deck の credits.json から許諾を引き継ぐ）。ユーザー素材は `--own "<権利者>"`。
3D の惑星などには **正距円筒図法（2:1）のテクスチャ**を使う（NASA 3D Resources など。§5）。

Remotion Studio で触りたいときは `cd film && npx remotion studio src/index.ts`（ブラウザでタイムライン確認。GPU があれば `--gl` 指定不要）。

## 2. 絶対ルール（壊れた動画の原因の 9 割）
1. **動きはすべて `useCurrentFrame()` から計算する**。`Date.now()`・`performance.now()`・`Math.random()`・three の `useFrame`/`Clock`・CSS アニメーション／transition は禁止（並列レンダーでコマごとにバラバラになる）。乱数は `mulberry32(seed)`。`video.py det` がこれを検査する
2. **非同期の読み込みは `delayRender`/`continueRender` で待つ**。テクスチャは `useTexture()`、画像は Remotion の `<Img>`、フォントは `<Fonts>` が待つ。自前で `TextureLoader` を呼ぶと**黒いコマ**になる
3. **日本語の文字は `lang="ja"` の中に置き、`word-break: auto-phrase` + `text-wrap: balance`**（語の途中で改行しない）
4. **ヘッドレスでは `--gl=swangle`**（GPU なしのソフトウェア WebGL。video.py が自動指定）。並列数は CPU コア数まで（超えると失敗する）
5. **3D の上の文字は HTML で重ねる**（WebGL 内に文字を描かない）。文字は 3D の反対側の列に置き、被写体と重ねない
6. 素材はすべて `public/` 配下を `staticFile()` で参照（外部 URL を直接読まない。レンダー中にネットが落ちると止まる）

## 3. storyboard.json
```jsonc
{
  "title": "…", "theme": "signal", "lang": "ja", "fps": 30, "width": 1920, "height": 1080,
  "transition": { "type": "fade", "seconds": 0.6 },   // "none" でカット
  "sky": "media/star-map.jpg",                          // 任意: 星空の天球テクスチャ（globe / stars カードの背景）
  "fonts": ["Murecho", …], "style": { "bg","fg","muted","accent","glow","head","body","num","mono" },   // new --theme が埋める
  "scenes": [ … ]
}
```
| type | 用途 | 主なキー |
|---|---|---|
| `title` / `end` | 表紙・締め | `kicker` `title` `sub` `credit` `backdrop`（`stars`＝既定 / `plain` / 画像パス） |
| `globe` | 3D の天体・球体をゆっくり回し、カメラが寄る | `texture`（2:1）`side`（被写体の側 `right`/`left`）`radius` `tilt`° `spin`°/秒 `glow`（大気の色）`glowStrength` `ring`（土星型の環）`sunAngle`° |
| `photo` | 写真にゆっくり寄る（Ken Burns）＋文字側にスクリム | `image` `side` `zoom`［開始,終了］`focus`［x,y］(0–1) `scrim`(0–1) |
| `kinetic` `stat` `steps` `bars` `lottie` | モーショングラフィック（文字・数字・手順・グラフ・Lottie） | **references/motion-graphics.md** を読む |

全体キー `motion`（`calm`/`lively`/`punchy`）で動きの性格、`transition` で既定の遷移、シーンの `transition`/`overlay` で上書き。見出しには `effect` と強調記法（`**` `==` `__` `(( ))`）が効く。

共通の文字キー: `kicker`（小見出し・英字可）→ `title`（主張。26 字以内）→ `big`＋`unit`（カウントアップする数字。桁区切り・小数対応）→ `caption`（補足 1 行）。`credit` は左下に常時表示。
文字は話す順に 0.2〜1.3 秒でせり上がる（rise）。**各シーンの秒数は「入ってから読み終わる」まで**: 目安 1 秒＋全角 10 字/秒（check が警告する）。

## 4. 見た目のコツ
- 1 シーンに主役は 1 つ（球体 or 写真 or 数字）。数字は `big` に 1 つだけ
- 色はテーマのトークン（`new --theme`）から。暗いテーマの方が 3D と光が映える（signal / terminal / blueprint）
- 被写体の位置を左右交互に（`side` を right/left と交互）にすると、フェードでも単調にならない
- カメラは「寄るだけ」。回り込み・急なズーム・回転を重ねない。1 シーン 1 つの動き
- 環のある天体は自動で小さめ（radius 1.05）。環が文字に被るなら `radius` を下げる
- テクスチャが無い抽象テーマなら globe を使わず、photo・title・数字で組む

## 5. 素材とクレジット
- 天体テクスチャ: NASA 3D Resources（github.com/nasa/NASA-3D-Resources, Images and Textures）。NASA 素材はクレジット表記、**NASA のロゴ・記章を使わない、NASA が推奨していると受け取れる表現をしない**。締めに「NASA が本動画を推奨・監修しているものではありません」を入れる
- その他の写真は visuals.md と同じ基準（NC・ND は既定で除外、出所不明は使わない、公式画像は権利者が認めたものだけ）
- シーンに `credit` を必ず書く（check が警告）。CC BY 系は作者名とライセンス名を

## 6. 拡張（新しいシーン種別）
`src/Scenes.tsx` にコンポーネントを追加し、`src/Movie.tsx` の分岐と `scripts/video.py` の `SCENE_TYPES`・`TITLE_MAX` に足す。§2 のルールを守り、追加後は `det` と `stills` を必ず通す。
部品: `useTexture`（待つテクスチャ）、`Starfield`（決定的な星）、`Atmosphere`（フレネルの縁光）、`Ring`（環）、`rise`・`CountUp`・`easeInOut`（`src/lib.tsx`・`Scenes.tsx`）。

## 7. 検証（省略禁止）
1. `check` エラー 0（警告は読んで判断）
2. `stills` の `out/sheet.png` を Read で見る: 文字と被写体が重なっていないか・改行位置・画面端の切れ・読みやすさ・黒コマ
3. `det` が一致
4. 本番 `render` 後、`out/<name>-sheet.png`（24 コマ）を見る。フェードの途中で文字が二重に見えるのは正常
5. 納品: MP4（H.264, 1080p30）。長さ・サイズを伝える。素材のクレジット（credits.json）も一緒に

## 8. トラブル
| 症状 | 原因と対処 |
|---|---|
| 真っ黒なコマ | 読み込みを待っていない → `useTexture` / `<Img>` を使う |
| コマごとに星・位置が変わる／`det` 失敗 | 時計・乱数・`useFrame` を使っている → frame から計算、`mulberry32` |
| 語の途中で改行 | `lang="ja"` の外にある |
| `Target closed` / WebGL エラー | 並列数が多すぎる → `--concurrency` を下げる。`SF_GL=angle` を試す |
| 初回 render でダウンロードが走る | Chromium が見つからない → `SF_BROWSER=<chrome のパス>` |
| 環が暗い・見えない | 環はライト非依存（unlit）。`tilt` と、group の傾き（0.38 rad）で見え方を調整 |
| `HTML in Canvas is not supported` | シェーダー遷移・motionBlur に Chrome 149 以上が必要 → `video.py setup`（Remotion の配布 → 失敗時は npm の @sparticuz/chromium を ~/.cache/slide-forge/chrome149 に展開）。無理なら CSS 遷移に替える |
| `Failed to create WebGL2 context` | Chrome 149 の横に GL ライブラリ（libEGL/libGLESv2/SwiftShader）が無い → `rm ~/.cache/slide-forge/browser.json` して `setup` をやり直す |
| `det` が 3D（globe）のシーンでまれに一度だけ失敗 | WebGL のソフトウェア描画の微小なピクセル差。同じコマで再実行し、続けて一致すれば問題なし。2 回続けて失敗したら `useCurrentFrame()` 以外の時間源（時計・乱数）を疑う |
