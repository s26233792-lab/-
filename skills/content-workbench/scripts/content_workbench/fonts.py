"""Pinned OFL font acquisition and renamed static subsets for reproducible rendering."""
from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from pathlib import Path
from functools import lru_cache

from .core import file_hash, read_json, write_json

DATA = Path(__file__).parent / "data"


@lru_cache(maxsize=4)
def _characters(path, checksum):
    from fontTools.ttLib import TTFont
    with TTFont(path) as font:
        return frozenset((font.getBestCmap() or {}).keys())


def check_glyphs(workspace, text):
    source = font_path(workspace)
    supported = _characters(str(source), file_hash(source))
    missing = sorted({ord(character) for character in text if not character.isspace() and ord(character) not in supported})
    if missing:
        raise ValueError("The verified font does not cover these characters: " + ", ".join(f"U+{code:04X}" for code in missing) + "; edit explicitly or audit a suitable licensed font, without silent fallback")


def install(workspace):
    manifest = read_json(DATA / "font.json")
    destination = workspace.root / "fonts" / "NotoSansSC.ttf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or file_hash(destination) != manifest["sha256"]:
        with urllib.request.urlopen(manifest["url"], timeout=60) as response:
            data = response.read(24 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
            raise ValueError("Downloaded font checksum does not match the pinned upstream version")
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(destination)
    shutil.copy2(DATA / "OFL-NotoSansSC.txt", destination.parent / "OFL-NotoSansSC.txt")
    write_json(destination.parent / "font-source.json", manifest)
    return {"path": str(destination), "sha256": manifest["sha256"], "license": "SIL OFL 1.1"}


def font_path(workspace):
    path = workspace.root / "fonts" / workspace.config()["font"]
    if not path.is_file():
        raise ValueError("Rendering needs the verified font; run fonts install first")
    manifest = read_json(DATA / "font.json")
    if file_hash(path) != manifest["sha256"]:
        raise ValueError("The font differs from the verified release; use fonts install. Custom fonts require a separate license and manifest audit")
    return path


def make_static(workspace, destination, text, weight=700):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    source = font_path(workspace)
    check_glyphs(workspace, text)
    font = TTFont(source)
    if "fvar" in font:
        font = instantiateVariableFont(font, {"wght": weight}, inplace=False)
    options = subset.Options()
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=text + " \u00a0ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?：，。！？｜（）-+/[]#@")
    subsetter.subset(font)
    family = f"CWB Sans {weight}"
    names = {1: family, 2: "Regular", 3: family + " 0.1", 4: family, 6: f"CWBSans-{weight}", 16: family, 17: "Regular"}
    for platform, encoding, language in ((3, 1, 0x409), (1, 0, 0)):
        for name_id, value in names.items():
            font["name"].setName(value, name_id, platform, encoding, language)
    destination.parent.mkdir(parents=True, exist_ok=True)
    font.save(destination)
    shutil.copy2(DATA / "OFL-NotoSansSC.txt", destination.parent / "OFL-NotoSansSC.txt")
    return family
