# FOSS4G 2026 Hiroshima 発表スライド設計

- **イベント**: FOSS4G 2026 Hiroshima
- **セッション**: 2026-09-02 (水) 17:30, Dahlia1
- **形式**: 発表 20 分 + Q&A 5 分
- **タイトル**: *A Self-Hostable Open-Source Geospatial Platform for Small Teams, with Natural Language Querying via MCP*
- **発表言語**: 英語（スライド・口頭ともに）
- **発表者**: 大塚 昇 (noboru.otsuka@geolonia.com)

このドキュメントはスライド作成の上位計画（spec）。実装手順（撮影・原稿・スライドファイル作成）は別途 plan に落とす。

## 1. 目的と聴衆

### 目的

abstract で打ち出した次の主張を、20 分の中で説得力ある形で伝える:

1. 小規模・非 IT チームを **primary user** に据えた self-hostable な OSS 地理空間プラットフォームが成立する。
2. MCP を通じた自然言語クエリは、こうしたチームの実用ハードルを下げる新しい選択肢になる。
3. 設計上の意図と限界を openly 共有し、コミュニティ議論のきっかけとする。

### 想定聴衆

- FOSS4G の地理空間 OSS 開発者・運用者
- 自治体／NPO／フィールド調査などの小規模組織で GIS を扱う実務者
- AI/LLM × 地理空間に関心がある開発者

技術詳細を深く語る場ではなく、「なぜそう作ったか」「何がうまくいき何がまだ駄目か」を語る thought piece として設計する。

## 2. ナラティブ方針

- **Story-centric**: Why → How → Demo → Reflection の弧で運ぶ。
- **Honest tone**: 限界・未解決点を隠さない。
  - "where it falls short" として 2 点を必ず語る: (1) MCP/自然言語クエリの不安定さ、(2) "self-hostable" と "scale" の現実的限界。
- **Hiroshima venue を意識**: デモデータは広島オープンデータ（避難所・防災ポイント）を用い、ローカル文脈を作る。
- **Tool-neutral**: スライドツールは Marp / Keynote / Google Slides のいずれにも変換可能な記述で本 spec を書く（タイトル・key message・visual・speaker note・時間の 5 要素）。

## 3. タイミング配分

| Part | 内容 | スライド | 時間 |
|---|---|---|---|
| 1 Opening | 1–3 | Title / Hook / Mismatch | 4:00 |
| 2 Design & Architecture | 4–6 | Thesis / Principles / Stack | 5:30 |
| 3 MCP & Demo | 7–9 | MCP bet / Tool catalog / Demo | 4:30 |
| 4 Reflection & Close | 10–14 | What worked / Reflection ×2 / Ask / Q&A intro | 4:30 |
| 予備 | — | 想定外バッファ | 1:30 |
| **合計** |  | 14 枚 | **20:00** |
| Q&A | — | — | 5:00 |

## 4. スライド単位設計

各スライドは `Key message / Visual / Speaker note (英語草案) / Duration` の 4 要素で記述する。Speaker note は最終原稿ではなく方針メモ。

### Part 1 — Opening (4:00)

#### Slide 1 — Title (0:30)

- **Key message**: タイトル提示と自己紹介
- **Visual**: タイトル文字 + 控えめな地図背景（広島周辺ベクター）+ 発表者・所属・日時
- **Speaker note**: "Hello, I'm Noboru Otsuka from Geolonia. Today I'd like to talk about geo-base — a small open-source platform we've been building, and what we've learned about putting AI and self-hosting in front of small geospatial teams."
- **Duration**: 0:30

#### Slide 2 — Hook: Meet the team this is for (1:30)

- **Key message**: *They don't need a platform. They need their data to work.*
- **Visual**: シンプルなシーンイラスト（自治体オフィス／NPO 現場）。文字は 2 行程度。
- **Speaker note**: 具体ペルソナを 1 つ語る — 例: 「5 人の市役所計画課、GIS 担当 1 人、DBA も DevOps もいない。Shapefile を共有フォルダで回している」。聴衆に「自分のお客さんで思い当たる人を 1 人思い浮かべて」と促す。
- **Duration**: 1:30

#### Slide 3 — The mismatch (2:00)

- **Key message**: 既存解はこのチーム向けに作られていない。
- **Visual**: 3 カラムカード — *Enterprise GIS* / *Cloud SaaS* / *Roll-your-own* に対し短い "なぜ合わないか" を 1 行ずつ。
  - Enterprise GIS: requires admin expertise
  - Cloud SaaS: data leaves their control
  - Roll-your-own (PostGIS + tiler + UI): too many moving pieces
- **Speaker note**: 「彼らは『プラットフォームを運用するチーム』ではなく、『地図を見ながら判断する仕事のチーム』。3 つの既存路線は全部、運用や統合のコストを彼らに押し付けてしまう」
- **Duration**: 2:00

### Part 2 — Design & Architecture (5:30)

#### Slide 4 — The thesis: one deployable product (2:00)

- **Key message**: 3 つの部品を 1 つのプロダクトとして畳む。
- **Visual**: hero diagram — 3 ボックス *Tile server* / *Admin dashboard* / *MCP connector* が共通の PostGIS に接続。
- **Speaker note**: 「個別の OSS を組み合わせる代わりに、3 つのインターフェースを同じデータと運用モデルの上に乗せた。これが geo-base の核」
- **Duration**: 2:00

#### Slide 5 — Design principles (2:00)

- **Key message**: Simplicity > breadth。やらないことを明示する。
- **Visual**: 4 つの原則と、それぞれに「だから採用しなかったもの」の対比。
  - *Operational simplicity > feature breadth* → no plugin ecosystem
  - *One person deployable* → no Kubernetes-required path
  - *Open formats only* (GeoTIFF / PMTiles / GeoJSON) → no proprietary binary
  - *Data stays with the team* → no third-party analytics, no telemetry-by-default
- **Speaker note**: 「機能ではなく『運用負荷』を設計指標にした。これは多くの OSS プロジェクトと逆方向の最適化」
- **Duration**: 2:00

#### Slide 6 — The stack at a glance (1:30)

- **Key message**: 普通の OSS 部品で組んでいる。魔法はない。
- **Visual**: レイヤード図 — Browser (MapLibre) / Admin UI (Next.js) / API (FastAPI) / MCP (FastMCP) / PostGIS / Redis / Tigris (S3 private)
- **Speaker note**: 「特殊な依存はない。Fly.io / Vercel / S3 互換のオブジェクトストレージという、現代的で手頃な土台に乗っているだけ」
- **Duration**: 1:30

### Part 3 — MCP & Demo (4:30)

#### Slide 7 — The MCP bet (1:30)

- **Key message**: 小さなチームのボトルネックは「データを持つこと」ではなく「クエリを書くこと」。
- **Visual**: 並列 2 パス図 — `human → Admin UI → DB` と `human → AI client → MCP → DB`
- **Speaker note**: 「『データはあるが SQL も PostGIS 式も書けない』という壁を、AI クライアントというもう一つのインターフェースで迂回できないかと考えた」
- **Duration**: 1:30

#### Slide 8 — What the AI client actually sees (1:00)

- **Key message**: 24+ の MCP ツールがタイル／フィーチャ／メタデータを語彙化している。
- **Visual**: 主要 4–6 ツール名と 1 行説明 + Claude Desktop の呼び出し画面スクショ。
  - `list_tilesets` / `get_tileset_metadata` / `query_features_by_bbox` / `get_feature_properties` / `render_preview` など
- **Speaker note**: 「ツールカタログ全部を覚えてもらう必要はない。重要なのは、AI クライアントから見ると『データを語る語彙』が用意されている、という点」
- **Duration**: 1:00

#### Slide 9 — Demo: upload → preview → ask (2:00)

- **Key message**: 非技術者が end-to-end でできることを実演する。
- **Visual**: 録画スクリーンキャスト埋め込み。左下にステップ進行表示（① Upload / ② Preview / ③ Ask）。広島市オープンデータ「避難所」を使用。
- **Speaker note**: フレーミング: "Watch a non-technical user upload the dataset, preview it, and ask one question in natural language."
- **Duration**: 2:00
- **撮影プラン**: 別節「6. デモ撮影プラン」参照

### Part 4 — Reflection & Close (4:30)

#### Slide 10 — What worked (1:00)

- **Key message**: 1 ツールで「Infra + Analyst + Dev」の三役を畳めた。
- **Visual**: 3 つの短い箇条書き
  - One tool collapsed the infra/analyst/dev trio
  - Fly + Tigris fit a small-team budget
  - Public/private tilesets share the same workflow
- **Speaker note**: 「ここまでは思った通りに動いた、という部分」
- **Duration**: 1:00

#### Slide 11 — Honest reflection 1: NL query is not yet reliable (1:30)

- **Key message**: *Single-tileset の問いは通る。cross-tileset の分析は脆い。*
- **Visual**: 実際の失敗ログのスクショ（ツール選択ミス／列名ハルシネーション）+ そこからの教訓ボックス。
- **Speaker note**: 「隠れた本丸はスキーマ／メタデータの記述設計。LLM にとってデータが『読める』ためには、ツールの記述だけでは足りない」
- **Duration**: 1:30

#### Slide 12 — Honest reflection 2: "self-hostable" is still hard (1:30)

- **Key message**: 1 人で回せるが「気軽に」ではない。Scale 限界も存在する。
- **Visual**: 2 ペイン
  - 左: 運用負荷（Fly / Vercel / Tigris の三点コーディネート）
  - 右: scale 限界（PostGIS 単体、single-team 想定、都市規模マルチテナント未対応）
- **Speaker note**: 「self-hostable と書いたが、誰でもクリック 3 回で立つわけではない。さらに想定規模を超えるとアーキテクチャ自体が合わなくなる」
- **Duration**: 1:30

#### Slide 13 — What we want from this community (0:30)

- **Key message**: OSS 地理空間は non-IT primary users にどう応えられるか、問いを残す。
- **Visual**: repo URL + QR コード + 短い問いかけ 2 行
- **Speaker note**: 「答えではなく問いを置きたい。MCP の schema 記述や非 IT ユーザ向け OSS 設計について、後で話しかけてほしい」
- **Duration**: 0:30

#### Slide 14 — Thanks / Q&A (バッファ 0–1:30 を含む遷移、その後 Q&A セクションへ)

- **Visual**: 連絡先、リポジトリ URL、デモデータ出典（広島市オープンデータポータルの該当 URL）、謝辞
- **Speaker note**: "Thank you. I'd love to hear your questions."
- **時間扱い**: 章の予備バッファ (1:30) を吸収するスライド。Q&A 5:00 はこのスライド表示中に進行する。

## 5. クロスカット要素

### 5.1 視覚スタイル

- 文字密度の上限: 1 スライドあたり本文 3–5 行
- カラー: 落ち着いた 2–3 色のミニマルパレット
- セクションディバイダーには地図画像（MapLibre スクリーンショット）を使い、口頭で章替えを明示
- フォントは sans-serif、最低 24pt（後方席視認性）

### 5.2 スピーカーノート方針

- 各スライドに英語の方針メモ（本ドキュメントに記載済み）。
- 最終原稿は plan フェーズで起こす。読み上げではなく要点メモ。
- ノンネイティブ向けに 1 文を短く、1 スライド内で必ず 1 つの "concrete example" を入れる。

### 5.3 アクセシビリティ

- 図版は color-only に頼らない（パターン／ラベル併用）
- 動画には字幕（英語）を焼き込む

## 6. デモ撮影プラン

### 6.1 データセット

広島市オープンデータポータルから **避難所・防災関連ポイント** を 1 セット選定（plan フェーズで正式 URL を確定）。GeoJSON で取り込み可能なものを優先。

### 6.2 シナリオ（合計 2 分以内）

1. **Upload** (約 30 秒)
   - Admin UI でドラッグ&ドロップ → 検出されたフィールド一覧が表示される
2. **Preview** (約 30 秒)
   - MapLibre プレビューでポイントが広島市域上に描画される
   - 1 ポイントをクリックし feature properties を見せる
3. **Ask in natural language** (約 60 秒)
   - AI クライアントに 1 つ自然言語クエリを投げる
     - 例案: *"How many evacuation shelters are inside the central ward?"* もしくは *"Show me shelters near Hiroshima Station."*
   - 結果が地図に反映される or テキストで返る
   - 結果に対し短いコメント (1 行) を字幕で付ける

### 6.3 録画体裁

- 解像度: 1920×1080
- 字幕: 各ステップタイトルを英語で焼き込み
- BGM なし／クリック音は控えめ
- 失敗カットは再撮影。発表本番でハマらない、安定して動くケースだけを使う

## 7. リスクと対策

| リスク | 対策 |
|---|---|
| 録画デモが本番投影で再生されない | スライドツール埋め込み + MP4 単体ファイルを USB / ローカルに別途持つ |
| Reflection が「ネガティブだけ」に見える | Slide 10 の "What worked" を先に置き、Slide 13 で前向きな問いかけで締める |
| 英語で 20 分話し切れない | スピーカーノート段階で 1 スライドの所要を計測、過剰な箇所を削る |
| Hiroshima OD データのライセンス／加工条件 | plan フェーズで利用条件を確認、出典明記をスライドに含める |
| MCP 失敗事例のスクショに個人情報・社内情報が混入 | スクショは plan フェーズで再撮影、レビュー後に確定 |

## 8. 受け入れ基準

このプレゼンが成功と言える条件:

1. 14 枚のスライドと 2 分以内のデモ録画が揃い、英語で 18:30–20:00 に収まる通し稽古ができている。
2. abstract の 3 つの主張（small-team thesis / MCP の価値 / honest reflection）が、それぞれ少なくとも 1 枚で明示されている。
3. デモが本番環境（投影 PC ＋スクリーン）で確実に再生できることが事前確認済み。
4. Q&A 想定問答を 5 件以上、発表者の手元に持っている。

## 9. 次フェーズ（plan）の範囲

このあと writing-plans スキルで作る implementation plan は次を扱う:

- スライドツール選定の最終判断（Marp / Keynote / Google Slides）
- スライド原稿（タイトル文・本文）の英語確定
- スピーカーノートの英語確定（読まずに話せる粒度のメモ）
- デモ用データセットの確定とライセンス確認
- デモ録画の撮影手順とリテイクポリシー
- 通し稽古スケジュール（少なくとも 2 回）
- 想定問答リスト
- 当日持ち物・バックアップ計画
