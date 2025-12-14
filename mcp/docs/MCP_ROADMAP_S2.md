# geo-base プロジェクト セカンドシーズン ロードマップ

## MCPサーバー機能拡充

**開始日**: 2025-12-14  
**プロジェクト**: geo-base MCP Server Enhancement  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**対象ディレクトリ**: `/mcp`  
**現行バージョン**: 0.2.0  
**目標バージョン**: 1.0.0

---

## 1. プロジェクト概要

### 1.1 目的

geo-base MCPサーバーの機能を拡充し、Claudeを通じた地理空間データの分析・操作を強化する。
特に「空間分析ツール（`tool_analyze_area`）」の実装を最重要ゴールとして位置づける。

### 1.2 最重要ゴール

**`tool_analyze_area` - 指定範囲の空間分析ツール**

指定したバウンディングボックス内の地理空間データを分析し、以下の情報を提供：
- フィーチャー数・タイプ分布
- 面積・距離の計算
- 密度分析
- 空間的な統計情報
- 近隣分析

### 1.3 期待される成果

- 保守性の高いコードベース（ロギング・エラーハンドリング強化）
- 強力な空間分析機能
- 充実したテストカバレッジ
- プロダクション品質のMCPサーバー

---

## 2. アーキテクチャ

### 2.1 現在の構成

```
mcp/
├── server.py              # FastMCPサーバー本体（16ツール）
├── config.py              # 設定管理
├── tools/
│   ├── __init__.py
│   ├── tilesets.py        # タイルセット関連ツール（3ツール）
│   ├── features.py        # フィーチャー関連ツール（2ツール）
│   ├── geocoding.py       # ジオコーディングツール（2ツール）
│   └── crud.py            # CRUD操作ツール（6ツール）
├── tests/
│   ├── conftest.py
│   ├── test_tools.py
│   ├── test_geocoding.py
│   ├── test_crud.py
│   └── live_test.py
├── Dockerfile
├── fly.toml
└── pyproject.toml
```

### 2.2 セカンドシーズン後の構成

```
mcp/
├── server.py              # FastMCPサーバー本体（20+ツール）
├── config.py              # 設定管理（バリデーション強化）
├── logger.py              # 【新規】ロギング設定
├── errors.py              # 【新規】カスタムエラー定義
├── retry.py               # 【新規】リトライ処理ユーティリティ
├── validators.py          # 【新規】入力バリデーション
├── tools/
│   ├── __init__.py
│   ├── tilesets.py        # タイルセット関連ツール
│   ├── features.py        # フィーチャー関連ツール
│   ├── geocoding.py       # ジオコーディングツール
│   ├── crud.py            # CRUD操作ツール
│   ├── stats.py           # 【新規】統計ツール
│   └── analysis.py        # 【新規】空間分析ツール ⭐最重要
├── tests/
│   ├── conftest.py
│   ├── test_tools.py
│   ├── test_geocoding.py
│   ├── test_crud.py
│   ├── test_stats.py      # 【新規】統計ツールテスト
│   ├── test_analysis.py   # 【新規】空間分析ツールテスト
│   ├── test_validators.py # 【新規】バリデーションテスト
│   └── live_test.py
├── Dockerfile
├── fly.toml
└── pyproject.toml
```

---

## 3. 開発フェーズ

### Phase 1: 基盤強化（ロギング・エラーハンドリング）

保守運用性を向上させるための基盤整備。

#### Step 2.5-A: ロギング基盤の追加

**目的**: 構造化ロギングによるデバッグ・監視の容易化

**タスク**:
- [ ] `logger.py` の作成（structlog または標準logging）
- [ ] 各ツールへのロギング追加
- [ ] ログレベル設定（環境変数対応）
- [ ] リクエスト/レスポンスのログ出力
- [ ] エラーログの詳細化

**成果物**:
- `mcp/logger.py`
- 全ツールのロギング対応

**参考**: documentor.txtのprintベースログを発展

---

#### Step 2.5-B: エラーハンドリング・リトライ処理の強化

**目的**: 信頼性の高いAPI通信と詳細なエラー情報

**タスク**:
- [ ] `errors.py` の作成（カスタム例外クラス）
- [ ] `retry.py` の作成（tenacity活用）
- [ ] HTTPエラーの詳細分類（401/403/404/5xx）
- [ ] 一時的エラーへの指数バックオフリトライ
- [ ] タイムアウト設定の最適化

**成果物**:
- `mcp/errors.py`
- `mcp/retry.py`
- 全ツールのエラーハンドリング強化

**参考**: openweather-mcp.txtの404/401分岐パターン

---

### Phase 2: 機能拡充

新しいツールの追加。

#### Step 2.5-C: 統計ツールの追加

**目的**: システム・タイルセットの統計情報へのアクセス

**タスク**:
- [ ] `tools/stats.py` の作成
- [ ] `tool_get_system_stats` の実装
- [ ] `tool_get_tileset_stats` の実装
- [ ] `test_stats.py` の作成
- [ ] server.pyへの統合

**新規ツール**:

| ツール名 | 説明 |
|---------|------|
| `tool_get_system_stats` | システム全体の統計（タイルセット数、フィーチャー数等） |
| `tool_get_tileset_stats` | 特定タイルセットの統計（フィーチャー数、ジオメトリ分布等） |

**成果物**:
- `mcp/tools/stats.py`
- `mcp/tests/test_stats.py`

---

#### Step 2.5-D: 空間分析ツールの追加 ⭐最重要

**目的**: 指定範囲の空間データを分析する高度な機能

**タスク**:
- [ ] `tools/analysis.py` の作成
- [ ] `tool_analyze_area` の実装
- [ ] `tool_calculate_distance` の実装
- [ ] `tool_find_nearby_features` の実装
- [ ] `test_analysis.py` の作成
- [ ] server.pyへの統合

**新規ツール**:

| ツール名 | 説明 | 優先度 |
|---------|------|--------|
| `tool_analyze_area` | 指定範囲の総合分析（フィーチャー統計、密度等） | ⭐最高 |
| `tool_calculate_distance` | 2点間の距離計算 | 高 |
| `tool_find_nearby_features` | 指定地点の近隣フィーチャー検索 | 高 |
| `tool_get_area_bounds` | 複数フィーチャーのバウンディングボックス計算 | 中 |

**`tool_analyze_area` 詳細設計**:

```python
@mcp.tool()
async def tool_analyze_area(
    bbox: str,
    tileset_id: str | None = None,
    analysis_type: str = "summary",
) -> dict:
    """
    指定範囲内の地理空間データを分析します。
    
    Args:
        bbox: バウンディングボックス "minx,miny,maxx,maxy" (WGS84)
        tileset_id: 分析対象のタイルセットID（省略時は全タイルセット）
        analysis_type: 分析タイプ
            - "summary": 基本統計（フィーチャー数、タイプ分布）
            - "density": 密度分析（面積あたりフィーチャー数）
            - "distribution": 空間分布分析
            - "full": 全分析
    
    Returns:
        分析結果（フィーチャー数、タイプ分布、面積、密度等）
    """
```

**成果物**:
- `mcp/tools/analysis.py`
- `mcp/tests/test_analysis.py`

---

### Phase 3: 品質向上

コード品質とテストカバレッジの向上。

#### Step 2.5-E: 入力バリデーション強化

**目的**: 不正な入力からの保護と明確なエラーメッセージ

**タスク**:
- [ ] `validators.py` の作成
- [ ] UUIDフォーマット検証
- [ ] bbox形式検証（"minx,miny,maxx,maxy"）
- [ ] GeoJSONジオメトリ検証
- [ ] 座標範囲検証（経度: -180〜180、緯度: -90〜90）
- [ ] `test_validators.py` の作成

**成果物**:
- `mcp/validators.py`
- `mcp/tests/test_validators.py`

---

#### Step 2.5-F: テストコードの拡充

**目的**: 高いテストカバレッジによる品質保証

**タスク**:
- [ ] モックを使った単体テストの追加
- [ ] エラーケースのテスト追加
- [ ] 境界値テストの追加
- [ ] 統合テストの追加
- [ ] カバレッジ80%以上を目標

**成果物**:
- 各ツールのテストファイル更新
- pytest-covによるカバレッジレポート

---

## 4. マイルストーン

| フェーズ | Step | 内容 | 目標期間 | 成果物 |
|---------|------|------|---------|--------|
| Phase 1 | 2.5-A | ロギング基盤 | 1週間 | logger.py |
| Phase 1 | 2.5-B | エラーハンドリング | 1週間 | errors.py, retry.py |
| Phase 2 | 2.5-C | 統計ツール | 1週間 | tools/stats.py |
| Phase 2 | 2.5-D | 空間分析ツール⭐ | 2週間 | tools/analysis.py |
| Phase 3 | 2.5-E | バリデーション | 1週間 | validators.py |
| Phase 3 | 2.5-F | テスト拡充 | 1週間 | test_*.py更新 |

**合計見込み期間**: 7〜8週間

---

## 5. 技術スタック

### 5.1 追加予定の依存関係

| パッケージ | 用途 | バージョン |
|-----------|------|-----------|
| tenacity | リトライ処理 | >=8.0.0 |
| structlog | 構造化ロギング | >=23.0.0（オプション） |
| pydantic | バリデーション | >=2.0.0（既存利用拡張） |

### 5.2 開発ツール

| ツール | 用途 |
|--------|------|
| pytest | テスト実行 |
| pytest-asyncio | 非同期テスト |
| pytest-cov | カバレッジ計測 |
| ruff | リンター |
| mypy | 型チェック |

---

## 6. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| APIサーバーの変更 | 中 | APIバージョニング、テストによる検知 |
| 空間分析の計算負荷 | 高 | ページネーション、制限値設定 |
| 依存関係の競合 | 低 | uv.lockによる固定 |
| テスト環境の不安定性 | 中 | モック活用、本番API依存の最小化 |

---

## 7. 成功基準

### 7.1 機能要件

- [ ] `tool_analyze_area` が動作すること
- [ ] 全ツールにロギングが実装されていること
- [ ] エラー時に詳細なメッセージが返ること

### 7.2 品質要件

- [ ] テストカバレッジ 80% 以上
- [ ] 型チェック（mypy）がパスすること
- [ ] リンター（ruff）がパスすること

### 7.3 運用要件

- [ ] Fly.ioへのデプロイが成功すること
- [ ] Claude Desktopから全ツールが呼び出せること
- [ ] ドキュメントが最新化されていること

---

## 8. 参考資料

- [MCPサーバー開発ベストプラクティス](./MCP_BEST_PRACTICES.md)
- [セカンドシーズン引き継ぎドキュメント](./HANDOVER_S2.md)
- [MCPサーバープレゼン資料](./MCP_PRESENTATION.md)
- [FastMCP公式ドキュメント](https://github.com/jlowin/fastmcp)
- [Model Context Protocol仕様](https://modelcontextprotocol.io/)

---

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2025-12-14 | 初版作成 |
