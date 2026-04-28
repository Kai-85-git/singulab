$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$logDir = $PSScriptRoot
$inFile = Join-Path $logDir "results.jsonl"

function Extract-JsonObject {
    param([string]$text)
    if ([string]::IsNullOrEmpty($text)) { return $null }
    $start = $text.IndexOf('{')
    if ($start -lt 0) { return $null }
    $depth = 0
    $inStr = $false
    $esc = $false
    for ($i = $start; $i -lt $text.Length; $i++) {
        $c = $text[$i]
        if ($esc) { $esc = $false; continue }
        if ($c -eq '\' -and $inStr) { $esc = $true; continue }
        if ($c -eq '"') { $inStr = -not $inStr; continue }
        if ($inStr) { continue }
        if ($c -eq '{') { $depth++ }
        elseif ($c -eq '}') {
            $depth--
            if ($depth -eq 0) { return $text.Substring($start, $i - $start + 1) }
        }
    }
    return $null
}

$lines = [System.IO.File]::ReadAllLines($inFile, [System.Text.Encoding]::UTF8)
$summary = @()

foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $rec = $line | ConvertFrom-Json
    $jsonStr = Extract-JsonObject $rec.content
    $parsed = $null
    $parseErr = $null
    if ($jsonStr) {
        try { $parsed = $jsonStr | ConvertFrom-Json } catch { $parseErr = $_.ToString().Substring(0, [Math]::Min(80, $_.ToString().Length)) }
    } else {
        $parseErr = "no JSON object found in content"
    }

    $hasAction = $false; $hasDirection = $false; $hasMemory = $false; $hasReasoning = $false
    $actionValid = $false; $directionValid = $false
    if ($parsed) {
        $hasAction = $parsed.PSObject.Properties.Name -contains "action"
        $hasDirection = $parsed.PSObject.Properties.Name -contains "direction"
        $hasMemory = $parsed.PSObject.Properties.Name -contains "memory"
        $hasReasoning = $parsed.PSObject.Properties.Name -contains "reasoning"
        if ($hasAction) {
            $actionValid = ($parsed.action -eq "move" -or $parsed.action -eq "stay")
        }
        if ($hasDirection) {
            $directionValid = ($null -eq $parsed.direction) -or ($parsed.direction -in @("up","down","left","right"))
        }
    }

    $summary += [PSCustomObject]@{
        model = $rec.model.Split('/')[-1]
        trial = $rec.trial
        elapsed_s = [math]::Round($rec.elapsed_ms / 1000, 1)
        tok_per_s = $rec.tokens_per_sec
        content_len = $rec.content_len
        json_extracted = ($null -ne $jsonStr)
        json_parsed = ($null -ne $parsed)
        has_all_keys = ($hasAction -and $hasDirection -and $hasMemory -and $hasReasoning)
        action_valid = $actionValid
        direction_valid = $directionValid
        action_value = if ($parsed) { $parsed.action } else { "" }
        direction_value = if ($parsed -and $hasDirection) { "$($parsed.direction)" } else { "" }
        parse_err = $parseErr
    }
}

Write-Host "===== Per-trial breakdown ====="
$summary | Format-Table model, trial, elapsed_s, tok_per_s, content_len, json_extracted, json_parsed, has_all_keys, action_valid, direction_valid, action_value, direction_value -AutoSize

Write-Host ""
Write-Host "===== Aggregate by model ====="
$summary | Group-Object model | ForEach-Object {
    $g = $_.Group
    $n = $g.Count
    [PSCustomObject]@{
        model = $_.Name
        trials = $n
        json_parse_rate = "$(($g | Where-Object { $_.json_parsed }).Count)/$n"
        all_keys_rate = "$(($g | Where-Object { $_.has_all_keys }).Count)/$n"
        valid_action_rate = "$(($g | Where-Object { $_.action_valid }).Count)/$n"
        avg_elapsed_s = [math]::Round((($g | Measure-Object elapsed_s -Average).Average), 1)
        avg_tok_s = [math]::Round((($g | Measure-Object tok_per_s -Average).Average), 1)
    }
} | Format-Table -AutoSize

Write-Host ""
Write-Host "===== Sample contents (first 200 chars each) ====="
foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $rec = $line | ConvertFrom-Json
    $name = $rec.model.Split('/')[-1]
    $preview = if ($rec.content.Length -gt 250) { $rec.content.Substring(0, 250) + "..." } else { $rec.content }
    Write-Host ("--- {0} trial {1} ---" -f $name, $rec.trial)
    Write-Host $preview
    Write-Host ""
}
