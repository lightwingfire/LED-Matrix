[CmdletBinding()]
param(
    [switch]$BuildOnly,
    [switch]$Inspect,
    [string]$RemoteDir,
    [int]$WebPort = 5000
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonCommand = $null
foreach ($relativePath in @('venv/Scripts/python.exe', '.venv/Scripts/python.exe')) {
    $candidate = Join-Path $projectRoot $relativePath
    if (Test-Path -LiteralPath $candidate) {
        $pythonCommand = $candidate
        break
    }
}
if (-not $pythonCommand) {
    $pythonCommand = (Get-Command python -ErrorAction Stop).Source
}

$deployArguments = @((Join-Path $projectRoot 'scripts/deploy_board.py'), '--web-port', "$WebPort")
if ($BuildOnly) { $deployArguments += '--build-only' }
if ($Inspect) { $deployArguments += '--inspect' }
if ($RemoteDir) { $deployArguments += @('--remote-dir', $RemoteDir) }

Push-Location $projectRoot
try {
    & $pythonCommand @deployArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Build/deployment failed. See the status above.'
    }
}
finally {
    Pop-Location
}
