トラブルシューティング
======================

よくある問題と解決方法をまとめています。

権限エラー
----------

Docker実行時の権限問題::

    ERROR: Permission denied

解決方法::

    # ユーザーをdockerグループに追加
    sudo usermod -aG docker $USER
    # セッションを再開
    newgrp docker

バージョン不整合
----------------

pyproject.tomlとmain.pyのバージョンが異なる::

    ⚠️  Version mismatch between pyproject.toml and main.py!

解決方法::

    make version-sync

GitHub API制限
--------------

GitHub APIレート制限に達した場合::

    HTTP 403: API rate limit exceeded

解決方法:

1. Personal Access Tokenを設定::

    export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"

2. トークンの権限を確認

Docker ビルド失敗
-----------------

イメージビルド時のエラー::

    ERROR: failed to solve

解決方法::

    # キャッシュをクリア
    docker system prune -a

    # 再ビルド
    make clean && make build

テスト失敗
----------

セキュリティテストの失敗::

    Container runs as non-root user: FAILED

これは正常な動作です。セキュリティ強化により、
非rootユーザーでの実行が強制されています。

ログ確認
--------

サービスログの確認::

    make logs

    # または
    docker compose logs -f [service-name]
