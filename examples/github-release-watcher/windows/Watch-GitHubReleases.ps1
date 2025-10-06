<#
.SYNOPSIS
    GitHub Release Watcher - Windows Toast通知ウォッチャー

.DESCRIPTION
    WSLからの通知ファイルを監視し、Windows Toast通知を表示します。
    BurntToastモジュールを使用してリッチなToast通知を実現します。

.NOTES
    Author: GitHub Release Watcher
    Requires: PowerShell 5.1+, BurntToast Module
#>

param(
    [Parameter()]
    [string]$NotificationPath = "$env:USERPROFILE\.github-release-watcher\notifications",

    [Parameter()]
    [switch]$InstallModule
)

# エラーアクションプリファレンス
$ErrorActionPreference = "Stop"

# ログ関数
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage

    # ログファイルにも記録
    $logPath = "$env:USERPROFILE\.github-release-watcher\watcher.log"
    Add-Content -Path $logPath -Value $logMessage -ErrorAction SilentlyContinue
}

# BurntToastモジュールのインストール確認
function Ensure-BurntToast {
    if (-not (Get-Module -ListAvailable -Name BurntToast)) {
        Write-Log "BurntToast module not found" "WARN"

        if ($InstallModule) {
            Write-Log "Installing BurntToast module..."
            try {
                Install-Module -Name BurntToast -Scope CurrentUser -Force -AllowClobber
                Write-Log "BurntToast module installed successfully"
            }
            catch {
                Write-Log "Failed to install BurntToast module: $_" "ERROR"
                Write-Host ""
                Write-Host "Please install BurntToast manually:" -ForegroundColor Yellow
                Write-Host "  Install-Module -Name BurntToast -Scope CurrentUser" -ForegroundColor Cyan
                exit 1
            }
        }
        else {
            Write-Host ""
            Write-Host "BurntToast module is required but not installed." -ForegroundColor Yellow
            Write-Host "Run this script with -InstallModule to install it automatically:" -ForegroundColor Yellow
            Write-Host "  .\Watch-GitHubReleases.ps1 -InstallModule" -ForegroundColor Cyan
            Write-Host "Or install it manually:" -ForegroundColor Yellow
            Write-Host "  Install-Module -Name BurntToast -Scope CurrentUser" -ForegroundColor Cyan
            exit 1
        }
    }

    Import-Module BurntToast -ErrorAction Stop
}

# 通知ディレクトリの作成
function Ensure-NotificationDirectory {
    if (-not (Test-Path $NotificationPath)) {
        Write-Log "Creating notification directory: $NotificationPath"
        New-Item -ItemType Directory -Path $NotificationPath -Force | Out-Null
    }
}

# Toast通知を表示
function Show-ReleaseNotification {
    param(
        [Parameter(Mandatory)]
        [hashtable]$NotificationData
    )

    try {
        $title = $NotificationData.title
        $repo = "$($NotificationData.owner)/$($NotificationData.repo)"
        $version = $NotificationData.version
        $url = $NotificationData.url

        # Toast通知のテキスト
        $text1 = New-BTText -Content $title -MaxLines 1
        $text2 = New-BTText -Content $NotificationData.body -MaxLines 2
        $text3 = New-BTText -Content "Version: $version" -MaxLines 1

        # GitHubアイコン（オプション）
        $appLogo = New-BTImage -Source "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" -AppLogoOverride -Crop Circle

        # アクション（GitHubリリースページを開く）
        $button = New-BTButton -Content "View Release" -Arguments $url

        # Toast通知のバインディング
        $binding = New-BTBinding -Children $text1, $text2, $text3 -AppLogoOverride $appLogo
        $visual = New-BTVisual -BindingGeneric $binding
        $actions = New-BTAction -Buttons $button

        # Toast通知のコンテンツ
        $content = New-BTContent -Visual $visual -Actions $actions -Audio (New-BTAudio -Source 'ms-winsoundevent:Notification.Default')

        # Toast通知を表示
        Submit-BTNotification -Content $content

        Write-Log "Toast notification displayed: $title"
    }
    catch {
        Write-Log "Failed to show toast notification: $_" "ERROR"
    }
}

# 通知ファイルを処理
function Process-NotificationFile {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath
    )

    try {
        # JSONファイルを読み込み
        $notificationData = Get-Content -Path $FilePath -Raw | ConvertFrom-Json -AsHashtable

        Write-Log "Processing notification: $($notificationData.title)"

        # Toast通知を表示
        Show-ReleaseNotification -NotificationData $notificationData

        # 処理済みファイルを削除（またはアーカイブ）
        Remove-Item -Path $FilePath -Force
        Write-Log "Notification file processed and removed: $FilePath"
    }
    catch {
        Write-Log "Failed to process notification file: $_" "ERROR"
    }
}

# ファイルシステムウォッチャーの開始
function Start-FileWatcher {
    Write-Log "Starting file watcher on: $NotificationPath"

    # FileSystemWatcherを作成
    $watcher = New-Object System.IO.FileSystemWatcher
    $watcher.Path = $NotificationPath
    $watcher.Filter = "notification_*.json"
    $watcher.EnableRaisingEvents = $true
    $watcher.IncludeSubdirectories = $false

    # イベントハンドラーを登録
    $action = {
        param($source, $e)

        # ファイル作成イベント
        if ($e.ChangeType -eq 'Created') {
            # ファイルが完全に書き込まれるまで少し待機
            Start-Sleep -Milliseconds 100

            # 通知ファイルを処理
            Process-NotificationFile -FilePath $e.FullPath
        }
    }

    # Created イベントを購読
    $created = Register-ObjectEvent -InputObject $watcher -EventName Created -Action $action

    Write-Log "File watcher started successfully"
    Write-Host ""
    Write-Host "Watching for GitHub release notifications..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""

    # 既存の通知ファイルを処理
    Get-ChildItem -Path $NotificationPath -Filter "notification_*.json" | ForEach-Object {
        Process-NotificationFile -FilePath $_.FullName
    }

    # 無限ループ（Ctrl+Cで終了）
    try {
        while ($true) {
            Start-Sleep -Seconds 1
        }
    }
    finally {
        # クリーンアップ
        Unregister-Event -SubscriptionId $created.Id
        $watcher.Dispose()
        Write-Log "File watcher stopped"
    }
}

# メイン処理
function Main {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host " GitHub Release Watcher" -ForegroundColor Cyan
    Write-Host " Windows Toast Notification" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    # BurntToastモジュールの確認
    Ensure-BurntToast

    # 通知ディレクトリの作成
    Ensure-NotificationDirectory

    # ファイルウォッチャーの開始
    Start-FileWatcher
}

# スクリプト実行
Main
