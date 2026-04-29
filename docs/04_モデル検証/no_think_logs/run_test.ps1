$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$logDir = $PSScriptRoot
$outFile = Join-Path $logDir "results.jsonl"
if (Test-Path $outFile) { Remove-Item $outFile }

$prompt = [System.IO.File]::ReadAllText((Join-Path $logDir "prompt.txt"), [System.Text.Encoding]::UTF8).Trim()
$model = "huihui_ai/qwen3-abliterated:4b"

function Invoke-Test {
    param([string]$Label, [hashtable]$Body)
    $bodyJson = $Body | ConvertTo-Json -Compress -Depth 10
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($bodyJson)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $r = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $bytes -ContentType "application/json; charset=utf-8" -TimeoutSec 300
    $sw.Stop()
    $thinking = if ($r.message.thinking) { $r.message.thinking } else { "" }
    $content = $r.message.content
    $tokpersec = if ($r.eval_duration -gt 0) { [math]::Round($r.eval_count * 1e9 / $r.eval_duration, 2) } else { 0 }

    $rec = @{
        label = $Label
        elapsed_ms = $sw.ElapsedMilliseconds
        eval_count = $r.eval_count
        tok_per_s = $tokpersec
        thinking_len = $thinking.Length
        content_len = $content.Length
        content = $content
        thinking_preview = if ($thinking.Length -gt 200) { $thinking.Substring(0, 200) + "..." } else { $thinking }
    } | ConvertTo-Json -Compress -Depth 10
    [System.IO.File]::AppendAllText($outFile, $rec + "`n", [System.Text.Encoding]::UTF8)

    Write-Host ("[{0,-30}] eval={1,5}, tok/s={2,6}, thinking_len={3,5}, content_len={4,5}" -f $Label, $r.eval_count, $tokpersec, $thinking.Length, $content.Length)
}

# ベースライン(thinking ON 既定)
Invoke-Test "A_baseline_thinking_on" @{
    model = $model
    messages = @(@{role="user"; content=$prompt})
    stream = $false
    options = @{temperature=0.5; num_predict=512}
}

# B: /no_think を user 末尾に
Invoke-Test "B_no_think_user_suffix" @{
    model = $model
    messages = @(@{role="user"; content="$prompt`n/no_think"})
    stream = $false
    options = @{temperature=0.5; num_predict=512}
}

# C: /no_think を user 先頭に
Invoke-Test "C_no_think_user_prefix" @{
    model = $model
    messages = @(@{role="user"; content="/no_think`n$prompt"})
    stream = $false
    options = @{temperature=0.5; num_predict=512}
}

# D: /no_think を system に
Invoke-Test "D_no_think_in_system" @{
    model = $model
    messages = @(
        @{role="system"; content="/no_think"},
        @{role="user"; content=$prompt}
    )
    stream = $false
    options = @{temperature=0.5; num_predict=512}
}

# E: think: false パラメータ (Ollama 0.21+ の正式 API)
Invoke-Test "E_think_false_param" @{
    model = $model
    messages = @(@{role="user"; content=$prompt})
    stream = $false
    think = $false
    options = @{temperature=0.5; num_predict=512}
}

Write-Host "==== Done ===="
