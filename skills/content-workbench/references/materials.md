# 命令与材料约定

工作区私有保存原始素材与中间稿。JSON 使用 UTF-8，时间单位为秒；字段必须来自实际素材或明确标注的演示，不能把示例时间复制到新视频。

## 常用命令

```text
cwb --workspace DIR init [--profile neutral|dongning]
cwb --workspace DIR doctor
cwb --workspace DIR fonts install
cwb --workspace DIR collect SOURCE [--title TEXT] [--tag TEXT] [--note TEXT]
cwb --workspace DIR batch links.txt [--tag TEXT]
cwb --workspace DIR list [--tag TEXT] [--include-held]
cwb --workspace DIR show ID
cwb --workspace DIR next ID
cwb --workspace DIR fetch ID [--kind auto|video|article]
cwb --workspace DIR transcribe ID [--model small] [--language en|auto]
cwb --workspace DIR video-options ID [--mode translation|title|follow] [--top-title TEXT]
cwb --workspace DIR metadata ID [--title TEXT] [--speaker TEXT] [--program TEXT] [--video-type TEXT] [--summary TEXT]
cwb --workspace DIR put ID KIND FILE
cwb --workspace DIR asset ID IMAGE --name NAME
cwb --workspace DIR youtube-review ID RECORD.json
cwb --workspace DIR build ID video|cards|wechat
cwb --workspace DIR review ID TARGET RECORD.json
cwb --workspace DIR export ID TARGET --to DIRECTORY
cwb --workspace DIR hold ID [--resume]
cwb --workspace DIR config KEY VALUE
```

`config` 只接受已知的非凭证字段。布尔值使用 `true` / `false`。`batch` 有部分失败时返回非零退出状态，同时保留成功记录。所有命令输出 JSON，进度或错误发到标准错误流；命令失败不能宣称已交付。

## 视频模式选择

`video-options ID` 是只读查询：返回翻译（默认推荐）、顶部标题、英语跟读三项，以及 `selection_recorded`。默认推荐不会自动写成用户选择。用户选定后用 `--mode translation|title|follow` 记录；未记录时，视频制作会停止。已有模式只在用户明确改选时切换，不能因为旧词条还在就自动开启跟读。

标题模式的 `--top-title` 是成片上方的实际标题，未给时沿用最终发布标题；它不改成片文件名。英语跟读要求真实词时间和非空的关键词条；普通翻译与顶部标题只需句子时间。

## 材料

`put` 支持 `transcript`、`evidence`、`subtitles`、`keywords`、`cards`、`article`、`posts`、`cover`。文章为 `.md`，其余 `.json`。保存新稿前保留旧内容的历史副本；直接改磁盘文件也会使内容签名变化，但无法自动生成改前历史，推荐使用 `put`。

### transcript.json

```json
{
  "provider": "实际服务或手工核验来源",
  "timing_method": "实际使用的时间获取方式",
  "complete": true,
  "coverage_start": 0,
  "covered_until": 2.4,
  "segments": [
    {"start": 0.1, "end": 2.0, "text": "Keep the source.", "words": [
      {"word": "Keep", "start": 0.1, "end": 0.4},
      {"word": "the", "start": 0.5, "end": 0.65},
      {"word": "source.", "start": 0.8, "end": 1.3}
    ]}
  ]
}
```

`covered_until` 是实际处理到的全片位置，不能用最后一句的结束时间代替结尾静音的覆盖范围。只有已核实的听不清语气词允许单独 segment 添加 `omit: "unclear_filler"`，疑似实质漏句需要查清。

### subtitles.json

```json
{"cues": [{"start": 0.1, "end": 2.0, "en": "Keep the source.", "zh": "保留原文", "words": [
  {"word": "Keep", "start": 0.1, "end": 0.4},
  {"word": "the", "start": 0.5, "end": 0.65},
  {"word": "source.", "start": 0.8, "end": 1.3}
]}]}
```

所有模式都要求 `start/end/en/zh`，并比较英文实质词与全文转录。翻译/顶部标题模式可省略 `words`；上面的词数据只在英语跟读模式必需。跟读的词序要与原文对应，词时间不能重叠或超出 cue，真实停顿保留，不均分句长。结构通过不证明翻译正确。

### evidence.json

```json
{
  "scope": "full / excerpt with range / user draft，以及实际范围说明",
  "sources": [{"name": "来源名称", "url": "https://example.com/primary", "type": "primary"}],
  "claims": [
    {"text": "需要核实的主张", "kind": "speaker_claim", "source": 0, "locator": "00:10–00:20"},
    {"text": "作者的分析及适用条件", "kind": "analysis"}
  ]
}
```

类型：`fact`、`speaker_claim`、`vendor_demo`、`analysis`、`advice`。前三种必须有有效来源索引和位置。代码只验证结构；虚构来源、伪造核验或把演示泛化为常态仍需要编辑审校识别。

### keywords.json

```json
{"entries": [{"start": 0, "end": 2.0, "word": "source", "meaning": "原始资料"}]}
```

只有英语跟读模式需要非空的 entries，每次一个词/短语，真实出现在对应原文区间，不重叠。翻译与顶部标题模式不会使用此文件，即使素材中已有旧词条。

### cover.json

```json
{"headline": "可读的短封面文字", "subtitle": "访谈｜实际讲者", "asset": "cover-visual"}
```

`asset` 可省略，则采用自绘抽象模板。公众号目标使用同一短文案重新排横版，不拉伸竖封面。长标题应编辑精简，不能删去影响准确性的条件。

### cards.json / posts.json / article.md

完整可运行格式见项目 `examples/`。卡片 3–6 页，每页 `title`、可选 `label`/`intro`、`blocks` 数组（`label` 可选，`text` 必填）。`layout: "steps"` 可显示步骤编号。

发布文案为三个完整字符串 `douyin`、`xiaohongshu`、`x`，平台名放文件小节，文本内部没有字段标签。若本次不需要三平台文案，可不导入，检查结果会注明未包含。

公众号 Markdown 配图写 `![说明](asset:NAME)`，先用 `asset` 导入对应图片。不要嵌入任意绝对路径、远程脚本或未知图片 URL。

## 记录实际审校

```json
{
  "reviewer": "assistant 或实际检查者",
  "notes": "具体检查范围、方法和仍存在的边界，不能仅写已检查",
  "checks": {"source": true, "claims": true, "wording": true, "visual": true}
}
```

公众号必需 `source/claims/wording/visual`；卡片另需 `copy`；视频必需 `source/speaker/translation/timing/visual/copy`。检查未完成时不登记 true。此记录是实际行为声明，不是用户批准或自动正确性证明。

## 个人 YouTube 门检

```json
{
  "decision": "clear",
  "reviewer": "实际检查者",
  "notes": "全文审阅范围与上下文判断",
  "reviewed_full_source": true,
  "findings": []
}
```

`pause` 可记录尚未补齐或疑似情况；`clear` 需要完整转录且没有批评/疑似命中。命中项记录 `start/end/original/explanation/attribution/classification`，classification 为 `criticism`、`uncertain` 或纯提及 `mention`。

用户实际明确同意后，才允许 `decision: "continue"`，并添加 `user_confirmation` 记录真实用户决定。工具验证记录完整性，不会辨认真伪；助手不能伪造授权。转录或源文件变化，旧门检自动失效。读完标题或关键词扫描不算全文审阅。
