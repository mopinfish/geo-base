# デモデータセット記録

このページは、発表デモで使用する公開データの出典、加工方法、再現手順をまとめたものです。
Admin UIへの取り込み、MapLibreプレビュー、MCPによる検索は2026-08-07に確認しました。

---

## データセット基本情報

| 項目 | 値 |
|---|---|
| データセット名 | 指定緊急避難場所データ_34広島県（広島市中区抽出） |
| 出典URL | https://www.geospatial.jp/ckan/dataset/hinanbasho （元データ: https://www.gsi.go.jp/bousaichiri/hinanbasho.html） |
| 提供元（広島市 / 広島県 / その他） | 国土地理院（一般社団法人 社会基盤情報流通推進協議会 AIGID が加工・GeoJSON化して公開） |
| ライセンス | クリエイティブ・コモンズ 表示（CC-BY。CKANデータセットページのライセンス欄に記載。バージョン番号の明記なし） |
| 取得日 | 2026-08-07 |
| 形式（GeoJSON / Shapefile / CSV+緯度経度 など、元の配布形式） | GeoJSON（配布時点でGeoJSON形式のため変換不要） |
| フィーチャ数 | 87（全県データ3,135件のうち、`所在地`が「広島県広島市中区」で始まるフィーチャのみを抽出） |
| 座標範囲（bbox: minx, miny, maxx, maxy） | 132.427388, 34.358435, 132.468435, 34.40697 |
| 座標系（CRS） | WGS84 / EPSG:4326（GeoJSON既定。ファイル内に`crs`メンバの明示指定はない） |

属性項目（全フィーチャ共通）: `指定緊急避難場所`（施設名）、`所在地`、`洪水`・`がけ崩れ、土石流及び地滑り`・
`高潮`・`地震`・`津波`・`大規模な火事`・`内水氾濫`・`火山現象`（各項目は`◎`または空文字列で、その災害種別の
指定緊急避難場所として使えるかを表す）。

## 加工内容

1. G空間情報センター（https://www.geospatial.jp/ckan/dataset/hinanbasho）から
   「指定緊急避難場所データ_34広島県（GeoJson）」をダウンロード（全県3,135フィーチャ、すべてPoint）。
2. `所在地`プロパティが文字列 `"広島県広島市中区"` で始まるフィーチャのみを抽出（Python `json`モジュールで
   フィルタしたのみ。座標変換・属性の追加や書き換えは行っていない）。抽出後 87フィーチャ。
3. 出力ファイル: `docs/foss4g-2026/demo/hinanbasho-naka-ku.geojson`（31,886 bytes）。

再現用スニペット（当時実行したものと同一。参照専用、生成パイプラインの一部ではない）:

```python
import json

with open("34.geojson", encoding="utf-8") as f:
    data = json.load(f)

feats = [
    f for f in data["features"]
    if f["properties"].get("所在地", "").startswith("広島県広島市中区")
]
out = {"type": "FeatureCollection", "features": feats}

with open("hinanbasho-naka-ku.geojson", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
```

匿名化・簡略化は行っていない（施設名・住所はすべて公開情報の指定緊急避難場所であり、個人情報を含まない）。

## 必要な出典表記（クレジット文言）

`about.pdf`（G空間情報センター公開の「『指定緊急避難場所データ』について」）の指示文言をそのまま使用する。
意訳・省略はしない。

```
出典：国土地理院ウェブサイト（http://www.gsi.go.jp/bousaichiri/hinanbasho.html）
加工：「指定緊急避難場所データ」（国土地理院）（http://www.gsi.go.jp/bousaichiri/hinanbasho.html）を
      AIGID が加工して作成
```

上記に加えて、本データセットは広島市中区のみを抽出しているため、次の一文を追記する（PDFの
「編集・加工した場合は別途その旨を記載する」という要求に対応）:

```
上記データから広島市中区のフィーチャのみを抽出して使用。
```

## 動作確認

- インポート方法: Admin UI（ローカル `localhost:3000`）の `/features/import` からGeoJSONアップロード
- 使用したタイルセットID/名: `ca7b5ae6-10f9-4ecf-b27b-3aa3f7992cb8` / `hiroshima-naka-hinanbasho`
- 結果: 87件すべてをインポートでき、MapLibreプレビューで広島市中区の範囲に描画されることを確認

MCPでは単一の完全一致フィルタを利用できます。複合式はHTTP 400で拒否されます。
