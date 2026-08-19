# Behavioral smoke test for scripts/windows/hermes.cmd.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$wrapper = Join-Path $repoRoot 'scripts\windows\hermes.cmd'
$sandbox = Join-Path ([System.IO.Path]::GetTempPath()) ("hermes-cli-wrapper-test-" + [guid]::NewGuid().ToString('N'))
$fakePython = Join-Path $sandbox 'python.cmd'
$capture = Join-Path $sandbox 'args.txt'

try {
    New-Item -ItemType Directory -Path $sandbox | Out-Null
    Set-Content -LiteralPath $fakePython -Encoding Ascii -Value @(
        '@echo off',
        ('echo %* > "' + $capture + '"'),
        'exit /b 23'
    )

    $env:HERMES_CLI_PYTHON = $fakePython
    & $wrapper status --json
    $exitCode = $LASTEXITCODE
    $argsSeen = (Get-Content -LiteralPath $capture -Raw).Trim()

    if ($exitCode -ne 23) {
        throw "wrapper did not preserve child exit code (expected 23, got $exitCode)"
    }
    if ($argsSeen -ne '-m hermes_cli.main status --json') {
        throw "wrapper arguments were '$argsSeen'"
    }

    Remove-Item Env:HERMES_CLI_PYTHON -ErrorAction SilentlyContinue
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $wrapper status 2>$null | Out-Null
    $ErrorActionPreference = $previousErrorAction
    if ($LASTEXITCODE -ne 127) {
        throw "missing-runtime path must exit 127 (got $LASTEXITCODE)"
    }

    Write-Host 'Windows CLI wrapper smoke test passed.'
} finally {
    Remove-Item Env:HERMES_CLI_PYTHON -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $sandbox) {
        Remove-Item -LiteralPath $sandbox -Recurse -Force
    }
}
