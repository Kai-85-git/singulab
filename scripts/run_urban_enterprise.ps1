$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = "d:\Projects\IRIS-company\departments\r_and_d\singulab"
Set-Location $root

$summaryFile = "$root\output\prod_runs_summary.log"
$t0 = Get-Date
"[start] prod_urban_enterprise (single) at $($t0.ToString('s'))" | Tee-Object -FilePath $summaryFile -Append
& "$root\.venv\Scripts\python.exe" -m src.main `
    --config "config/scenario_prod_urban_enterprise.yaml" `
    --output-dir "output/prod_urban_enterprise" *> "$root\output\prod_urban_enterprise_stdout.log"
$elapsed = (Get-Date) - $t0
"[done]  prod_urban_enterprise elapsed=$($elapsed.ToString('hh\:mm\:ss')) exit=$LASTEXITCODE" | Tee-Object -FilePath $summaryFile -Append
