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
| prod_local_startup | 0.336 | 1.000 | 0.705 | 0.422 | 69 |
| prod_urban_startup | 0.310 | 1.000 | 0.675 | 0.560 | 71 |
| prod_local_enterprise | 0.278 | 1.000 | 0.733 | 0.579 | 109 |
| prod_urban_enterprise | 0.247 | 1.000 | 0.748 | 0.702 | 91 |

## エージェント別の自己類似度(同じことを言い続けているか)


### prod_local_startup

- Agent 0: self-similarity = 0.494 🟡 やや反復
- Agent 1: self-similarity = 0.450 🟡 やや反復
- Agent 2: self-similarity = 0.341 🟡 やや反復
- Agent 3: self-similarity = 0.428 🟡 やや反復
- Agent 4: self-similarity = 0.386 🟡 やや反復

### prod_urban_startup

- Agent 0: self-similarity = 0.717 ⚠️ 膠着
- Agent 1: self-similarity = 0.575 ⚠️ 膠着
- Agent 2: self-similarity = 0.517 ⚠️ 膠着
- Agent 3: self-similarity = 0.541 ⚠️ 膠着
- Agent 4: self-similarity = 0.409 🟡 やや反復

### prod_local_enterprise

- Agent 0: self-similarity = 0.777 ⚠️ 膠着
- Agent 1: self-similarity = 0.501 ⚠️ 膠着
- Agent 2: self-similarity = 0.544 ⚠️ 膠着
- Agent 3: self-similarity = 0.651 ⚠️ 膠着
- Agent 4: self-similarity = 0.533 ⚠️ 膠着
- Agent 6: self-similarity = 0.583 ⚠️ 膠着
- Agent 7: self-similarity = 0.586 ⚠️ 膠着
- Agent 9: self-similarity = 0.488 🟡 やや反復

### prod_urban_enterprise

- Agent 0: self-similarity = 0.029
- Agent 1: self-similarity = 0.665 ⚠️ 膠着
- Agent 3: self-similarity = 0.796 ⚠️ 膠着
- Agent 4: self-similarity = 0.709 ⚠️ 膠着
- Agent 6: self-similarity = 0.800 ⚠️ 膠着
- Agent 7: self-similarity = 0.554 ⚠️ 膠着
- Agent 9: self-similarity = 0.741 ⚠️ 膠着