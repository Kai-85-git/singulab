# build_pdf.ps1
#
# Build the Singulab submission PDF using Pandoc + XeLaTeX (xeCJK).
#
# Usage:
#   .\build_pdf.ps1                              # full build
#   .\build_pdf.ps1 -Chapters "03,04"            # rebuild specific chapters only
#   .\build_pdf.ps1 -Output "output\v2.pdf"      # custom output path
#   .\build_pdf.ps1 -ResetFromTemplate           # discard build/chapters edits
#
# Requirements:
#   - pandoc (auto-detected; falls back to pypandoc-binary bundled exe)
#   - XeLaTeX (TeX Live 2025+)
#   - xeCJK package (bundled with TeX Live full install)
#   - Japanese fonts: Yu Mincho/Yu Gothic UI (Windows 10/11 default).
#     Noto Sans/Serif JP is preferred but xdvipdfmx may reject the variable
#     font variant from Google Fonts. Yu Gothic is the safe default on Windows.
#   See references/pandoc_setup.md for details.

param(
    [string]$Output = "output\singulab_submission.pdf",
    [string]$Chapters = "",
    [switch]$ResetFromTemplate
)

$ErrorActionPreference = "Stop"
Set-Location "C:\Projects\singulab"

$SkillRoot = ".claude\skills\submission-pdf"
$TemplateDir = Join-Path $SkillRoot "templates"
$BuildDir = "build"
$ChapterBuildDir = Join-Path $BuildDir "chapters"
$MetadataYaml = Join-Path $BuildDir "metadata.yaml"
$HeaderFile = Join-Path $BuildDir "xecjk_header.tex"

# 1. Prepare directories
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $ChapterBuildDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $Output) | Out-Null

# 2. Copy metadata.yaml on first run only (preserve user edits)
if (-not (Test-Path $MetadataYaml)) {
    Copy-Item (Join-Path $TemplateDir "metadata.yaml") $MetadataYaml
    Write-Host "[init] copied metadata.yaml -> $MetadataYaml"
}

# 3. Stage chapter files (template files use kanji names; we keep them on disk)
$RealTemplates = Get-ChildItem -Path $TemplateDir -Filter "*.md" | Sort-Object Name | Select-Object -ExpandProperty Name

foreach ($real in $RealTemplates) {
    $src = Join-Path $TemplateDir $real
    $dst = Join-Path $ChapterBuildDir $real

    if ($ResetFromTemplate -or -not (Test-Path $dst)) {
        Copy-Item $src $dst -Force
        Write-Host "[copy] $real"
    }
}

# 4. -Chapters filter forces re-copy of selected chapters
if ($Chapters -ne "") {
    $targetIds = $Chapters -split "," | ForEach-Object { $_.Trim() }
    foreach ($id in $targetIds) {
        $match = $RealTemplates | Where-Object { $_.StartsWith($id + "_") }
        if ($match) {
            $src = Join-Path $TemplateDir $match
            $dst = Join-Path $ChapterBuildDir $match
            Copy-Item $src $dst -Force
            Write-Host "[regen] chapter $id -> $match"
        } else {
            Write-Warning "no template matches chapter id $id"
        }
    }
}

$ChapterPaths = $RealTemplates | ForEach-Object { Join-Path $ChapterBuildDir $_ }

# 5. Locate pandoc (PATH first, then pypandoc-binary bundle)
$pandocCmd = Get-Command pandoc -ErrorAction SilentlyContinue
if ($pandocCmd) {
    $PandocExe = $pandocCmd.Source
} else {
    $bundled = "$env:APPDATA\Python\Python311\site-packages\pypandoc\files\pandoc.exe"
    if (Test-Path $bundled) {
        $PandocExe = $bundled
        Write-Host "[info] using pypandoc-binary bundled pandoc: $PandocExe"
    } else {
        Write-Error "pandoc not found. See references/pandoc_setup.md."
        exit 1
    }
}

# 6. Pick fonts. Yu Mincho/Yu Gothic UI ship with Windows 10/11 and are
#    handled cleanly by xdvipdfmx. Noto JP would be ideal but the variable-font
#    OTF from Google Fonts trips xdvipdfmx. To switch to Noto JP, install the
#    static (non-variable) variants and edit this block.
$MainFont = "Yu Mincho"
$SansFont = "Yu Gothic UI"
$MonoFont = "Consolas"
$CJKMain  = "Yu Mincho"
$CJKSans  = "Yu Gothic UI"
$CJKMono  = "Yu Gothic UI"
Write-Host "[font] latin: main=$MainFont sans=$SansFont mono=$MonoFont"
Write-Host "[font] cjk  : main=$CJKMain sans=$CJKSans mono=$CJKMono"

# 7. Write the xeCJK header used by --include-in-header
$headerLines = @(
    '\usepackage{xeCJK}',
    "\setCJKmainfont{$CJKMain}",
    "\setCJKsansfont{$CJKSans}",
    "\setCJKmonofont{$CJKMono}",
    '\xeCJKsetup{CJKecglue=}'
)
$headerLines -join "`r`n" | Out-File -FilePath $HeaderFile -Encoding utf8
Write-Host "[header] wrote $HeaderFile"

# 8. Run Pandoc
Write-Host ""
Write-Host "[build] running Pandoc + XeLaTeX..."
Write-Host "  chapters: $($ChapterPaths.Count)"
Write-Host "  output  : $Output"
Write-Host ""

$pandocArgs = @(
    "--from=markdown",
    "--pdf-engine=xelatex",
    "--metadata-file=$MetadataYaml",
    "--toc",
    "--toc-depth=2",
    "--number-sections",
    "-V", "geometry=margin=22mm",
    "-V", "fontsize=11pt",
    "-V", "mainfont=$MainFont",
    "-V", "sansfont=$SansFont",
    "-V", "monofont=$MonoFont",
    "-V", "linkcolor=MidnightBlue",
    "-V", "urlcolor=MidnightBlue",
    "-H", $HeaderFile,
    "-o", $Output
) + $ChapterPaths

& $PandocExe @pandocArgs
$pandocExit = $LASTEXITCODE

if ($pandocExit -eq 0 -and (Test-Path $Output)) {
    Write-Host ""
    Write-Host "[done] PDF built successfully: $Output" -ForegroundColor Green
    $size = (Get-Item $Output).Length / 1KB
    Write-Host ("       size: {0:N1} KB" -f $size)
} else {
    Write-Error "Pandoc build failed (exit code $pandocExit). See references/pandoc_setup.md."
    exit $pandocExit
}
