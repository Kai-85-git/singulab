# VOICEVOX Zundamon TTS for Claude Code Stop hook
$ErrorActionPreference = 'SilentlyContinue'
try {
    $text = '作業完了しました'
    $speaker = 3  # ずんだもん (ノーマル)
    $base = 'http://localhost:50021'
    $encodedText = [uri]::EscapeDataString($text)
    $query = Invoke-RestMethod -Method POST -Uri "$base/audio_query?speaker=$speaker&text=$encodedText" -TimeoutSec 5
    $body = $query | ConvertTo-Json -Depth 100 -Compress
    $wav = Join-Path $env:TEMP 'claude-stop-tts.wav'
    Invoke-WebRequest -Method POST -Uri "$base/synthesis?speaker=$speaker" -Body $body -ContentType 'application/json' -OutFile $wav -TimeoutSec 30 | Out-Null
    (New-Object Media.SoundPlayer $wav).PlaySync()
} catch {
    # VOICEVOX engine not running or error — fail silently so Claude is not disturbed
}
