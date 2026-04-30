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
| prod_v2_alien_5 | 0.012 | 0.889 | 0.138 | 0.027 | 61 |
| prod_v2_zero_gravity_5 | 0.003 | 0.333 | 0.134 | 0.013 | 62 |
| echo_check_v2_mbti | 0.021 | 1.000 | 0.033 | 0.093 | 45 |

## エージェント別の自己類似度(同じことを言い続けているか)


### prod_v2_alien_5

- Agent 0: self-similarity = 0.000
- Agent 1: self-similarity = 0.011
- Agent 2: self-similarity = 0.071
- Agent 3: self-similarity = 0.024
- Agent 4: self-similarity = 0.000

### prod_v2_zero_gravity_5

- Agent 0: self-similarity = 0.000
- Agent 1: self-similarity = 0.036
- Agent 2: self-similarity = 0.000
- Agent 3: self-similarity = 0.000
- Agent 4: self-similarity = 0.019

### echo_check_v2_mbti

- Agent 0: self-similarity = 0.000
- Agent 1: self-similarity = 0.269
- Agent 2: self-similarity = 0.000
- Agent 3: self-similarity = 0.074
- Agent 4: self-similarity = 0.156