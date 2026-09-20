$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
$env:GEMINI_MODEL = "gemini-3.1-flash-lite"
$pdf = $args[0]
$outDir = $args[1]
$start = $args[2]
$end = $args[3]
$log = $args[4]
$noResume = if ($args[5] -eq "1") { $env:NO_RESUME = "1" } else { Remove-Item Env:NO_RESUME -ErrorAction SilentlyContinue }
Set-Location "E:\AI-Content\_ocr"
$proc = Start-Process -FilePath "node" -ArgumentList "gemini-ocr.mjs", $pdf, $outDir, $start, $end -NoNewWindow -PassThru -RedirectStandardOutput $log
Write-Output "PID: $($proc.Id)"
Write-Output "Log: $log"