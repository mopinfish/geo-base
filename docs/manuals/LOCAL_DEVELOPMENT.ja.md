# ローカル開発

`docker compose -f docker/docker-compose.yml up -d`でPostGISとRedisを起動します。各サービスの`.env.example`を実行時の環境ファイルへコピーしてください。ルートREADMEのコマンドを使い、APIは8000、HTTP transportのMCPは8001、管理画面は3000番ポートで起動します。

DBテストには専用の`geo_base_test`だけを使用します。ローカルのストレージ・認証情報をコミットしないでください。
