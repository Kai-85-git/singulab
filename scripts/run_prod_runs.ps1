$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = "d:\Projects\IRIS-company\departments\r_and_d\singulab"
Set-Location $root

$summaryFile = "$root\output\prod_runs_summary.log"
"=== Production runs started: $((Get-Date).ToString('s')) ===" | Out-File -FilePath $summaryFile -Encoding utf8

$scenarios = @(
    @{name="prod_local_startup"; yaml="config/scenario_prod_local_startup.yaml"},
    @{name="prod_urban_startup"; yaml="config/scenario_prod_urban_startup.yaml"},
    @{name="prod_local_enterprise"; yaml="config/scenario_prod_local_enterprise.yaml"},
    @{name="prod_urban_enterprise"; yaml="config/scenario_prod_urban_enterprise.yaml"}
)

foreach ($s in $scenarios) {
    $t0 = Get-Date
    "[start] $($s.name) at $($t0.ToString('s'))" | Tee-Object -FilePath $summaryFile -Append
    & "$root\.venv\Scripts\python.exe" -m src.main `
        --config $s.yaml `
        --output-dir "output/$($s.name)" *> "$root\output\$($s.name)_stdout.log"
    $elapsed = (Get-Date) - $t0
    "[done]  $($s.name) elapsed=$($elapsed.ToString('hh\:mm\:ss')) exit=$LASTEXITCODE" | Tee-Object -FilePath $summaryFile -Append
}

"=== Production runs finished: $((Get-Date).ToString('s')) ===" | Tee-Object -FilePath $summaryFile -Append
