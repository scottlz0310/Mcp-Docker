インストール
============

前提条件
--------

* Docker >= 20.10
* Docker Compose >= 2.0
* Python >= 3.13
* uv (Python package manager)

セットアップ
------------

1. リポジトリのクローン::

    git clone https://github.com/scottlz0310/mcp-docker.git
    cd mcp-docker

2. 初期設定の実行::

    ./scripts/setup.sh

3. 環境変数の設定::

    echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"' >> ~/.bashrc
    source ~/.bashrc

4. イメージのビルド::

    make build

開発環境セットアップ
--------------------

開発依存関係のインストール::

    uv sync --group dev --group docs

Pre-commitフックの設定::

    pre-commit install
