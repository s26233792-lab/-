# 公众号文章发布包

两种任务：已有稿排版时只处理排版；从视频/事件改编时，先按编辑参考完成有依据、适合连续阅读的文章。可以复用原文、转录和证据，不能用短视频文案直接扩写填字数。

文章标题和正文范围一致。人物访谈保留论证、故事、例子与观点归属；事件文章说明变化、实际用法、证据范围和限制。编辑建议与来源人物的原话分开。篇幅服从信息，不固定写“1500 字”。

文章用 UTF-8 Markdown，首个 H1 视为文章标题，不重复输出到正文。后续 H1 降成 H2。保留句末标点；格式转换不改写观点。链接保留可见文本，来源 URL 留在独立证据记录，不机械附来源尾注。

配图先导入：

```sh
cwb --workspace WORKSPACE asset ID diagram.png --name workflow
```

正文写 `![流程示意](asset:workflow)`，不直接引用不稳定外链或任意磁盘路径。封面用 `cover.json` 的短标题；最终文章标题用 `metadata --title`，摘要可用 `metadata --summary` 明确给定。

```sh
cwb --workspace WORKSPACE config wechat_style minimal
cwb --workspace WORKSPACE put ID evidence evidence.json
cwb --workspace WORKSPACE put ID article article.md
cwb --workspace WORKSPACE build ID wechat
```

样式：`minimal`（清爽黑白/蓝色重点）、`editorial`（暖色编辑式）。正式 `wechat.html` 使用逐元素行内样式，无脚本、外链 CSS、伪元素和远程字体，不依赖最外层容器继承。表格转为带列名的列表，保留内容；代码按原样转义。

输出：正文 Markdown、摘要、公众号正文 HTML、本地配图预览、900×383 横版封面、配图文件和使用说明。公众号正文用有序配图标记，本地预览用相对图片文件；不能声称本地路径复制后已经上传到微信。

完成实际内容、尺寸和本地视觉检查后记录 review。交付时说明：复制 wechat.html 正文，按编号上传替换配图，在公众号后台发手机预览后发布。未实测账号的粘贴效果保持未验证。不登录账号、不上传草稿、不自动发布。
