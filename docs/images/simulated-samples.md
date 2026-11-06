# 模拟样张与使用图的制作记录

制作日期：2026-11-06。使用内置 `image_gen` 生成无字插画，再以已核实字体排入中文，经浏览器导出 PNG；不是模型生成文字后直接发布。

## 最终图片

- 卡片：技能目录 `references/styles/` 的七张 PNG，均为 1080×1440（3:4）。
- [七种风格对照](card-styles-overview.png)：2000×1800，引用同一批新样张。
- [Skill 使用图解](skill-usage.png)：2000×1440，展示安装、发素材、选输出、收成品四步和可直接复用的说法。

模拟主题为“把收藏变成作品”。文字由项目新写，不引用历史文章、名人原话或真实账号。深色人物为虚构创作者；企鹅插画只参考作者原有小知角色设计，重新生成场景。白底极简和推文阅读通过原生排版新制，不调用图像模型生成多余插画。

## 字体与排版

- Noto Sans SC，SIL OFL 1.1；字体 SHA-256：`a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`。字体来源与许可见[项目字体记录](../../skills/content-workbench/scripts/content_workbench/data/font.json)。
- Noto Serif SC，已检查字体内嵌的 SIL Open Font License 1.1 声明；本次实际字体 SHA-256：`a4aed9985a5916fbf6690456f8732a9fccd517938e353165d4142b4f11a39280`。仅用于样张栅格化，没有分发字体二进制。
- 中文由 HTML/CSS 排版，字体加载后导出；标题、正文和页码单独定位，检查边界与实际画面。
- 卡片标题通常为“把收藏 / 变成作品”；语录版为“先整理一份素材，再完成一份作品。”并标明“演示文案 · 非人物引语”。
- 公共示例署名为“演示文案 · 冻柠自媒体”；推文阅读作者为虚构的“示例创作者”，没有认证、互动数据或真实账号。

## 使用图中的文字

1. 让助手安装：把本仓库链接发给 Codex，说“请安装冻柠自媒体 Skill”。
2. 发素材：发链接、视频或文章，说明这次想做的内容形式。
3. 选输出：选视频、卡片或公众号，再选对应的模式或风格。
4. 收成品：收取保存在本地的文件，继续改标题、换封面。

示例说法：“用冻柠自媒体 Skill，把这篇文章做成卡片，选 02 暖白拼贴。”

这是说明用图，不是真实应用界面截图，也不代表七套命令行自动换肤已经实现。

2026-11-06 更名后，图内的产品名称与示例说法已重新排版为“冻柠自媒体 Skill”；无字插画继续复用。以下保留当时实际生成提示词，其中旧产品名称属于原始记录。

## 实际图像生成提示词

下面保存每次调用内置工具时使用的原文。提示词只生成无字插画；中文、风格编号和页码由后续排版添加。全部输出使用不透明背景。

### dark-blue

无输入参考图。

```text
Use case: stylized-concept. Asset type: text-free illustration layer for a 3:4 Chinese editorial card, simulated example. Create a full 3:4 portrait canvas. Black charcoal background, restrained electric blue #1769FF highlights, grayscale sophisticated editorial paper-halftone portrait of a COMPLETELY FICTIONAL anonymous adult content creator in a plain dark sweater, seen from rear three-quarter at a small desk holding a folder of notes. No recognizable real person, no celebrity, no logos. Subject entirely within the lower 40% and right-hand portion; dramatic empty BLACK top 52% and left blank negative space for later licensed-font Chinese typesetting. An understated electric blue line loops around a stack of papers, subtle print texture. High-end sharp editorial cover, ample breathing room, no glowing science-fiction interface. CRITICAL absolutely NO text, letters, numbers, labels, signatures, watermarks, Chinese characters or UI anywhere. Not a screenshot. Output opaque 3:4 raster illustration.
```

### warm-collage

无输入参考图。

```text
Use case: stylized-concept. Asset type: text-free illustration layer for a 3:4 Chinese magazine card, simulated example. Full 3:4 portrait canvas. Warm off-white #F8F6F2 paper, rich charcoal #1A1A1A, deep gray #4A4A4A, restrained vivid orange #FF6A00. Editorial collage of torn blank paper, grayscale books and a notebook, a modest path joining a scattered paper stack to a neatly bound booklet; a small orange sun and two short orange crayon strokes. Refined commercial magazine aesthetic, tactile torn edges, restrained grain. All collage elements stay in the bottom 38% of canvas; the top 55% is clean warm off-white negative space for later Chinese typography. No people required, no brands. Absolutely no text, letters, numbers, signatures, printed book titles, quotes, diagrams with labels, interface or watermark. Do not make a moodboard or a grid: a single finished card background. Opaque image.
```

### comic-explainer

输入参考：作者已有的小知企鹅角色设定，仅参考角色特征，重新生成新场景。

```text
Use case: illustration-story. Asset type: text-free background for a single 3:4 Chinese knowledge comic card. Reference image is ONLY the design of the original little penguin character 小知, not an edit target. Preserve its round big head, short chubby body, charcoal outline and body, creamy face and belly, little orange beak and feet, tiny tuft, large warm round eyes, pink cheeks and BLUE BOW TIE. Create a BRAND NEW scene: the same penguin content helper in lower right is cheerfully sorting blank loose paper into a notebook, with three small unlabelled props near the bottom: paperclip folder, pencil, completed booklet. Warm off-white very pale soft background, cute handmade pencil and ink linework, editorial educational clarity, restrained warm orange and soft blue accents. Full portrait 3:4 canvas. Entire top 55% and middle left remains clean uncluttered empty space reserved for later licensed-font Chinese text. Single scene, not a character sheet, no multi-panel grid. Absolutely NO text, glyphs, labels, captions, numbers, speech inside bubbles, brand, watermarks or old author signature. No other animal character. Output opaque raster.
```

### dark-orange

无输入参考图。

```text
Use case: stylized-concept. Asset type: text-free 3:4 editorial knowledge card background, simulated example. Full portrait canvas of near-black lightly textured paper #101113. At lower right in the bottom 35%, render a sharp grayscale regular halftone engraving collage of an open blank notebook, a pencil, three blank index cards and a small closed booklet, organized as an editorial still life. Tiny coral orange #F45B3D paper tab and short underline-shaped brush mark beside the objects. Strong cream-white on black contrast, monochrome object textures, fine print grain, no neon, no UI. Top 58% is calm clean black negative space for later Chinese text, left half of lower area also mostly empty. NO text, letters, numbers, legible writing, stamps, signatures, branding or watermark; notebook pages are blank. Opaque 3:4 image.
```

### quote-pencil

无输入参考图。

```text
Use case: illustration-story. Asset type: text-free illustration background for a 3:4 minimal Chinese quote card, fictional demonstration. Pure white #FFFFFF full portrait 3:4 canvas with abundant clean space. In the bottom 32% only, delicate fine graphite pencil drawing with extremely light warm gray and sage green watercolor tint: a small wooden desk by an open window, a closed laptop, a handwritten-looking but BLANK notebook and pencil, a person seen only as tiny indistinct back silhouette calmly arranging blank paper into a small booklet. Peaceful grounded everyday scene, integrated into white background without a box, no dramatic effect. Top 62% absolutely blank pure white for later licensed-font text. Hand-drawn quiet and restrained, not a stock clip-art icon, no dark heavy color. Absolutely NO typography, characters, letters, quote, labels, numbers, author, watermark or logos anywhere. Pages and computer screen blank. Opaque raster.
```

### skill-usage-art

无输入参考图。

```text
Use case: infographic-diagram. Asset type: four-stage instructional illustration STRIP to be combined with separately typeset Chinese instructions for an open-source AI assistant Skill named 内容工作台. Create a wide landscape 4:1 aspect ratio (e.g. 2048x512). Soft warm white background #F8F6F2. Exactly FOUR evenly spaced separate mini-scenes, left to right, centered at 12.5%,37.5%,62.5%,87.5% of width, each staying inside its own quarter. Scene1: an open package with a small puzzle-piece symbol entering a plain laptop chat window (install Skill in assistant). Scene2: paper article, link-chain symbol and plain video thumbnail flowing into a chat input (send materials). Scene3: three small output choices displayed as simple cards: vertical subtitled video, stacked editorial image cards, article page (choose output). Scene4: neatly finished video, image cards and article inside a local folder with a small check mark (receive and revise files). Elegant friendly editorial illustration, muted gray linework with electric blue #1769FF and warm orange #FF6A00 accents. A few light curved arrows between stages allowed, no realistic app interface. Absolutely NO text, Chinese characters, letters, numbers, labels, logos or watermark. Do not draw people or real company marks. All important objects comfortably inside image with generous margin. This is only the four illustrations strip, not a full poster with empty title region. Opaque wide raster.
```
