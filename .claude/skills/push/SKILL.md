---
name: push
description: 現在の変更をすべてコミットしてリモートにPushする
disable-model-invocation: true
allowed-tools: Bash(git *)
---

# コミット & プッシュ

ここまでの内容をコミットしPushしてください。

## 手順

1. `git status` で未追跡ファイル・変更ファイルを確認する
2. `git diff --stat` でステージ済み・未ステージの変更を確認する
3. `git log --oneline -5` で直近のコミットメッセージのスタイルを確認する
4. 変更内容を分析し、日本語で簡潔なコミットメッセージを作成する
   - 変更の種類（追加・更新・修正等）と対象を明記
   - コミットメッセージの末尾に `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` を付ける
5. 関連ファイルを `git add` でステージングする（機密ファイルは除外）
6. `git commit` を実行する
7. `git push` を実行する
8. 結果を報告する

## 注意事項

- `.env` や認証情報などの機密ファイルはコミットしない
- 変更がない場合はその旨を報告して終了する
- Pushに失敗した場合はエラー内容を報告する
