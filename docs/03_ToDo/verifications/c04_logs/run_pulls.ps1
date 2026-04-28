$ErrorActionPreference = 'Continue'
$start = Get-Date
'=== C-04 sequential pull started: ' + $start.ToString('s') | Out-File -FilePath 'd:\Projects\IRIS-company\departments\r_and_d\singulab\docs\03_ToDo\verifications\c04_logs\summary.log' -Encoding utf8
$models = @(
    'huihui_ai/qwen3-abliterated:4b',
    'huihui_ai/llama3.2-abliterated:3b',
    'huihui_ai/dolphin3-abliterated:8b-llama3.1-q4_K_M'
)
foreach ($m in $models) {
    $safe = $m -replace '[/:]','_'
    $t0 = Get-Date
    ('--- pulling ' + $m + ' at ' + $t0.ToString('s')) | Out-File -FilePath 'd:\Projects\IRIS-company\departments\r_and_d\singulab\docs\03_ToDo\verifications\c04_logs\summary.log' -Append -Encoding utf8
    & ollama pull $m *> "d:\Projects\IRIS-company\departments\r_and_d\singulab\docs\03_ToDo\verifications\c04_logs\$safe.log"
    $elapsed = (Get-Date) - $t0
    ('--- done ' + $m + ' in ' + $elapsed.ToString() + ' (exit ' + $LASTEXITCODE + ')') | Out-File -FilePath 'd:\Projects\IRIS-company\departments\r_and_d\singulab\docs\03_ToDo\verifications\c04_logs\summary.log' -Append -Encoding utf8
}
$total = (Get-Date) - $start
('=== C-04 finished. total ' + $total.ToString()) | Out-File -FilePath 'd:\Projects\IRIS-company\departments\r_and_d\singulab\docs\03_ToDo\verifications\c04_logs\summary.log' -Append -Encoding utf8
ollama list *> "d:\Projects\IRIS-company\departments\r_and_d\singulab\docs\03_ToDo\verifications\c04_logs\final_list.log"
