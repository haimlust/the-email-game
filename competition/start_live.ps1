$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Game environment not found. Expected: $python"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = $PSScriptRoot
$env:EMAIL_GAME_FORCE_IPV4 = "1"
$env:OPENAI_BASE_URL = "https://gateway.theemailgame.com"
$env:OPENAI_MODEL = "gpt-4.1-mini"
$env:EMAIL_GAME_RESOLVER_MODEL = "gpt-4.1"
$env:EMAIL_GAME_LLM_TIMEOUT_SEC = "12"
$env:EMAIL_GAME_ATTACK_MODE = "1"

$secureKey = Read-Host "Paste your issued Email Game key (input is hidden)" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    Remove-Variable secureKey, keyPointer -ErrorAction SilentlyContinue
}

Write-Host "Checking the issued key and gateway..."
& $python "scripts\check_openai_key.py"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "The hosted model gateway is not responding. The live game server may still work."
    Write-Host "This agent can play deterministically without model access."
    Write-Host "It will decline fuzzy authorizations it cannot resolve rather than risk a penalty."
    $decision = Read-Host "Type START to compete in deterministic fallback mode, or press Enter to stop"
    if ($decision -cne "START") {
        throw "Gateway check failed. The live agent was not started."
    }
}

Write-Host "Starting the live agent. Keep this window open."
Write-Host "The watch page should open automatically; watch the walkthrough once."
& $python "scripts\run_custom_agent.py" `
    "chaim_hayim_lusthaus" `
    "--module" "my_agent.py" `
    "--server" "https://play.theemailgame.com" `
    "--model" "gpt-4.1-mini" `
    "--temperature" "0"

exit $LASTEXITCODE
