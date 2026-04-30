# 100 体本番ラン(粉川氏マシン用)。
# 2 シナリオ(宇宙人 / 無重力)を逐次実行 → 動画 + メトリクス + 集計 CSV を生成。
#
# 想定環境:
#   - Windows 11 + ゲーミング GPU(VRAM ≥ 24GB 推奨、Qwen3 34B Q4_K_M で約 22GB)
#   - Ollama 0.21+ がローカルで起動済み
#   - リポジトリ直下で実行(.venv は事前作成済み)
#
# 詳細手順: docs/05_運用手順/粉川氏向け_100体ラン手順.md

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = $PSScriptRoot | Split-Path -Parent
Set-Location $root

$summaryFile = "$root\output\prod_v2_100agents_summary.log"
"=== 100agents runs started: $((Get-Date).ToString('s')) ===" | Out-File -FilePath $summaryFile -Encoding utf8

$scenarios = @(
    @{name="prod_v2_alien_100"; yaml="config/scenario_alien_100.yaml"},
    @{name="prod_v2_zero_gravity_100"; yaml="config/scenario_zero_gravity_100.yaml"}
)

foreach ($s in $scenarios) {
    $t0 = Get-Date
    "[start] $($s.name) at $($t0.ToString('s'))" | Tee-Object -FilePath $summaryFile -Append
    & "$root\.venv\Scripts\python.exe" -m src.main `
        --config $s.yaml `
        --output-dir "output/$($s.name)" *> "$root\output\$($s.name)_stdout.log"
    $exit = $LASTEXITCODE
    $elapsed = (Get-Date) - $t0
    "[done]  $($s.name) elapsed=$($elapsed.ToString('hh\:mm\:ss')) exit=$exit" | Tee-Object -FilePath $summaryFile -Append

    if ($exit -eq 0) {
        # 動画 + メトリクス
        & "$root\.venv\Scripts\python.exe" -m tools.generate_video "output/$($s.name)" --fps 5 -y *>> "$root\output\$($s.name)_stdout.log"
        & "$root\.venv\Scripts\python.exe" -m tools.analyze_run "output/$($s.name)" *>> "$root\output\$($s.name)_stdout.log"
    }
}

"=== 100agents runs finished: $((Get-Date).ToString('s')) ===" | Tee-Object -FilePath $summaryFile -Append

# 完走後の指標確認(短文化エコー指標)
$env:PYTHONIOENCODING = "utf-8"
& "$root\.venv\Scripts\python.exe" `
    "$root\docs\04_モデル検証\conversation_check\check_conversation.py" `
    prod_v2_alien_100 prod_v2_zero_gravity_100 `
    --out=D_100agents.md
"=== conversation_check に D_100agents.md を出力 ===" | Tee-Object -FilePath $summaryFile -Append
