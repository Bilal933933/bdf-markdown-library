# Requires GEMINI_KEYS (comma-separated) to be set in your shell. Never hardcode keys here.
if (-not $env:GEMINI_KEYS) { throw "GEMINI_KEYS is not set in this shell." }
$env:GEMINI_MODEL = "gemini-3.1-flash-lite"
$env:GEMINI_FALLBACK = "gemini-3.1-flash-lite,gemini-2.5-flash-lite,gemini-2.5-flash"
Set-Location "E:\AI-Content\_ocr"
node gemini-ocr.mjs $args[0] $args[1] $args[2] $args[3]
