#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.0' }
<#
.SYNOPSIS
    scripts/lib/setup-tls-functions.ps1 の単体テスト（#204）。

.DESCRIPTION
    mkcert / winget / 証明書ストアなどの環境依存処理は setup-tls.ps1 本体に残されており、
    ここではパス引数のみで動作する純粋なロジックを $TestDrive 上で検証する。
#>

BeforeAll {
    . (Join-Path -Path $PSScriptRoot -ChildPath '../../scripts/lib/setup-tls-functions.ps1')
    $script:setupTlsScript = Get-Content -Raw -Path (Join-Path -Path $PSScriptRoot -ChildPath '../../scripts/setup-tls.ps1')
}

Describe 'setup-tls.ps1 の mkcert 実行コンテキスト' {
    It 'CA を現在のユーザーとして直接生成・信頼登録する' {
        $setupTlsScript | Should -Match '(?m)^\s*& \$mkcert -install\s*$'
    }

    It 'mkcert を別ユーザーとして昇格実行しない' {
        $setupTlsScript | Should -Not -Match '(?i)Start-Process.*-Verb\s+RunAs'
    }

    It 'Java の証明書ストアへ登録しない' {
        $setupTlsScript | Should -Match '\$env:TRUST_STORES = ''system'''
    }
}

Describe 'Set-EnvValue' {
    BeforeEach {
        $script:envFile = Join-Path $TestDrive '.env'
        Write-EnvFile -Path $envFile -Lines @(
            '# comment',
            'MCP_GATEWAY_PORT=8080',
            'LOG_LEVEL=info'
        )
    }

    It '既存キーの値を置換する' {
        Set-EnvValue -Path $envFile -Key 'MCP_GATEWAY_PORT' -Value '9443'

        Get-EnvValue -Path $envFile -Key 'MCP_GATEWAY_PORT' | Should -Be '9443'
    }

    It '他の行は変更しない' {
        Set-EnvValue -Path $envFile -Key 'MCP_GATEWAY_PORT' -Value '9443'

        $lines = Get-Content -Path $envFile
        $lines[0] | Should -Be '# comment'
        $lines[2] | Should -Be 'LOG_LEVEL=info'
    }

    It '存在しないキーは末尾に追記する' {
        Set-EnvValue -Path $envFile -Key 'NODE_EXTRA_CA_CERTS' -Value 'C:/Users/dev/rootCA.pem'

        $lines = Get-Content -Path $envFile
        $lines[-1] | Should -Be 'NODE_EXTRA_CA_CERTS=C:/Users/dev/rootCA.pem'
        $lines.Count | Should -Be 4
    }

    It '値に = を含んでも分割しない' {
        Set-EnvValue -Path $envFile -Key 'EXTRA' -Value 'a=b=c'

        Get-EnvValue -Path $envFile -Key 'EXTRA' | Should -Be 'a=b=c'
    }

    It 'BOM なし UTF-8 で書き込む' {
        Set-EnvValue -Path $envFile -Key 'MCP_GATEWAY_PORT' -Value '9443'

        $bytes = [System.IO.File]::ReadAllBytes($envFile)
        $bytes.Length | Should -BeGreaterThan 3
        @($bytes[0], $bytes[1], $bytes[2]) | Should -Not -Be @(0xEF, 0xBB, 0xBF)
    }

    It 'BOM 付きで書かれた既存ファイルも BOM なしに正規化する' {
        [System.IO.File]::WriteAllLines(
            $envFile,
            [string[]]@('MCP_GATEWAY_PORT=8080'),
            [System.Text.UTF8Encoding]::new($true)
        )

        Set-EnvValue -Path $envFile -Key 'MCP_GATEWAY_PORT' -Value '9443'

        $bytes = [System.IO.File]::ReadAllBytes($envFile)
        @($bytes[0], $bytes[1], $bytes[2]) | Should -Not -Be @(0xEF, 0xBB, 0xBF)
        Get-EnvValue -Path $envFile -Key 'MCP_GATEWAY_PORT' | Should -Be '9443'
    }
}

Describe 'Get-EnvValue' {
    BeforeEach {
        $script:envFile = Join-Path $TestDrive '.env'
    }

    It 'ファイルが存在しなければ $null を返す' {
        Get-EnvValue -Path (Join-Path $TestDrive 'missing.env') -Key 'ANY' | Should -BeNullOrEmpty
    }

    It '<name>' -TestCases @(
        @{ name = 'キーが存在すれば値を返す'
           lines = @('MCP_GATEWAY_PORT=8080'); key = 'MCP_GATEWAY_PORT'; expected = '8080' }
        @{ name = 'キーが存在しなければ $null を返す'
           lines = @('MCP_GATEWAY_PORT=8080'); key = 'MISSING'; expected = $null }
        @{ name = '同一キーが複数あれば最後の値を返す'
           lines = @('KEY=first', 'KEY=last'); key = 'KEY'; expected = 'last' }
        @{ name = '値の前後の空白を取り除く'
           lines = @('KEY=  padded  '); key = 'KEY'; expected = 'padded' }
        @{ name = '行頭に空白があってもキーに一致する'
           lines = @('  KEY=indented'); key = 'KEY'; expected = 'indented' }
        @{ name = 'コメント行のキー風文字列には一致しない'
           lines = @('# KEY=commented'); key = 'KEY'; expected = $null }
    ) {
        param($lines, $key, $expected)
        Write-EnvFile -Path $envFile -Lines $lines

        Get-EnvValue -Path $envFile -Key $key | Should -Be $expected
    }
}

Describe 'Get-NodeExtraCaCertsAction' {
    It '<name>' -TestCases @(
        @{ name = '未設定なら set'
           current = $null; desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'set' }
        @{ name = '空文字列なら set'
           current = ''; desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'set' }
        @{ name = '空白のみなら set'
           current = '   '; desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'set' }
        @{ name = '同一パスなら noop'
           current = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'
           desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'noop' }
        @{ name = 'バックスラッシュ区切りでも同一パスなら noop'
           current = 'C:\Users\dev\AppData\Local\mkcert\rootCA.pem'
           desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'noop' }
        @{ name = '大文字小文字の差だけなら noop'
           current = 'c:/users/dev/appdata/local/mkcert/rootca.pem'
           desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'noop' }
        @{ name = '前後の空白は無視して比較する'
           current = ' C:/Users/dev/AppData/Local/mkcert/rootCA.pem '
           desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'noop' }
        @{ name = '別の値が設定済みなら conflict（上書きしない）'
           current = 'C:/corp/proxy-ca.pem'
           desired = 'C:/Users/dev/AppData/Local/mkcert/rootCA.pem'; expected = 'conflict' }
    ) {
        param($current, $desired, $expected)
        Get-NodeExtraCaCertsAction -CurrentValue $current -DesiredValue $desired | Should -Be $expected
    }
}

Describe 'Get-CertReuseState' {
    BeforeEach {
        $script:certFile = Join-Path $TestDrive 'localhost.pem'
        $script:keyFile = Join-Path $TestDrive 'localhost-key.pem'
        $script:fpFile = Join-Path $TestDrive '.ca-fingerprint'
        Set-Content -Path $certFile -Value 'cert'
        Set-Content -Path $keyFile -Value 'key'
        Set-Content -Path $fpFile -Value 'ABCDEF0123456789'
    }

    It 'fingerprint が一致すれば reusable' {
        Get-CertReuseState -CertFile $certFile -KeyFile $keyFile -FingerprintFile $fpFile -CaFingerprint 'ABCDEF0123456789' |
            Should -Be 'reusable'
    }

    It '記録に末尾改行や空白があっても一致と判定する' {
        [System.IO.File]::WriteAllText($fpFile, "ABCDEF0123456789`n")

        Get-CertReuseState -CertFile $certFile -KeyFile $keyFile -FingerprintFile $fpFile -CaFingerprint 'ABCDEF0123456789' |
            Should -Be 'reusable'
    }

    It '<name>' -TestCases @(
        @{ name = 'fingerprint が不一致なら ca-changed（CA 再生成後の旧証明書再利用を防ぐ）'
           fpContent = 'OUTDATED'; expected = 'ca-changed' }
        @{ name = 'fingerprint 記録が空なら ca-changed'
           fpContent = ''; expected = 'ca-changed' }
    ) {
        param($fpContent, $expected)
        Set-Content -Path $fpFile -Value $fpContent

        Get-CertReuseState -CertFile $certFile -KeyFile $keyFile -FingerprintFile $fpFile -CaFingerprint 'ABCDEF0123456789' |
            Should -Be $expected
    }

    It '<name>' -TestCases @(
        @{ name = '証明書がなければ missing'; remove = 'localhost.pem' }
        @{ name = '秘密鍵がなければ missing'; remove = 'localhost-key.pem' }
        @{ name = 'fingerprint 記録がなければ missing'; remove = '.ca-fingerprint' }
    ) {
        param($remove)
        Remove-Item -Path (Join-Path $TestDrive $remove)

        Get-CertReuseState -CertFile $certFile -KeyFile $keyFile -FingerprintFile $fpFile -CaFingerprint 'ABCDEF0123456789' |
            Should -Be 'missing'
    }
}
