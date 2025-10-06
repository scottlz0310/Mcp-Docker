<#
.SYNOPSIS
    GitHub Release Watcher - タスクスケジューラ自動登録

.DESCRIPTION
    GitHub Release WatcherのToast通知ウォッチャーをWindowsタスクスケジューラに登録します。
    ユーザーログオン時に自動起動し、バックグラウンドで常駐します。

.NOTES
    Author: GitHub Release Watcher
    Requires: 管理者権限（推奨）
#>

param(
    [Parameter()]
    [string]$TaskName = "GitHubReleaseWatcher",

    [Parameter()]
    [switch]$Unregister
)

# エラーアクションプリファレンス
$ErrorActionPreference = "Stop"

# スクリプトのパスを取得
$scriptPath = "$PSScriptRoot\Watch-GitHubReleases.ps1"

# タスクの削除
if ($Unregister) {
    Write-Host "Unregistering task: $TaskName" -ForegroundColor Yellow

    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Task unregistered successfully: $TaskName" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to unregister task: $_" -ForegroundColor Red
        exit 1
    }

    exit 0
}

# タスクの登録
Write-Host ""
Write-Host "Registering GitHub Release Watcher to Task Scheduler..." -ForegroundColor Cyan
Write-Host ""

# スクリプトの存在確認
if (-not (Test-Path $scriptPath)) {
    Write-Host "Error: Script not found at: $scriptPath" -ForegroundColor Red
    exit 1
}

# タスクアクション（PowerShellスクリプトを実行）
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

# タスクトリガー（ユーザーログオン時）
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# タスク設定
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

# タスクプリンシパル（現在のユーザー）
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# 既存のタスクを削除
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
}
catch {
    # 既存のタスクがない場合は無視
}

# タスクを登録
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "GitHub Release Watcher - Windows Toast Notification Monitor" `
        -Force | Out-Null

    Write-Host "✅ Task registered successfully: $TaskName" -ForegroundColor Green
    Write-Host ""
    Write-Host "The watcher will start automatically when you log in." -ForegroundColor Cyan
    Write-Host "To start it now, run:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To unregister, run:" -ForegroundColor Yellow
    Write-Host "  .\Register-TaskScheduler.ps1 -Unregister" -ForegroundColor Cyan
}
catch {
    Write-Host "❌ Failed to register task: $_" -ForegroundColor Red
    exit 1
}
