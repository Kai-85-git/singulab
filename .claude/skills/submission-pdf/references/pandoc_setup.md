# Pandoc + XeLaTeX + 日本語フォント セットアップ (Windows 11)

`build_pdf.ps1` を動かすために、ホスト側に必要な道具のインストール手順。一度入れれば再生成のたびに使い回せる。

> **本リポジトリの実機検証結果(2026-04-25)**
> - Pandoc: `pip install --user pypandoc-binary` 経由が一番手軽(winget 不要)。バンドルされた `pandoc.exe` を `build_pdf.ps1` が自動検出する。
> - 日本語フォント: **Yu Mincho / Yu Gothic UI** (Windows 10/11 標準) を採用。Noto JP の Google Fonts 配布版(可変フォント)は `xdvipdfmx` が `Invalid font: -1 (0)` で弾くため、デフォルトでは使わない。

## 1. Pandoc

### 1a. pip 経由(推奨・winget 不要)

```powershell
pip install --user pypandoc-binary
```

`%APPDATA%\Python\Python311\site-packages\pypandoc\files\pandoc.exe` にバンドル版が入る。`build_pdf.ps1` は PATH に pandoc が無いとここを自動で探す。

### 1b. winget 経由(PATH 通したい場合)

```powershell
winget install --id JohnMacFarlane.Pandoc -e
```

確認:

```powershell
pandoc --version   # 3.0 以上推奨
```

## 2. TeX Live(XeLaTeX)

XeLaTeX は日本語縦書き・多言語混在の組版に強い。MiKTeX でも可だが TeX Live のほうが「全部入り」で楽。

```powershell
winget install --id TeXLive.TeXLive -e
```

または手動:
- <https://www.tug.org/texlive/> から `install-tl-windows.exe`
- フルインストール(数 GB だが、足りないパッケージのオンデマンド取得トラブルを避けられる)

確認:

```powershell
xelatex --version
```

## 3. 日本語フォント

### 3a. Yu Mincho / Yu Gothic UI(デフォルト・追加作業ゼロ)

Windows 10/11 に最初から入っているので **何もしなくてよい**。`build_pdf.ps1` のデフォルトはこれ。

### 3b. Noto Sans JP / Noto Serif JP(オプション・要注意)

Google Fonts 配布版は **可変フォント (variable OTF)** で、`xdvipdfmx` が読めず PDF 生成に失敗する。Noto を使いたい場合は **静的版 (static)** を入れる:

1. <https://fonts.google.com/noto/specimen/Noto+Sans+JP> → 「Get font」→ ダウンロード
2. zip 内の `static/` フォルダにある `.ttf`(NotoSansJP-Regular.ttf 等)を選んでインストール
3. `Noto Serif JP` も同様
4. `build_pdf.ps1` 内の `$CJKMain` / `$CJKSans` を `"Noto Serif JP"` / `"Noto Sans JP"` に書き換え

確認:

```powershell
fc-list :lang=ja | Select-String "Noto"
```

## 4. xeCJK(日本語組版)

`build_pdf.ps1` は xeCJK 経由で日本語を組む。TeX Live フルインストールなら同梱済み。

入っていない場合:

```powershell
tlmgr install xecjk
```

## 5. Cascadia Mono(コードブロック用、任意)

`build_pdf.ps1` のデフォルト monofont は Consolas(Windows 標準)。Cascadia Mono を使いたい場合は xdvipdfmx 互換版 (`cascadiamono-otf` パッケージ経由ではなく、システムフォントとして) が必要。試さない方が無難。

## 6. ビルドテスト

```powershell
cd C:\Projects\singulab
.\.claude\skills\submission-pdf\scripts\build_pdf.ps1 -ResetFromTemplate
```

`output\singulab_submission.pdf` が生成されれば OK。

## トラブルシューティング

| 症状 | 原因 / 対処 |
| --- | --- |
| `pandoc: command not found` | PATH に通っていない。winget 後 PowerShell を再起動 |
| `! LaTeX Error: File 'bxjsarticle.cls' not found` | `tlmgr install bxjscls jlreq` |
| `! Package fontspec Error: The font "Noto Sans JP" cannot be found` | Noto JP 未インストール、または「すべてのユーザー」でインストールしていない |
| 日本語が `??` や豆腐になる | `mainfont` / `sansfont` の指定が誤っている。`fc-list :lang=ja` で正確なフォント名を確認 |
| ビルドはできるがフォントが汚い | XeLaTeX ではなく LaTeX が呼ばれている。`--pdf-engine=xelatex` を確認 |

## 代替案: Docker で固める(任意)

ローカルに TeX Live を入れたくない場合、`pandoc/extra` イメージを使う手もある。ただし日本語フォントを別途マウントする必要があり、初手としては推奨しない。
