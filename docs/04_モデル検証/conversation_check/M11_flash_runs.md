# エージェント間の会話の実態チェック

## 指標の意味

- **echo_mean / echo_max**: 同 step 内の異なる agent の発言ペアの Jaccard 類似度(4-gram)。
  **0.3 を超えるとエコー(似た発言)が起きていると疑える**。1.0 はコピペ

- **reflection_mean**: agent の発言が、それまでに受信したメッセージのキーワードと
  どれくらい重なるか。**0.1〜0.3 程度なら受信を踏まえた応答、0 に近いと無視**

- **self_similarity**: 同じ agent の連続する step の発言類似度。
  **0.5 を超えると同じことを言い続けている状態(膠着)**


## 結果

| シナリオ | echo_mean | echo_max | reflection_mean | self_similarity | unique_msgs |
| --- | ---: | ---: | ---: | ---: | ---: |
| prod_v2_alien_5 | 0.149 | 1.000 | 0.463 | 0.337 | 114 |
| prod_v2_zero_gravity_5 | 0.212 | 1.000 | 0.515 | 0.260 | 79 |

## エージェント別の自己類似度(同じことを言い続けているか)


### prod_v2_alien_5

- Agent 0: self-similarity = 0.645 ⚠️ 膠着
- Agent 1: self-similarity = 0.177
- Agent 2: self-similarity = 0.456 🟡 やや反復
- Agent 3: self-similarity = 0.252
- Agent 4: self-similarity = 0.151

### prod_v2_zero_gravity_5

- Agent 0: self-similarity = 0.174
- Agent 1: self-similarity = 0.245
- Agent 2: self-similarity = 0.209
- Agent 3: self-similarity = 0.120
- Agent 4: self-similarity = 0.539 ⚠️ 膠着