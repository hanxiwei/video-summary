# transcript-quality Skill

对比不同 Whisper 参数下的转写质量，自动推荐最优参数。

## 触发条件
- 用户提到 "transcript quality" / "转写质量" / "Whisper 参数"
- 修改 `app/audio/transcriber.py` 中的 `language` 或 `temperature` 等参数时

## 执行流程

### 1. 准备测试音频
- 使用 `tests/` 中已有的 mock 音频，或让用户提供一个 30-60 秒的中文测试音频
- 确保音频包含：清晰语音 + 背景噪音 + 中英文混合内容

### 2. 参数矩阵测试
对以下参数组合分别转写：
| 参数 | 候选值 |
|------|--------|
| language | zh, auto |
| temperature | 0, 0.2, 0.4 |
| response_format | verbose_json, text |

### 3. 质量评分
对每个结果评估：
- **字错率 (CER)**：对比人工标注文本
- **标点准确度**：逗号/句号位置是否正确
- **数字/英文处理**：中文语境下的数字和英文词汇是否正确
- **噪音鲁棒性**：背景噪音处的转写是否受影响

### 4. 输出推荐
生成 Markdown 表格，列出每个组合的评分和推荐理由。

## 实现提示
- 复用 `WhisperTranscriber` 类，传入不同的初始化参数
- 将温度参数加入 `WhisperTranscriber.__init__`（当前未暴露 temperature）
- 评分脚本写入 `scripts/transcript-bench.py`
