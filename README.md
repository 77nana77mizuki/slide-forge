# Slide Forge — アニメーション付き HTML スライド生成ハーネス

Claude に「発表資料を作って」と頼むだけで、**構成設計 → テーマ選定 → 制作 → 自動検証 → 独立レビュー** の流れを踏んで、
1 ファイルで動くアニメーション付き HTML スライドを作るためのハーネス（スキル＋サブエージェント＋スクリプト）です。

```
依頼 ─▶ ① ブリーフ ─▶ ② outline.md ──[outline.py check]──▶ ゴーストデッキ確認
                         (slide-storyteller)                        │
      ③ テーマ 3 案プレビュー [themes.py preview] ◀─────────────────┘
                         │
      ④ ビジュアル調達 [assets.py]（必要なスライドだけ・フリー素材・ライセンス記録）
                         (slide-art-director)
      ⑤ outline.py scaffold → deck.src.html を設計 → build.py → deck.html（単一ファイル）
                         │
      ⑥ check.py（はみ出し・重なり・文字サイズ・コントラスト・写真上の文字・画像解像度・密度・フォント）
         → contact sheet / モーションのコマ撮りを目視 → 修正ループ
         → slide-reviewer（作り手と独立した採点・読み取り専用）
                         │
      ⑦ 納品: deck.html ＋ PDF（ベクター）／ PNG ／ 動画（webm・mp4）
```

## 何ができるか
- **スライド本体（ランタイム・依存ゼロ）**: 1920×1080 固定ステージを画面に合わせて拡縮 / キーボード・クリック・スワイプ / クリックで順に出すステップ（前の項目を薄くするフォーカスモード付き）/ 自動で時間差がつく入場アニメーション 14 種 / 数字のカウントアップ / 棒・縦棒・ドーナツグラフの伸長 / SVG の線描画 / View Transitions API による遷移 6 種と **マジックムーブ（`data-morph`）** / **発表者ビュー（S: ノート・次スライド・タイマー）** / 一覧（O）/ ブラックアウト（B）/ **ブラウザ上で文字を直接編集して保存（E → Ctrl+S）** / 印刷・PDF 対応 / `prefers-reduced-motion` 対応
- **フリー素材の調達**: Openverse・Wikimedia Commons（キー不要）、Pixabay・Unsplash・Pexels（無料キー）、社内/手元フォルダ（`local:`）から検索 → 番号付き候補シートを Claude が**目で見て**選ぶ → トリミング・テーマ色処理（duotone 等）→ `credits.json` にライセンス記録。NC（非営利）・ND（改変禁止）は既定で除外
- **アイコン**: `<i class="ico" data-icon="tabler:robot"></i>` と書くだけで build が SVG を取得・埋め込み（テーマ色に追従）。Tabler / Lucide / Phosphor / Material Symbols / Fluent Emoji など 20 万点以上
- **クレジット自動化**: 表示義務のある素材には画像上にキャプション、末尾にクレジットスライド（改変内容も明記）。記録のない画像・非営利素材は build が警告
- **7 テーマ**: swiss（最も無難）・washi・blueprint・signal・forest・terminal・pop。全レイアウト×全テーマでコントラスト検証済み
- **日本語組版**: 文節改行（`word-break: auto-phrase`）、`text-wrap: balance`、禁則、見出しの字詰め、泣き別れ検出
- **オフライン対応**: `--fonts embed` で「デッキで実際に使っている文字」を含むフォントサブセットだけを埋め込み（会場 Wi-Fi 不要）
- **映像（Remotion × three.js）**: `storyboard.json` 1 つから 1080p の MP4 を書き出し。3D の天体（テクスチャ・大気の縁光・土星型の環・カメラの寄り）、写真のゆっくりズーム、数字のカウントアップ、フェード遷移。テーマの色・フォントを共有し、事前チェック（読む時間・見出し長・素材の許諾）、シーンごとの静止画シート、決定性チェック付き。※Remotion は個人・3 人以下の会社・非営利は無料、それ以外の企業利用は有料ライセンス
- **モーショングラフィック**: 動きの性格を 3 プリセット（calm / lively / punchy）で統一。日本語を文節単位で動かすキネティックタイポ 9 種（rise・mask・pop・slam・blur・type・tracking・scramble・shimmer）と手描き風マーカー、数字＋リング、線が伸びる手順図、横棒グラフ、Lottie、背景 6 種、遷移 20 種＋光漏れ。1 シーンのコマ撮り確認と点滅検査（WCAG 2.3.1）付き。Web の動きのカタログ（Magic UI・Motion Primitives・Anime.js など）は見た目だけ参考にし、コマ単位で決まる形に作り直してある。CC0 の素材（3dicons・Kitbitz）は `video.py add --license CC0` で許諾を記録して使える
- **データベース図・画面イメージ（v1.5）**: JSON を書くだけで、テーブルと関連の図（PK/FK・例データ・線が描かれるアニメーション）と、表計算ソフトで開いた出力ファイルの画面（列記号・行番号・シートタブ・セルを指す吹き出し）を生成。旧・新の CSV を渡すと新規／更新／削除を突き合わせ、旧データはグレー・新データはグリーン・変わったセルは赤で自動表示。システム提案・ヒアリング資料向け
- **Web アプリ・スマホの画面イメージ（v1.6）**: ブラウザ（タブ・アドレスバー・メニュー）かスマホの枠に、KPI・折れ線・棒・ドーナツ・一覧・進捗・ガント・表・フォームのパネルを JSON で配置。画面の左右に「管理者画面」「利用者の声」などの注記カードを置き、パネルまで引き出し線を自動で引く。要件ヒアリング資料向け
- **表現の拡張（v1.7）**: 目標線・吹き出し・期間帯・強調を書き込めるグラフ（棒・横棒・折れ線・面・散布図）と、スライドをまたいで棒が並べ替わるグラフのモーフ / Prezi 風のズームキャンバス（全体図からクリックごとに寄る）/ 手描き風の丸・下線・囲み・蛍光ペン / 版ごとにトークンが滑って変わるコード / 線の上をデータの粒が流れる構成図とシーケンス図 / ベントーグリッド（縁を光が回るタイル）/ ドラッグできる前後比較スライダー / 47 都道府県のタイル地図 / 動画用だったキネティック文字（mask・words・type・scramble・slam・tracking）/ three.js の地球儀（都市と弧）・3D モデル（.glb）・立体
- **品質保証**: レンダリング後の自動検査（16 種。写真上の文字は実際の描画ピクセルでコントラストを計測）＋スクリーンショットの一覧画像＋アニメーションのコマ撮り＋独立レビュアー

## 設計の根拠（2026 年時点の調査）
| 知見 | ハーネスでの反映 |
|---|---|
| スライドを HTML で扱うと LLM の生成成功率が大きく上がる（PPTAgent のアブレーションで 74.6%→95.0%）。評価は Content / Design / Coherence の 3 軸 | 出力は HTML。レビュールーブリックはこの 3 軸＋Message・Motion・Audience |
| レンダリング結果を見て直す「環境に根ざした振り返り」が品質を上げる（DeepPresenter, SlideForge 論文） | check.py の実測＋スクリーンショット目視を必須ループに |
| 人気 HTML スライドスキル（frontend-slides）の実践: 1920×1080 固定ステージ、密度モード、スタイルは「見せて選ばせる」、AI っぽい見た目の回避 | 固定ステージ、speaker/reading 密度、themes.py preview、AI slop 回避ルール |
| Anthropic のスキル作成ガイド: SKILL.md は短く・参照は 1 階層・決定的処理はスクリプト化・plan→validate→execute・評価を先に作る | 500 行未満の SKILL.md、references/ 5 本、outline.py による計画検証、evals/ と tests/ |
| 1 スライド 1 メッセージ、見出しは主張で書く | outline.py がトピックラベル見出しをエラーに |
| View Transitions は reduced-motion で無効化、transform/opacity 中心で動かす | ランタイムが自動対応 |

## リポジトリ構成
| パス | 内容 |
|---|---|
| `skills/slide-forge/` | スキル本体（SKILL.md・references・scripts・テーマ・ランタイム・動画の雛形） |
| `agents/` | サブエージェント（構成作家・画像担当・独立レビュアー） |
| `claude-ai/SKILL.md` | claude.ai（Web・アプリ）用の起動版 SKILL.md。本体は Artifact のバンドル（`sf-bundle.json`）から取り込む |
| `tests/` `evals/` | 回帰テスト（`tests/run_all.sh`）と評価 |

## 変更履歴
### v1.7（2026-09-27）
- **表現力の強化 10 種**（`references/expressive.md`、実例 `assets/examples/fx/fx.src.html`）
  1. 注釈付きグラフ `data-mock="chart"`（`scripts/mock_chart.py`）: bar / hbar / line / area / scatter、`highlight`・`sort`・`top`、注釈 target / band / point / note、系列をクリックで追加。同じ `id` のグラフを並べると棒と値がモーフ
  2. ズームキャンバス（`L-zoom`・`.zoom-view`）: `data-zoom` の順にカメラが寄り、領域間は少し引いて移動。寄ったときだけ出る `.zoom-detail`
  3. 手描きの注釈 `data-annotate`（underline / circle / box / highlight / strike / cross / bracket）: 揺れは文字列から決まるので毎回同じ形。クリックで描ける
  4. コードの変化 `data-codemove`: 版の間で共通トークンを LCS で対応づけ、FLIP で移動・追加分だけフェード。自動の色分け・行強調・ファイル名タブ
  5. 構成図 `arch` と シーケンス図 `seq`（`scripts/mock_diagram.py`）: 自動配線（直線／L 字・往復のずらし）、線の上を流れるデータの粒（offset-path）、クリックで段階表示
  6. ベントーグリッド（`L-bento`・`.bento`）と Border Beam（Magic UI〔MIT〕の考え方）
  7. 前後比較スライダー `.ba-slider`: 入場時に掃く・クリックで指定位置へ・ドラッグ可
  8. 日本のタイル地図 `data-mock="japan"`: 値の濃淡（文字色は自動で読みやすい方）、強調、ピン
  9. キネティック文字 `data-anim="mask|words|type|scramble|slam|tracking"`（日本語は Intl.Segmenter で単語分割）
  10. 3D `data-3d="globe|model|shape"`: three.js r186（MIT）を使うデッキだけに同梱。陸地ドットは Natural Earth（パブリックドメイン）から作ったマスク。表示中のスライドだけ描画、PDF は静止 1 コマ
- ランタイム: `slides-fx.js` を追加（slides.js より前に読み込み、クリック連動の状態を見えないステップマーカーで管理）。slides.js は `deck:layout` イベント（フォント・自動縮小の確定後）を発行し、E 編集の保存時に効果の DOM を取り除く
- check: ズームキャンバス・比較スライダー・グラフ／図の中の判定を調整。build: 新しいアニメ名・`data-annotate`・`data-3d` の lint、`.glb` の埋め込み、three.js の条件付き同梱
- テスト: `tests/test_fx.py`（ズーム・コード・スライダー・注釈・3D・書き出しの最終状態）を `run_all.sh` に追加。7 テーマすべてで fx デッキのエラー 0

### v1.6（2026-09-27）
- **Web アプリ・スマホの画面イメージ**を追加（`data-mock="app"`、`scripts/mock_app.py`、`references/layouts.md` §8、実例 `assets/examples/mock/app.src.html`）
  - ブラウザ（タブ・アドレスバー・URL・左メニュー・ヘッダー）とスマホ（ノッチ・ステータスバー・下タブ）の枠
  - パネル 11 種（kpi / line / bars / donut / list / progress / gantt / table / form / profile / text）をグリッドに自動配置
  - 画面の左右の注記カードから、指定したパネルの端まで引き出し線を自動で引く。注記の幅は文字数から自動計算。吹き出しもパネルを指定して付けられる
- check: 画面イメージの枠（mk-device / mk-sheet / mk-entity）を solid として扱い、出典や本文がぶつかると `text-over-graphic` で検出（画面自身の文字・注記・吹き出しは対象外）
- 回帰テストに Web アプリの画面イメージのデッキを追加

### v1.5（2026-09-27）
- **データベース図と表計算ソフトの画面イメージ**を追加（`scripts/mock.py`、`references/layouts.md` §7、実例 `assets/examples/mock/`）
  - `<div data-mock="er" data-src="db.json">` → テーブル（PK/FK・例データ）と 1:N の線。縦積み・横並び・枝分かれ
  - `<script type="application/json" data-mock="sheet">` → タイトルバー・数式バー・列記号・行番号・シートタブ付きの画面。`diff` に旧・新（配列か CSV）とキーを渡すと、新規／更新／削除／変化なしの判定、旧＝グレー・新＝グリーンの帯、差分の記号、変更セルの強調まで自動。`callouts` でセル番地を指す吹き出し（クリックで順に表示）
  - 寸法はすべて em 基準で計算し、列幅は全 7 テーマのフォントで実測した字幅から決めるので、テーマを変えてもはみ出さない
- check: 画面イメージの中の 20〜23px の文字は小さな文字の警告から除外（20px 未満は従来どおりエラー）
- 回帰テストに画面イメージのデッキと新旧判定を追加

### v1.4（2026-09-26）
- **OSS を実際に組み込む手順**を追加（`references/resources.md` §5）: Magic UI・Motion Primitives・Uiverse・Anime.js（MIT）、3dicons（CC0）を GitHub / npm から取得し、作者と許諾文を残して使う。Uiverse は iframe に隔離、Anime.js は `deck:change` で再生、許諾文は `<script type="text/plain" id="oss-licenses">` で同梱
- **日本のフリー素材の扱い**（§6）: ソコスト等は自動取得しない。ユーザーが添付したものをそのまま配置（ソコストは AI での画像生成への利用を禁止）
- build: 最初のスライドより前に書いた `<script>` が捨てられていた → 末尾に移して残す／クリック数の警告が要素数で数えていた → 実際のクリック数で数える
- check: `.bleed` の中の意図的なはみ出し（流れる帯・背景演出）を clip エラーから除外／`aria-hidden` と `data-density-skip` を文字量から除外
- runtime: コード欄の合字（`<!--` が矢印になる）を無効化／ドーナツのラベルを `--size` に比例
- themes.py preview: 各テーマの表紙を `previews/<theme>.png` にも保存
- 目視で見つけた落とし穴（予約クラス名 `.bg` との衝突、ライトテーマの `media-bg` で写真が霞む、動く前の要素の初期位置など）を layouts.md・qa.md に追記

## インストール
### A. Claude Code プラグインとして（推奨）
```text
/plugin marketplace add /path/to/slide-forge
/plugin install slide-forge@slide-forge
```
スキルは `/slide-forge:slide-forge`、エージェントは `slide-storyteller` / `slide-reviewer` として使えます。

### B. 手動コピー
```bash
cd slide-forge && ./install.sh            # ~/.claude に（全プロジェクト）
./install.sh --project                    # ./.claude に（このプロジェクトのみ）
```
依存: Python 3.10+ と `pip install playwright pillow && python -m playwright install chromium`（install.sh が実行）。
npm があれば、Google Fonts に届かない環境でも `@fontsource` からフォントを埋め込めます。
PPTX 変換を使うなら `pip install python-pptx`。

### C. claude.ai（Web/デスクトップのスキル）
`skills/slide-forge` フォルダを zip にしてスキルとしてアップロードできます。ただし検証スクリプトはブラウザ（Chromium）を使うため、
**フルの検証ループは Claude Code 推奨**です。

## 使い方
```text
/slide-forge 来週の勉強会（15分・エンジニア30人）で「生成AIでのコードレビュー」を話す資料を作って
/slide-forge この報告書を役員向けの配布資料にして（印刷もする）   ← ファイルを添付
/slide-forge talk.pptx を HTML スライドに変換して、構成も改善して
```
スクリプトを直接使うこともできます（`SF=skills/slide-forge`）:
```bash
python3 $SF/scripts/outline.py check outline.md                       # 構成の検査＋見出し一覧
python3 $SF/scripts/outline.py scaffold outline.md -o deck.src.html   # 叩き台生成
python3 $SF/scripts/themes.py preview --title "…" --points "a,b,c" --themes swiss,signal,washi
python3 $SF/scripts/assets.py search "factory robot arm" --kind photo       # 候補＋sheet.png（deck フォルダで実行）
python3 $SF/scripts/assets.py pick img/_cand/factory-robot-arm 3 --as img/hero.jpg --crop 16:9 --treat duotone --theme signal
python3 $SF/scripts/assets.py icon "shield check" --sheet                  # アイコン見比べ
python3 $SF/scripts/assets.py credits deck.src.html                        # ライセンス一覧・記録漏れ
python3 $SF/scripts/build.py deck.src.html [--theme signal] [--fonts embed] [--watch]
python3 $SF/scripts/check.py deck.html --out qa/ [--motion 5]
python3 $SF/scripts/export.py deck.html [--png shots/]                # ベクター PDF / PNG
python3 $SF/scripts/record.py deck.html                               # 自動再生動画（スライドの録画）
python3 $SF/scripts/video.py new film --theme signal                  # 映像作品（Remotion × three.js）→ references/video.md
python3 $SF/scripts/extract_pptx.py talk.pptx -o work/                # PPTX → outline.md 下書き
```

### 画像検索の API キー（任意）
キーなしでも Openverse・Wikimedia Commons・アイコンは使えます。写真の質と量を上げたい場合は無料キーを環境変数に:
```bash
export PIXABAY_API_KEY=...      # https://pixabay.com/api/docs/   （日本語検索可・イラスト/ベクターも）
export UNSPLASH_ACCESS_KEY=...  # https://unsplash.com/developers
export PEXELS_API_KEY=...       # https://www.pexels.com/api/
```
社内の写真フォルダは `--sources local:/path/to/photos`（同名の `.json` に `{"license":"...","creator":"...","tags":[...]}` を置くとライセンス・タグ検索に使われます）。
いらすとや等 API の無い素材サイトは、自分でダウンロードして `assets.py add img/x.png --license "..." --source-url ...` で記録してください。

### 発表時のキー操作
| キー | 動作 |
|---|---|
| → / Space / クリック | 次へ（ステップ → スライド） |
| ← | 戻る |
| S | 発表者ビュー（ノート・次のスライド・タイマー。こちらからも操作可） |
| O | 一覧（クリックでジャンプ） |
| 数字 + Enter | 指定スライドへ |
| F / B | 全画面 / ブラックアウト |
| E → Ctrl(⌘)+S | 文字を直接編集してファイル保存（Esc で終了） |
| ? | ヘルプ |

## ファイル構成
```
slide-forge/
├── .claude-plugin/        plugin.json, marketplace.json
├── agents/
│   ├── slide-storyteller.md   構成作家（outline.md を作って検証）
│   ├── slide-art-director.md  画像・アイコン調達（入れるべき所の判断→検索→目視選定→加工→ライセンス記録）
│   └── slide-reviewer.md      独立レビュアー（読み取り専用・6 軸採点）
├── skills/slide-forge/
│   ├── SKILL.md               ワークフロー（地図）
│   ├── references/            narrative / design / visuals / layouts / motion / qa / video / motion-graphics
│   ├── assets/runtime/        slides.css, slides.js（build が同梱）
│   ├── assets/themes/         7 テーマ
│   ├── assets/examples/       sample.src.html（16 枚の全機能デモ）, outline.example.md
│   ├── assets/video-template/ Remotion × three.js の雛形（src/, render.mjs, 太陽系とモーションの storyboard 例）
│   └── scripts/               outline, themes, assets, build, fonts, check, export, record, extract_pptx, video
├── tests/                     run_all.sh（全テーマ×QA、負例テスト、操作テスト、動画、PDF）
├── evals/                     評価シナリオ 6 本
└── install.sh
```

## カスタマイズ
- 色だけ変える: deck-config に `"tokens": {"--accent": "#0B6E4F", "--accent-ink": "#08563D"}`
- 新テーマ: `assets/themes/swiss.css` をコピーして編集（書式は references/design.md §7）。`tests/run_all.sh` で全レイアウトの検証が走ります
- 社内ルール（ロゴ位置・必須の表紙情報など）は SKILL.md の「核となる考え方」に 1 行足すのが最も効きます

## テスト
```bash
tests/run_all.sh              # Google Fonts リンク版
FONTS=embed tests/run_all.sh  # オフライン埋め込み版
```
7 テーマ × 16 枚のサンプルがエラー 0、既知の欠陥（はみ出し・重なり・極小文字・低コントラスト・画像切れ・過密）を 6 種とも検出、
画像パイプライン 11 項目（NC 除外、トリミング・色処理、ライセンス記録、アイコン埋め込み、クレジット自動生成、写真上の文字・低解像度・記録漏れの検出）、操作テスト 20 項目（ステップ送り/戻し、カウントアップ、一覧、ジャンプ、モーフ遷移、編集→保存→再読込、発表者ビュー連動、reduced motion）、動画 25 項目（雛形・素材記録・storyboard 検査の正例/負例、全シーン種別の静止画、WebGL 描画、決定性、モーション例・負例 5 種・コマ撮り・点滅検査の正例/負例）、PDF 16 ページ。

## 出典
- Zheng et al., *PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides* (2025) — https://arxiv.org/html/2501.03936
- *DeepPresenter* (2026) — https://arxiv.org/pdf/2602.22839 ／ *SlideForge* (2026) — https://arxiv.org/html/2609.03109
- zarazhangrui/frontend-slides — https://github.com/zarazhangrui/frontend-slides
- Anthropic, Skill authoring best practices — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Claude Code, Create custom subagents — https://code.claude.com/docs/en/sub-agents
- web.dev, View transitions & prefers-reduced-motion — https://web.dev/learn/css/view-transitions-spas
- MDN, word-break: auto-phrase — https://developer.mozilla.org/ja/docs/Web/CSS/word-break
