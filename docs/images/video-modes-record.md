# 短视频效果图制作记录

制作日期：2026-11-06；工具版本：内容工作台 v0.1.2。

## 素材与制作

源画面由内置 `image_gen` 新生成，为虚构人物的静态图；合成语音取自项目自写的 `tools/smoke_demo.py` 第一条完整演示句。不是实际访谈，也不展示人物口型同步。

英文：Keep the full original source.；中文：保留完整原始资料。单词时间来自逐词合成音频的实际构造，未用均分句长冒充自然语音对齐。

将源图与已知语音组成测试源后，使用同一个 `cwb build … video` 实际生成翻译、顶部标题、英语跟读三条 MP4，再用 FFmpeg 从每条成片的 2.5295 秒截取 PNG。截图没有重新叠字或修改画面。

顶部标题为“演示｜内容整理 / 保留完整原始资料”；跟读词条为“original source / 原始资料”，截图时 `original` 正在高亮。三图无账号署名。

单张截图 1080×1440（3:4）；对照总览 1800×1260，仅在三张截图外添加说明标题和模式介绍。字幕及顶部文字使用已核实的 Noto Sans SC / SIL OFL 1.1，渲染日志确认没有字体回退。

## 实际成片检查

三条均完整保留测试源的 3.96 秒、99 帧，音频 PCM 一致、音画流起点偏移不变，完成全片解码。检查截图可见的顶部标题、青绿词条和英文当前词像素；翻译及标题模式的英文没有青绿高亮。

这些结果只针对本次短测试源，不代表对用户视频设有时长限制，也不证明任意来源的事实或翻译正确。

| 模式 | 时长 / 帧数 | 截图时刻 | 截图 |
|---|---|---|---|
| `translation` | 3.96 秒 / 99 帧 | 2.5295 秒 | [video-translation.png](video-translation.png) |
| `title` | 3.96 秒 / 99 帧 | 2.5295 秒 | [video-title.png](video-title.png) |
| `follow` | 3.96 秒 / 99 帧 | 2.5295 秒 | [video-follow.png](video-follow.png) |

## 文件指纹

### translation

- 已编码 MP4 SHA-256：`dc312f09d81e85e0d11bd4fc7c6db85d1dd984e7b4c64d61ac8a2347b9c57522`。
- 截图 PNG SHA-256：`50fc7bf90ead59d7f1e521d1dd34f6a66c029345a5a2ced063b0c8dbbe382e1c`。

### title

- 已编码 MP4 SHA-256：`db80f260ed66aa1170e4c7ff4f3fd216262d28e18b1fb8241e205694e280b11c`。
- 截图 PNG SHA-256：`61c64747910ac6eb5698a45479f86b9741a31510f9f6f97f9528a64a72fe7d5d`。

### follow

- 已编码 MP4 SHA-256：`71a606642fa1eda748878e98d544871bea417b6dcb0b7b6b68d1c9b5499764a2`。
- 截图 PNG SHA-256：`0da03467f4009777cf3bba1ec04241337390c14e2093ebf9316cf54e38d19149`。

## 实际源图生成提示词

无输入参考图，使用内置图像生成工具、不透明背景。仅生成源画面，不生成字幕或成片布局。

```text
Use case: photorealistic-natural. Asset type: ORIGINAL synthetic source still for an open-source short-video editing demonstration. Generate a landscape 16:9 image, approximately 1920 by 1080. A completely fictional adult educator in their early thirties, friendly thoughtful expression, ordinary dark navy sweater, seated at a wooden desk and looking toward the camera as if explaining a simple idea; one hand makes a small natural gesture, the other rests near a closed plain notebook. Comfortable neutral home studio, soft warm light, a plant and a few unlabelled books softly blurred in the background. Medium shot including head, shoulders and some desk; subject centered, both hands natural and inside the frame, clean documentary-like lens rendering without imitating a real program or person. Natural believable lighting, tasteful restrained colors, high image clarity. This is a fictional demonstration, no resemblance to a celebrity or public figure intended. Absolutely NO text, subtitles, captions, letters, numbers, logos, brand marks, watermarks, app interfaces, microphones with branding or borders. Do not create a finished video frame, black bars, title region or subtitles; output only the source camera scene. Opaque background.
```

代码、项目自写文案及图外排版采用仓库 MIT 许可；项目作者在其可授权范围内按同一许可提供本次模拟效果图。图片不构成对真实人物或事件的声明。

[返回视频效果说明](../video-examples.md)
