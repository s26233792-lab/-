"""Deterministic typography with a verified font; optional visuals come from imported assets."""
from __future__ import annotations

import re
from pathlib import Path

from .core import write_json
from .fonts import font_path, check_glyphs


def load_font(workspace, size, weight=700):
    from PIL import ImageFont
    font = ImageFont.truetype(str(font_path(workspace)), size)
    if hasattr(font, "set_variation_by_axes"):
        font.set_variation_by_axes([weight])
    return font


def wrapped(text, font, width, max_lines=None):
    """Wrap CJK by character and Latin by whole word, using actual glyph widths."""
    from PIL import Image, ImageDraw
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tokens = re.findall(r"[A-Za-z0-9]+(?:[’'./+-][A-Za-z0-9]+)*|[^A-Za-z0-9]", text)
    lines, current = [], ""
    for token in tokens:
        if token == "\n":
            lines.append(current.rstrip())
            current = ""
            continue
        if draw.textlength(token, font=font) > width:
            raise ValueError("An unbreakable word exceeds the available width; shorten the wording or split at a semantic boundary")
        trial = current + token
        if current and draw.textlength(trial, font=font) > width:
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            current = trial
    if current or not lines:
        lines.append(current.rstrip())
    if max_lines and len(lines) > max_lines:
        raise ValueError(f"Text needs {len(lines)} lines but this region permits {max_lines}; edit or split the content instead of shrinking it")
    return lines


def text_block(draw, xy, text, font, width, color, line_height, max_lines=None):
    lines = wrapped(text, font, width, max_lines)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=color, anchor="lt")
        y += line_height
    return y


def base_image(accent):
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (1080, 1440), "#101113")
    draw = ImageDraw.Draw(image)
    draw.rectangle((64, 58, 126, 67), fill=accent)
    draw.line((64, 1354, 1016, 1354), fill="#34373C", width=2)
    return image, draw


def footer(draw, workspace, page=""):
    signature = workspace.config()["signature"]
    font = load_font(workspace, 26)
    if signature:
        draw.text((64, 1380), signature, font=font, fill="#B4B8BE", anchor="lt")
    if page:
        draw.text((1016, 1380), page, font=font, fill="#B4B8BE", anchor="rt")


def cover(workspace, item, destination, spec=None, wide=False):
    from PIL import Image, ImageDraw, ImageOps
    spec = spec or workspace.material(item, "cover", required=False) or {}
    title = spec.get("headline") or item["title"]
    subtitle = spec.get("subtitle", "")
    check_glyphs(workspace, title + subtitle + workspace.config()["signature"])
    accent = workspace.config()["cover_accent"]
    size = (900, 383) if wide else (1080, 1440)
    image = Image.new("RGB", size, "#0A0B0D")
    draw = ImageDraw.Draw(image)
    asset = spec.get("asset")
    if asset:
        if asset not in item["assets"]:
            raise ValueError(f"Cover asset is not imported: {asset}")
        source = workspace.item_dir(item["id"]) / item["assets"][asset]["path"]
        region = (500, 0, 900, 383) if wide else (0, 400, 1080, 1040)
        with Image.open(source) as opened:
            subject = ImageOps.fit(ImageOps.grayscale(opened).convert("RGB"), (region[2]-region[0], region[3]-region[1]))
            image.paste(subject, region[:2])
        # Regular circular halftone treatment, without modifying the stored original asset.
        for y in range(region[1], region[3], 10):
            for x in range(region[0], region[2], 10):
                draw.ellipse((x, y, x + 2, y + 2), fill="#141518")
    elif not wide:
        # Self-drawn abstract editorial motif, not a screenshot or documentary claim.
        for y in range(466, 950, 24):
            for x in range(96, 990, 24):
                r = 2 + int(4 * ((x + y) % 180) / 180)
                draw.ellipse((x-r, y-r, x+r, y+r), fill="#41464E")
        draw.rounded_rectangle((232, 520, 848, 880), radius=16, fill="#171A1F", outline="#B9BEC5", width=4)
        draw.rectangle((282, 576, 794, 586), fill=accent)
        draw.rectangle((282, 630, 692, 640), fill="#777F8B")
        draw.rectangle((282, 684, 744, 694), fill="#777F8B")
        draw.rectangle((492, 880, 588, 942), fill="#9CA3AF")
        draw.rectangle((380, 942, 700, 952), fill="#9CA3AF")
    if wide:
        font = load_font(workspace, 49)
        text_block(draw, (44, 76), title, font, 438 if asset else 812, "#F5F5F5", 70, 3)
        if subtitle:
            text_block(draw, (44, 308), subtitle, load_font(workspace, 23), 810, accent, 32, 1)
    else:
        if subtitle:
            text_block(draw, (64, 100), subtitle, load_font(workspace, 30), 952, "#B8BDC3", 46, 2)
        lines = wrapped(title, load_font(workspace, 84), 952, 3)
        for index, line in enumerate(lines):
            draw.text((64, 1018 + index * 104), line, font=load_font(workspace, 84), fill=accent if index == len(lines)-1 else "#F4F4F4", anchor="lt")
        footer(draw, workspace)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return {"size": list(size), "font": "Noto Sans SC / SIL OFL 1.1", "asset": asset, "illustration": "imported visual" if asset else "abstract template"}


def render_cards(workspace, item, destination):
    from PIL import Image, ImageOps
    data = workspace.material(item, "cards")
    pages = data.get("pages", [])
    if not 3 <= len(pages) <= 6:
        raise ValueError("A card series needs 3-6 substantive pages; do not repeat text to meet the count")
    accent = workspace.config()["cards_accent"]
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Each card page must be an object")
        all_text = "".join(str(page.get(key, "")) for key in ("title", "intro", "label", "image_caption"))
        for block in page.get("blocks", []):
            if isinstance(block, dict):
                all_text += str(block.get("label", "")) + str(block.get("text", ""))
        check_glyphs(workspace, all_text + workspace.config()["signature"])
    total = len(pages)
    for index, page in enumerate(pages, 1):
        if not page.get("title") or not page.get("blocks"):
            raise ValueError("Every card needs a title and substantive blocks")
        image, draw = base_image(accent)
        label = page.get("label", "")
        if label:
            text_block(draw, (154, 52), label, load_font(workspace, 25), 860, "#AAB0B9", 36, 1)
        y = text_block(draw, (64, 128), page["title"], load_font(workspace, 76), 952, "#F4F4F4", 104, 3) + 42
        if page.get("intro"):
            y = text_block(draw, (64, y), page["intro"], load_font(workspace, 38, 600), 952, "#C6CBD2", 58, 3) + 30
        if page.get("asset"):
            name = page["asset"]
            if name not in item["assets"]:
                raise ValueError(f"Card image has not been imported: {name}")
            source = workspace.item_dir(item["id"]) / item["assets"][name]["path"]
            with Image.open(source) as opened:
                visual = ImageOps.contain(opened.convert("RGB"), (952, 320))
                image.paste(visual, (64 + (952-visual.width)//2, int(y)))
            y += visual.height + 24
            if page.get("image_caption"):
                y = text_block(draw, (64, y), page["image_caption"], load_font(workspace, 26, 600), 952, "#B4B8BE", 38, 2) + 24
        for block_index, block in enumerate(page["blocks"], 1):
            if not isinstance(block, dict) or not block.get("text"):
                raise ValueError("Each card block needs text")
            if page.get("layout") == "steps":
                draw.text((64, y), f"{block_index:02d}", font=load_font(workspace, 32), fill=accent, anchor="lt")
                x, width = 144, 872
            else:
                x, width = 64, 952
            if block.get("label"):
                y = text_block(draw, (x, y), block["label"], load_font(workspace, 39), width, accent, 58, 2) + 12
            y = text_block(draw, (x, y), block["text"], load_font(workspace, 38, 600), width, "#E6E8EC", 58, 7) + 40
            if y > 1320:
                raise ValueError(f"Card {index} overflows; spread the information across pages or simplify without losing conditions")
        footer(draw, workspace, f"{index:02d} / {total:02d}")
        image.save(destination / f"card-{index:02d}.png")
    cover_info = cover(workspace, item, destination / "cover.png")
    thumbs = Image.new("RGB", (270 * total, 360), "#101113")
    for index in range(total):
        with Image.open(destination / f"card-{index + 1:02d}.png") as page:
            thumbs.paste(page.resize((270, 360)), (270 * index, 0))
    thumbs.save(destination / "overview.png")
    return {"passed": True, "page_count": total, "ratio": "3:4", "size": [1080, 1440], "cover": cover_info,
            "scope": "dimensions, measured text fit and file readability; factual accuracy and visual quality require review"}
