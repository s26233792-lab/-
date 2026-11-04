# 收集、获取与恢复

所有示例中的 `cwb` 都可替换为 `python <本技能目录>/scripts/cwb.py`。`--workspace` 放在子命令之前。

```sh
cwb --workspace WORKSPACE init
cwb --workspace WORKSPACE collect URL_OR_FILE --tag 待选题 --note "我想关注的点"
cwb --workspace WORKSPACE batch links.txt
cwb --workspace WORKSPACE list
cwb --workspace WORKSPACE show ITEM_ID
cwb --workspace WORKSPACE next ITEM_ID
```

- 本地文件复制入素材库，避免原文件移动后丢失。内容相同的本地文件去重。
- YouTube 按视频 ID 去重，X 按 status ID 去重；起播参数不会授权截取，默认处理全片。普通网页保留有意义查询参数，仅去除常见追踪参数。
- 同一条重复收集会合并标签和新备注，不覆盖已写终稿与成品。不自动轮询、不创建定时任务。
- `batch` 的输入是 UTF-8 每行一条链接或路径，空行和 `#` 注释跳过；逐条返回错误，部分成功也必须如实说明。
- `hold ID` 暂缓，默认列表隐藏；`list --include-held` 查看，`hold ID --resume` 恢复。

## 获取

```sh
cwb --workspace WORKSPACE fetch ITEM_ID
cwb --workspace WORKSPACE transcribe ITEM_ID --model small --language en
```

普通网页保留原始 HTML 与提取正文。动态页面、付费或登录内容用宿主已经授权的读取能力，或者用户提供的可处理完整文稿；不能只看网页标题补内容。正文提取成功不证明完整。

在线视频获取原片、原封面、元数据及可用字幕，检查媒体 ID 一致。字幕下载独立进行，429 等失败不丢弃已取得的视频。平台字幕用于核对措辞；翻译/顶部标题使用可靠句子时间，选择英语跟读时才用本地 ASR/强制对齐取得真实词时间。不得累加 X 字幕中不含停顿的词时长来伪造跟读。

本地 ASR 按音频区间保存检查点，恢复时校验源文件与模型设置。`complete` 表示覆盖了处理范围，不表示识别完全正确。错误、幻听、专名、漏句需要结合原字幕与原声检查。

取得说话人证据后：

```sh
cwb --workspace WORKSPACE metadata ITEM_ID --speaker "实际讲者" --program "实际节目" --video-type "访谈" --title "访谈｜人物谈具体话题"
```

## 续做

`next` 列出来源状态、个人门检、目标状态和缺失材料。只补本次请求相关部分。

- `not_started`：该输出尚未制作。
- `needs_review`：已制作，等待实际语义/视觉检查。
- `ready`：当前版本已登记检查，可导出。
- `stale`：输入或配置变化，旧成品保留，但不允许当作当前终稿导出。
- `damaged`：成品缺失或内容校验失败，需要重建。
- `failed`：当前输入的制作失败；`next` 返回最后的具体错误，修正后续做。

工作区一次执行一个写入任务。异常退出留下 `.lock` 时，先确认原进程已经结束，再移除那个锁文件；不能直接删除素材目录。失败构建保留独立目录，下次重新制作，避免覆盖或误复用半成品。
