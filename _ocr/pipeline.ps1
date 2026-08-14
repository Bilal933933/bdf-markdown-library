$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
# GEMINI_KEYS يُمرر عبر البيئة (لا يُكتب في المستودع)
if (-not $env:GEMINI_KEYS) { Write-Error "GEMINI_KEYS غير مضبوط — مرّره عبر البيئة"; exit 1 }
$env:GEMINI_MODEL = "gemini-3.1-flash-lite"
$env:GEMINI_FALLBACK = "gemini-3.1-flash-lite-preview,gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-flash-latest,gemini-3.6-flash,gemini-omni-flash-preview,gemini-3.7-flash,gemini-pro-latest"
$LOG = "E:\AI-Content\_ocr\pipeline.log"
New-Item -ItemType File -Path $LOG -Force | Out-Null
Set-Content -Path $LOG -Value "" -Encoding UTF8
function Log($m){ Add-Content -Path $LOG -Value ("[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $m) -Encoding UTF8 }

function Run-Ocr($pdf, $out, $total, $tag) {
  $done = $false
  for ($i=0; $i -lt 100 -and -not $done; $i++) {
    Log ("${tag}: round " + ($i + 1) + " - starting node")
    & node "E:\AI-Content\_ocr\gemini-ocr.mjs" $pdf $out 1 $total *>> $LOG
    $prog = "$out\progress.json"
    if (Test-Path $prog) {
      $j = Get-Content $prog -Raw | ConvertFrom-Json
      $last = [int]$j.lastPage
      Log ("${tag}: last page = " + $last + " / " + $total)
      if ($last -ge $total) { $done = $true; break }
    }
    if (-not $done) { Log ("${tag}: incomplete, retry in 30s"); Start-Sleep -Seconds 30 }
  }
  if (-not $done) { Log ("WARN: " + $tag + " not complete after 100 rounds") }
}

Run-Ocr "E:\AI-Content\_ocr\marker_in\balagha\balagha.pdf" "E:\AI-Content\_ocr\marker_out\balagha_full" 528 "balagha"
Run-Ocr "E:\AI-Content\_ocr\marker_in\sarf\sarf.pdf" "E:\AI-Content\_ocr\marker_out\sarf_full" 617 "sarf"

Log "rebuilding parts..."
& node "E:\AI-Content\_ocr\rebuild-parts.mjs" "E:\AI-Content\_ocr\marker_out\balagha_full" "E:\AI-Content\_ocr\marker_out\balagha_rebuilt" 528 *>> $LOG
& node "E:\AI-Content\_ocr\rebuild-parts.mjs" "E:\AI-Content\_ocr\marker_out\sarf_full" "E:\AI-Content\_ocr\marker_out\sarf_rebuilt" 617 *>> $LOG
Log "pipeline DONE"