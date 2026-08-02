$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Game environment not found. Expected: $python"
}

$env:PYTHONUTF8 = "1"
$env:OPENAI_BASE_URL = "https://gateway.theemailgame.com"

$secureKey = Read-Host "Paste your issued Email Game key (input is hidden)" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    Remove-Variable secureKey, keyPointer -ErrorAction SilentlyContinue
}

& $python "scripts\submit_code.py" `
    "--name" "chaim_hayim_lusthaus" `
    "--server" "https://play.theemailgame.com"

exit $LASTEXITCODE
