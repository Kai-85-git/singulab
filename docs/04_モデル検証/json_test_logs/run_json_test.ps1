$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$logDir = $PSScriptRoot
$outFile = Join-Path $logDir "results.jsonl"
if (Test-Path $outFile) { Remove-Item $outFile }

$systemMsg = [System.IO.File]::ReadAllText((Join-Path $logDir "prompt_system.txt"), [System.Text.Encoding]::UTF8).Trim()
$userPromptBase = [System.IO.File]::ReadAllText((Join-Path $logDir "prompt_user.txt"), [System.Text.Encoding]::UTF8).Trim()

$models = @(
    @{ name = "huihui_ai/qwen3-abliterated:4b"; needsNoThink = $true },
    @{ name = "huihui_ai/llama3.2-abliterate:3b"; needsNoThink = $false },
    @{ name = "huihui_ai/dolphin3-abliterated:8b-llama3.1-q4_K_M"; needsNoThink = $false }
)

$trials = 3

foreach ($m in $models) {
    Write-Host "=========================================="
    Write-Host "Model: $($m.name)"
    Write-Host "=========================================="

    for ($i = 1; $i -le $trials; $i++) {
        $effectiveUserPrompt = $userPromptBase
        if ($m.needsNoThink) {
            $effectiveUserPrompt += "`n/no_think"
        }

        $body = @{
            model = $m.name
            messages = @(
                @{ role = "system"; content = $systemMsg },
                @{ role = "user"; content = $effectiveUserPrompt }
            )
            stream = $false
            options = @{
                temperature = 0.7
                num_predict = 1024
                num_ctx = 4096
            }
        } | ConvertTo-Json -Compress -Depth 10

        $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $r = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $bodyBytes -ContentType "application/json; charset=utf-8" -TimeoutSec 600
            $sw.Stop()
            $thinking = if ($r.message.thinking) { $r.message.thinking } else { "" }
            $content = $r.message.content
            $tokpersec = if ($r.eval_duration -gt 0) { [math]::Round($r.eval_count * 1e9 / $r.eval_duration, 2) } else { 0 }

            $record = @{
                model = $m.name
                trial = $i
                elapsed_ms = $sw.ElapsedMilliseconds
                eval_count = $r.eval_count
                tokens_per_sec = $tokpersec
                thinking_len = $thinking.Length
                content_len = $content.Length
                content = $content
                thinking_preview = if ($thinking.Length -gt 200) { $thinking.Substring(0, 200) + "..." } else { $thinking }
            } | ConvertTo-Json -Compress -Depth 10

            [System.IO.File]::AppendAllText($outFile, $record + "`n", [System.Text.Encoding]::UTF8)

            Write-Host ("  Trial {0} : eval={1} tok, {2} tok/s, content_len={3}" -f $i, $r.eval_count, $tokpersec, $content.Length)
        } catch {
            $sw.Stop()
            Write-Host "  Trial $i ERROR: $_"
            $record = @{
                model = $m.name
                trial = $i
                error = $_.ToString()
            } | ConvertTo-Json -Compress -Depth 10
            [System.IO.File]::AppendAllText($outFile, $record + "`n", [System.Text.Encoding]::UTF8)
        }
    }
}

Write-Host "=========================================="
Write-Host "Done. results.jsonl written to $outFile"
