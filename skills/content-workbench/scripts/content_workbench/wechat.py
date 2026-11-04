"""Safe Markdown to inline-styled WeChat HTML; local image preview is separate."""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

from .core import atomic_text
from .graphics import cover

STYLES = {
    "minimal": {"color": "#25272B", "accent": "#1769FF", "muted": "#F3F5F8", "heading": "#101113"},
    "editorial": {"color": "#292725", "accent": "#C65335", "muted": "#F6F1EB", "heading": "#282421"},
}
FONT = "sans-serif"


def style(tag, palette):
    base = f"font-family:{FONT};font-size:16px;line-height:1.85;color:{palette['color']};"
    additions = {
        "p": "margin:14px 0;word-wrap:break-word;",
        "h2": f"font-size:22px;font-weight:700;line-height:1.5;color:{palette['heading']};margin:30px 0 14px;",
        "h3": f"font-size:18px;font-weight:700;line-height:1.6;color:{palette['heading']};margin:24px 0 12px;",
        "blockquote": f"margin:20px 0;padding:12px 16px;border-left:4px solid {palette['accent']};background-color:{palette['muted']};",
        "ul": "margin:12px 0;padding-left:24px;",
        "ol": "margin:12px 0;padding-left:26px;",
        "li": "margin:8px 0;",
        "strong": f"font-weight:700;color:{palette['accent']};",
        "em": "font-style:italic;",
        "code": f"font-family:monospace;font-size:14px;background-color:{palette['muted']};padding:2px 4px;",
        "pre": f"font-family:monospace;font-size:14px;white-space:pre-wrap;word-wrap:break-word;padding:16px;background-color:{palette['muted']};margin:18px 0;",
        "hr": "border:0;border-top:1px solid #DDDFE3;margin:28px 0;",
        "img": "display:block;width:100%;height:auto;margin:18px 0;",
    }
    return base + additions.get(tag, "")


def element(tag, content, palette):
    return f'<{tag} style="{style(tag, palette)}">{content}</{tag}>'


def convert(markdown, title, palette, resolve_image):
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        raise ValueError("Markdown rendering needs markdown-it-py; install the render extra") from None
    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = parser.parse(markdown)
    # Remove the first leading H1 from the body; keep title in metadata and filename.
    if len(tokens) >= 3 and tokens[0].type == "heading_open" and tokens[0].tag == "h1":
        tokens = tokens[3:]
    images = []

    def inline(children, preview):
        output = []
        for token in children or []:
            if token.type == "text":
                output.append(html.escape(token.content))
            elif token.type in ("softbreak", "hardbreak"):
                output.append(" ")
            elif token.type in ("strong_open", "em_open"):
                tag = "strong" if token.type == "strong_open" else "em"
                output.append(f'<{tag} style="{style(tag, palette)}">')
            elif token.type in ("strong_close", "em_close"):
                output.append("</strong>" if token.type == "strong_close" else "</em>")
            elif token.type == "code_inline":
                output.append(element("code", html.escape(token.content), palette))
            elif token.type == "image":
                src, description = token.attrGet("src") or "", token.content
                relative = resolve_image(src)
                key = (src, description, relative)
                if key not in images:
                    images.append(key)
                number = images.index(key) + 1
                if preview:
                    output.append(f'<img src="{html.escape(relative, quote=True)}" alt="{html.escape(description, quote=True)}" style="{style("img", palette)}">')
                else:
                    output.append(html.escape(f"[配图 {number}：{description}]"))
            elif token.type in ("link_open", "link_close"):
                # Keep visible anchor text. Source records retain URLs separately.
                continue
            else:
                output.append(html.escape(token.content))
        return "".join(output)

    def render(preview):
        output, table_rows, row, in_table = [], [], [], False
        for token in tokens:
            t = token.type
            if t == "table_open":
                in_table = True
                table_rows = []
                continue
            if in_table:
                if t == "tr_open":
                    row = []
                elif t == "inline":
                    row.append(inline(token.children, preview))
                elif t == "tr_close":
                    table_rows.append(row)
                elif t == "table_close":
                    in_table = False
                    headers = table_rows[0] if table_rows else []
                    output.append(f'<ul style="{style("ul", palette)}">')
                    for record in table_rows[1:]:
                        pairs = [element("strong", headers[i] + "：", palette) + value if i < len(headers) else value for i, value in enumerate(record)]
                        output.append(element("li", "；".join(pairs), palette))
                    output.append("</ul>")
                continue
            if t == "inline":
                output.append(inline(token.children, preview))
            elif t in ("fence", "code_block"):
                output.append(element("pre", element("code", html.escape(token.content), palette), palette))
            elif t == "hr":
                output.append(f'<hr style="{style("hr", palette)}">')
            elif token.nesting:
                tag = {"heading_open": "h2" if token.tag in ("h1", "h2") else "h3", "heading_close": "h2" if token.tag in ("h1", "h2") else "h3"}.get(t, token.tag)
                if tag not in ("p", "h2", "h3", "blockquote", "ul", "ol", "li"):
                    raise ValueError(f"Unsupported Markdown block: {tag}")
                if token.nesting == 1:
                    start = token.attrGet("start") if tag == "ol" else None
                    extra = f' start="{int(start)}"' if start is not None else ""
                    output.append(f'<{tag} style="{style(tag, palette)}"{extra}>')
                else:
                    output.append(f"</{tag}>")
            elif token.content:
                output.append(element("p", html.escape(token.content), palette))
        return "\n".join(output)

    publish_body, preview_body = render(False), render(True)
    def document(body):
        return '<!doctype html>\n<html lang="zh-CN">\n<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + html.escape(title) + '</title></head>\n<body style="max-width:740px;margin:0 auto;padding:24px 22px;">\n' + body + "\n</body></html>\n"
    return document(publish_body), document(preview_body), images


def render_wechat(workspace, item, destination):
    markdown = workspace.material(item, "article")
    selected = workspace.config()["wechat_style"]
    if selected not in STYLES:
        raise ValueError("wechat_style must be minimal or editorial")
    assets = destination / "assets"
    assets.mkdir()
    def resolve_image(src):
        if not src.startswith("asset:"):
            raise ValueError("Article images must reference imported assets as asset:NAME; automatic external-image fetching is not supported")
        name = src.removeprefix("asset:")
        if name not in item["assets"]:
            raise ValueError(f"Article image has not been imported: {name}")
        source = workspace.item_dir(item["id"]) / item["assets"][name]["path"]
        target = assets / source.name
        shutil.copy2(source, target)
        return "assets/" + target.name
    publish, preview, images = convert(markdown, item["title"], STYLES[selected], resolve_image)
    atomic_text(destination / "article.md", markdown)
    atomic_text(destination / "wechat.html", publish)
    atomic_text(destination / "preview.html", preview)
    # Match the existing skill's upload-ready cover size without claiming that every account has identical requirements.
    cover_info = cover(workspace, item, destination / "cover.png", wide=True)
    body_without_title = re.sub(r"\A\s*# [^\n]*\n", "", markdown).strip()
    first_paragraph = re.sub(r"[#>*`\[\]]", "", body_without_title.split("\n\n")[0]).strip()
    atomic_text(destination / "摘要.txt", (item.get("summary") or first_paragraph[:120]) + "\n")
    lines = ["公众号发布包", "", "1. 将文章标题填入公众号标题框；正文已经去掉首个一级标题。", "2. 打开 wechat.html，复制正文后粘贴到公众号编辑器。", "3. 将 cover.png 作为封面；横图按账号后台的实际裁切预览检查。", "4. 按编号上传 assets 内的配图，替换正文中的配图标记。", "5. 在公众号后台发给手机预览，检查字级、列表、引用、配图和裁切后再发布。", "", "preview.html 展示本地配图效果；本地图片路径不能通过复制自动变成微信图片。", "未连接公众号账户；未执行草稿同步或发布。", "", "配图顺序："]
    lines += [f"{i}. {description} → {relative}" for i, (_, description, relative) in enumerate(images, 1)]
    atomic_text(destination / "使用说明.txt", "\n".join(lines) + "\n")
    return {"passed": True, "style": selected, "images": len(images), "inline_styles": True, "body_title_removed": True, "cover": cover_info, "platform_paste_verified": False,
            "scope": "safe HTML and local asset packaging; WeChat paste/mobile preview still requires the account owner"}
