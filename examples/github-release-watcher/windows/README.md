# GitHub Release Watcher - Windows Toast通知

WSL環境からWindowsホストへToast通知を送信する機能です。

## アーキテクチャ

```
┌─────────────────────────────────────┐
│ WSL (Docker Container)              │
│ ┌─────────────────────────────────┐ │
│ │ GitHub Release Watcher          │ │
│ │  - 新リリース検知               │ │
│ │  - Windows Bridge通知チャネル   │ │      ┌──────────────────────────┐
│ │  - JSON書き込み                 │ │      │ Windows Host             │
│ │    → /mnt/c/Users/.../          │ ├─────→│ ┌──────────────────────┐ │
│ └─────────────────────────────────┘ │      │ │ PowerShell Watcher   │ │
└─────────────────────────────────────┘      │ │  - FileSystemWatcher │ │
                                              │ │  - Toast通知表示     │ │
                                              │ └──────────────────────┘ │
                                              │ (タスクスケジューラ常駐) │
                                              └──────────────────────────┘
```

## 自動インストール（推奨）

PowerShellで以下のコマンドを実行してください：

```powershell
# Windowsターミナル（PowerShell）で実行
cd \\wsl$\Ubuntu\home\<username>\workspace\Mcp-Docker\examples\github-release-watcher\windows
.\Install.ps1
```

これにより以下が自動的に実行されます：
1. ✅ BurntToastモジュールのインストール
2. ✅ 通知ディレクトリの作成
3. ✅ タスクスケジューラへの登録
4. ✅ サービスの起動

## 手動インストール

### 1. BurntToastモジュールのインストール

```powershell
Install-Module -Name BurntToast -Scope CurrentUser
```

### 2. 通知ウォッチャーの起動

```powershell
# フォアグラウンドで起動（テスト用）
.\Watch-GitHubReleases.ps1

# バックグラウンドで起動（タスクスケジューラ）
.\Register-TaskScheduler.ps1
```

## WSL側の設定

`config.toml` を編集してWindows Bridge通知を有効化：

```toml
[notifications]
enabled = true
channels = ["windows_bridge"]

[notifications.windows_bridge]
enabled = true
# パスは自動検出されます（オプション）
# bridge_path = "/mnt/c/Users/YourUsername/.github-release-watcher/notifications"
```

## 動作確認

### テスト通知の送信

WSL側で以下のコマンドを実行：

```bash
# テスト用通知ファイルを作成
mkdir -p /mnt/c/Users/$USER/.github-release-watcher/notifications
cat > /mnt/c/Users/$USER/.github-release-watcher/notifications/notification_test.json << 'EOF'
{
  "timestamp": "2025-10-05T12:00:00Z",
  "title": "New Release: microsoft/WSL 2.6.1",
  "body": "A new release 2.6.1 is available for microsoft/WSL",
  "owner": "microsoft",
  "repo": "WSL",
  "version": "2.6.1",
  "release_name": "2.6.1",
  "url": "https://github.com/microsoft/WSL/releases/tag/2.6.1",
  "published_at": "2025-08-07T01:00:00Z"
}
EOF
```

数秒後にWindows Toast通知が表示されます。

## 管理コマンド

### サービスの状態確認

```powershell
Get-ScheduledTask -TaskName "GitHubReleaseWatcher"
```

### サービスの停止

```powershell
Stop-ScheduledTask -TaskName "GitHubReleaseWatcher"
```

### サービスの開始

```powershell
Start-ScheduledTask -TaskName "GitHubReleaseWatcher"
```

### アンインストール

```powershell
.\Register-TaskScheduler.ps1 -Unregister
```

## ログ確認

ログファイル: `C:\Users\<username>\.github-release-watcher\watcher.log`

```powershell
Get-Content $env:USERPROFILE\.github-release-watcher\watcher.log -Tail 20
```

## トラブルシューティング

### Toast通知が表示されない

1. **BurntToastモジュールの確認**
   ```powershell
   Get-Module -ListAvailable -Name BurntToast
   ```

2. **通知ディレクトリの確認**
   ```powershell
   Test-Path "$env:USERPROFILE\.github-release-watcher\notifications"
   ```

3. **タスクスケジューラの確認**
   ```powershell
   Get-ScheduledTask -TaskName "GitHubReleaseWatcher" | Select-Object State, LastRunTime
   ```

4. **ログの確認**
   ```powershell
   Get-Content $env:USERPROFILE\.github-release-watcher\watcher.log
   ```

### WSL側でパスが見つからない

USERPROFILEが設定されていることを確認：

```bash
echo $USERPROFILE
# 出力: /mnt/c/Users/YourUsername
```

設定されていない場合は `.bashrc` または `.zshrc` に追加：

```bash
export USERPROFILE=$(wslpath "$(cmd.exe /C 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')")
```

## 技術詳細

### 通知フロー

1. WSL: 新リリースを検知
2. WSL: JSON通知ファイルを `/mnt/c/Users/<username>/.github-release-watcher/notifications/` に書き込み
3. Windows: FileSystemWatcherが新規ファイルを検出
4. Windows: JSONを読み込みToast通知を表示
5. Windows: 処理済みファイルを削除

### ファイル形式

```json
{
  "timestamp": "ISO 8601形式",
  "title": "通知タイトル",
  "body": "通知本文",
  "owner": "リポジトリオーナー",
  "repo": "リポジトリ名",
  "version": "バージョン",
  "release_name": "リリース名",
  "url": "GitHubリリースURL",
  "published_at": "公開日時"
}
```

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
