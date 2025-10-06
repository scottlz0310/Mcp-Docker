<#
.SYNOPSIS
    GitHub Release Watcher - 自動インストーラー

.DESCRIPTION
    GitHub Release WatcherのWindows Toast通知機能を自動セットアップします。
    - BurntToastモジュールのインストール
    - タスクスケジューラへの登録
    - サービスの起動

.EXAMPLE
    .\Install.ps1

.NOTES
    Author: GitHub Release Watcher
    Requires: PowerShell 5.1+
#>

[CmdletBinding()]
param()

# エラーアクションプリファレンス
$ErrorActionPreference = "Stop"

# アスキーアートバナー
function Show-Banner {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  GitHub Release Watcher Installer     ║" -ForegroundColor Cyan
    Write-Host "║  Windows Toast Notification Setup     ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# ステップ表示
function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "▶ $Message" -ForegroundColor Yellow
}

# 成功メッセージ
function Write-Success {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

# エラーメッセージ
function Write-Error {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
}

# インフォメーション
function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  $Message" -ForegroundColor Cyan
}

# PowerShellバージョンチェック
function Test-PowerShellVersion {
    Write-Step "Checking PowerShell version..."

    $version = $PSVersionTable.PSVersion
    if ($version.Major -lt 5) {
        Write-Error "PowerShell 5.1 or later is required (current: $version)"
        exit 1
    }

    Write-Success "PowerShell version: $version"
}

# BurntToastモジュールのインストール
function Install-BurntToastModule {
    Write-Step "Installing BurntToast module..."

    if (Get-Module -ListAvailable -Name BurntToast) {
        Write-Success "BurntToast module is already installed"
        return
    }

    try {
        Write-Info "Downloading and installing BurntToast..."
        Install-Module -Name BurntToast -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck
        Write-Success "BurntToast module installed successfully"
    }
    catch {
        Write-Error "Failed to install BurntToast module: $_"
        Write-Host ""
        Write-Host "Please install manually:" -ForegroundColor Yellow
        Write-Host "  Install-Module -Name BurntToast -Scope CurrentUser" -ForegroundColor Cyan
        exit 1
    }
}

# 通知ディレクトリの作成
function New-NotificationDirectory {
    Write-Step "Creating notification directory..."

    $notificationPath = "$env:USERPROFILE\.github-release-watcher\notifications"

    if (Test-Path $notificationPath) {
        Write-Success "Notification directory already exists: $notificationPath"
        return
    }

    try {
        New-Item -ItemType Directory -Path $notificationPath -Force | Out-Null
        Write-Success "Notification directory created: $notificationPath"
    }
    catch {
        Write-Error "Failed to create notification directory: $_"
        exit 1
    }
}

# タスクスケジューラへの登録
function Register-WatcherTask {
    Write-Step "Registering task to Task Scheduler..."

    $registerScript = "$PSScriptRoot\Register-TaskScheduler.ps1"

    if (-not (Test-Path $registerScript)) {
        Write-Error "Register-TaskScheduler.ps1 not found at: $registerScript"
        exit 1
    }

    try {
        & $registerScript
        Write-Success "Task registered successfully"
    }
    catch {
        Write-Error "Failed to register task: $_"
        exit 1
    }
}

# サービスの起動
function Start-WatcherService {
    Write-Step "Starting GitHub Release Watcher service..."

    try {
        Start-ScheduledTask -TaskName "GitHubReleaseWatcher"
        Start-Sleep -Seconds 2
        Write-Success "Service started successfully"
    }
    catch {
        Write-Error "Failed to start service: $_"
        Write-Info "You can start it manually later:"
        Write-Info "  Start-ScheduledTask -TaskName 'GitHubReleaseWatcher'"
    }
}

# インストール完了メッセージ
function Show-CompletionMessage {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║     Installation Complete! 🎉         ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "GitHub Release Watcher is now running in the background." -ForegroundColor Cyan
    Write-Host "You will receive Windows Toast notifications for new releases." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Configuration:" -ForegroundColor Yellow
    Write-Host "  Notification Path: $env:USERPROFILE\.github-release-watcher\notifications" -ForegroundColor White
    Write-Host "  Log File: $env:USERPROFILE\.github-release-watcher\watcher.log" -ForegroundColor White
    Write-Host "  Task Name: GitHubReleaseWatcher" -ForegroundColor White
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Yellow
    Write-Host "  Check status:    Get-ScheduledTask -TaskName 'GitHubReleaseWatcher'" -ForegroundColor Cyan
    Write-Host "  Stop service:    Stop-ScheduledTask -TaskName 'GitHubReleaseWatcher'" -ForegroundColor Cyan
    Write-Host "  Start service:   Start-ScheduledTask -TaskName 'GitHubReleaseWatcher'" -ForegroundColor Cyan
    Write-Host "  Uninstall:       .\Register-TaskScheduler.ps1 -Unregister" -ForegroundColor Cyan
    Write-Host ""
}

# メイン処理
function Main {
    Show-Banner

    # インストール手順を実行
    Test-PowerShellVersion
    Install-BurntToastModule
    New-NotificationDirectory
    Register-WatcherTask
    Start-WatcherService

    # 完了メッセージ
    Show-CompletionMessage
}

# スクリプト実行
try {
    Main
}
catch {
    Write-Host ""
    Write-Error "Installation failed: $_"
    exit 1
}
