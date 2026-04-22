---
description: 変更を確認し、日本語コミット + push まで一気に実行する
argument-hint: [任意: コミットメッセージ。省略時は差分から自動生成]
allowed-tools: Bash(git:*), Read, Grep, Glob
---

以下の手順でコミットと push を行ってください。

## 0. 現状確認

!`git status`

!`git diff --stat`

## 1. ステージング方針

- **ステージ対象**: 上記の modified / untracked のうち、以下 **以外** のすべて
  - `CLAUDE.md` / `MEMORY.md`(空のメタファイル)
  - `.claude/` 配下(ローカル設定)
  - `.gitignore` でブロック済みのもの
- ステージ済みファイルがあればそれを尊重する。未ステージのみの場合は上記基準で `git add` する。
- 判断に迷う新規フォルダ・拡張子があればユーザーに確認してから追加する。

## 2. コミットメッセージの決定

- `$ARGUMENTS` が与えられている場合、それを **件名** として採用する。
- 与えられていない場合、`git diff --cached` の内容から日本語で件名を生成する。
  - 件名は 50字以内、変更の種類(追加/更新/修正/整理/削除)を含める
  - 複数ファイルにまたがる変更は本文で箇条書きにする
- 末尾に必ず以下の trailer を含める(1行空けて):

  ```
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```

- コミット実行は heredoc を使う:

  ```bash
  git commit -m "$(cat <<'EOF'
  <件名>

  <本文(必要なら)>

  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  EOF
  )"
  ```

## 3. Push の実行

- `git push` を試みる。
- ハーネスの権限ルールで **main 直push が拒否された場合のみ**、以下の案内をユーザーに返す:

  > Push が権限ルールで拒否されました。ターミナルで以下を実行してください:
  >
  > ```
  > cd <リポジトリのルート>
  > git push
  > ```

- 拒否以外のエラー(認証・リモート未設定 等)が出た場合は、そのエラーメッセージを共有して対処方針を提示する。

## 4. 結果報告

- コミットの短縮 SHA と件名
- push 成否(成功 / 手動 push 要)
- 次にやるべきことが明らかなら一言添える

## 注意

- **破壊的操作は禁止**(`--force`, `reset --hard`, `push --force`, `--no-verify` 等)
- 秘密情報(`.env`、鍵、トークン等)が差分に混ざっていないかコミット前に目視確認
- `docs/10_共有資料/` は `.gitignore` 済み。ここに秘匿コードがあるので間違えて追加しない
