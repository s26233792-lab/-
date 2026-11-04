"""Full-duration bilingual video composition with word-accurate color events."""
from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from .acquire import probe, run
from .core import atomic_text, file_hash, write_json
from .fonts import make_static
from .graphics import cover, wrapped


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Timestamps must be finite seconds")
    return float(value)


def ass_time(value):
    cs = round(value * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def srt_time(value):
    ms = round(value * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_text(text):
    if any(ch in text for ch in ("{", "}", "\\", "\r")):
        raise ValueError("ASS control characters in subtitle text need explicit handling; do not embed override commands")
    return text.replace("\n", r"\N")


def normalized(text):
    return "".join(ch.casefold() for ch in text if ch.isalnum())


def validate_subtitles(data, transcript, duration):
    if transcript.get("complete") is not True or seconds(transcript.get("coverage_start", 0)) > 0.01 or seconds(transcript.get("covered_until", -1)) < duration - 0.15:
        raise ValueError("The full source must be transcribed before a complete video can be produced")
    cues = data.get("cues", [])
    if not cues:
        raise ValueError("No bilingual cues; do not manufacture dialogue for silence")
    last_end = 0
    for index, cue in enumerate(cues, 1):
        a, b = seconds(cue.get("start")), seconds(cue.get("end"))
        if not 0 <= a < b <= duration + 0.05 or a < last_end - 0.001:
            raise ValueError(f"Cue {index} is out of range or overlaps its predecessor")
        last_end = b
        if not isinstance(cue.get("en"), str) or not isinstance(cue.get("zh"), str) or not cue["en"].strip() or not cue["zh"].strip():
            raise ValueError(f"Cue {index} requires nonempty English and Chinese")
        words = cue.get("words", [])
        if not words:
            raise ValueError("Word highlighting requires actual word timestamps; sentence durations must not be evenly divided")
        end = a
        for word in words:
            wa, wb = seconds(word.get("start")), seconds(word.get("end"))
            if not isinstance(word.get("word"), str) or not word["word"].strip():
                raise ValueError("Each timed word needs text")
            if not a - 0.001 <= wa < wb <= b + 0.001 or wa < end - 0.001:
                raise ValueError(f"Cue {index} has overlapping or invalid word timestamps")
            if wb - wa < 0.01:
                raise ValueError("Word duration is below ASS centisecond resolution; merge punctuation with its word")
            end = wb
        if normalized(cue["en"]) != normalized(" ".join(w["word"] for w in words)):
            raise ValueError(f"Cue {index} text disagrees with its timed words")
    full_text = " ".join(s["text"] for s in transcript.get("segments", []) if s.get("omit") != "unclear_filler")
    if not full_text or normalized(full_text) != normalized(" ".join(c["en"] for c in cues)):
        raise ValueError("Subtitle English does not cover the checked transcript. Resolve omissions and transcription corrections first; only individually marked unclear fillers may be omitted")
    return cues


def fit_box(stream):
    width, height = int(stream["width"]), int(stream["height"])
    sar = stream.get("sample_aspect_ratio", "1:1")
    try:
        pixel_ratio = float(Fraction(sar.replace(":", "/"))) if sar not in ("N/A", "0:1") else 1.0
    except (ValueError, ZeroDivisionError):
        raise ValueError("Cannot determine the source display aspect ratio") from None
    ratio = width * pixel_ratio / height
    rotation = float(stream.get("tags", {}).get("rotate", 0))
    for entry in stream.get("side_data_list", []):
        if "rotation" in entry:
            rotation = float(entry["rotation"])
    if round(rotation) % 180:
        ratio = 1 / ratio
    max_width, max_height = 1080, 608
    if ratio >= max_width / max_height:
        target_width, target_height = max_width, max_width / ratio
    else:
        target_width, target_height = max_height * ratio, max_height
    target_width = max(2, 2 * round(target_width / 2))
    target_height = max(2, 2 * round(target_height / 2))
    return {"width": target_width, "height": target_height, "x": 2 * round((1080-target_width)/4), "y": 2 * round((1440-target_height)/4), "source_display_ratio": ratio, "rotation": rotation}


def write_ass(workspace, item, destination, cues, keywords):
    from PIL import ImageFont
    text = " ".join(c["zh"] + " " + c["en"] for c in cues) + " ".join(k.get("word", "") + k.get("meaning", "") for k in keywords) + workspace.config()["brand"] + "重点词汇"
    family_zh = make_static(workspace, destination / "fonts" / "CWB650.ttf", text, 650)
    family_en = make_static(workspace, destination / "fonts" / "CWB700.ttf", text, 700)
    font_en = ImageFont.truetype(str(destination / "fonts" / "CWB700.ttf"), 44)
    font_zh = ImageFont.truetype(str(destination / "fonts" / "CWB650.ttf"), 90)
    active = "&H00" + "".join(reversed([workspace.config()["video_accent"][i:i+2] for i in (1, 3, 5)])) + "&"
    gray = "&H00C3BDB8&"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1440
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Chinese,{family_zh},90,&H00F4F4F4,&H00F4F4F4,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,64,64,0,1
Style: English,{family_en},44,&H00C3BDB8,&H00C3BDB8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,76,76,0,1
Style: Keyword,{family_en},132,{active},{active},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1
Style: Meaning,{family_en},46,&H00F4F4F4,&H00F4F4F4,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1
Style: Label,{family_en},28,&H00C3BDB8,&H00C3BDB8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1
Style: Brand,{family_en},58,&H00F4F4F4,&H00F4F4F4,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,9,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events, srt = [], []
    def event(a, b, style, text, layer=1):
        if round(b * 100) > round(a * 100):
            events.append(f"Dialogue: {layer},{ass_time(a)},{ass_time(b)},{style},,0,0,0,,{text}")
    two_line_cues = []
    for index, cue in enumerate(cues, 1):
        wrapped(cue["zh"], font_zh, 952, 1)
        event(cue["start"], cue["end"], "Chinese", r"{\pos(540,1080)}" + ass_text(cue["zh"]))
        word_lines, current, width = [], [], 0
        for word_index, word in enumerate(cue["words"]):
            text_width = font_en.getlength(word["word"])
            gap = font_en.getlength(" ") if current else 0
            if text_width > 928:
                raise ValueError("An English word exceeds the subtitle width")
            if current and width + gap + text_width > 928:
                word_lines.append(current)
                current, width = [], 0
            if current:
                width += font_en.getlength(" ")
            current.append(word_index)
            width += text_width
        if current:
            word_lines.append(current)
        if len(word_lines) > 2:
            raise ValueError(f"Cue {index} needs more than two English lines; split it at real word timings")
        if len(word_lines) == 2:
            two_line_cues.append(index)
        boundaries = sorted({round(cue["start"], 2), round(cue["end"], 2), *(round(w[key], 2) for w in cue["words"] for key in ("start", "end"))})
        for a, b in zip(boundaries, boundaries[1:]):
            middle = (a + b) / 2
            active_word = next((i for i, w in enumerate(cue["words"]) if w["start"] <= middle < w["end"]), None)
            lines = []
            for line in word_lines:
                lines.append(" ".join(r"{\c" + (active if i == active_word else gray) + "}" + ass_text(cue["words"][i]["word"]) for i in line))
            event(a, b, "English", r"{\pos(540,1252)}" + r"\N".join(lines))
        srt.append(f"{index}\n{srt_time(cue['start'])} --> {srt_time(cue['end'])}\n{cue['zh']}\n")
    previous = 0
    for keyword in keywords:
        a, b = seconds(keyword.get("start")), seconds(keyword.get("end"))
        if not 0 <= a < b <= item["source"]["duration"] + 0.05 or a < previous:
            raise ValueError("Keyword intervals overlap or exceed the source")
        previous = b
        if not keyword.get("word") or not keyword.get("meaning"):
            raise ValueError("Keyword needs its real English word/phrase and contextual Chinese meaning")
        if normalized(keyword["word"]) not in normalized(" ".join(c["en"] for c in cues if c["start"] < b and c["end"] > a)):
            raise ValueError("Keyword is not present in the corresponding source interval")
        short_font = ImageFont.truetype(str(destination / "fonts" / "CWB700.ttf"), 132)
        large = short_font.getlength(keyword["word"]) <= 930
        size = 132 if large else 82
        keyword_font = ImageFont.truetype(str(destination / "fonts" / "CWB700.ttf"), size)
        lines = wrapped(keyword["word"], keyword_font, 930, 1 if large else 2)
        meaning_font = ImageFont.truetype(str(destination / "fonts" / "CWB700.ttf"), 46)
        wrapped(keyword["meaning"], meaning_font, 930, 1)
        event(a, b, "Label", r"{\pos(540,100)}重点词汇")
        event(a, b, "Keyword", r"{\pos(540," + ("165" if large else "145") + r")\fs" + str(size) + "}" + ass_text("\n".join(lines)))
        event(a, b, "Meaning", r"{\pos(540," + ("305" if large else "330") + ")}" + ass_text(keyword["meaning"]))
    if workspace.config()["brand"]:
        brand_font = ImageFont.truetype(str(destination / "fonts" / "CWB700.ttf"), 58)
        if brand_font.getlength(workspace.config()["brand"]) > 400:
            raise ValueError("Brand text is too wide for the top-right safe area")
        event(0, item["source"]["duration"], "Brand", r"{\pos(1020,32)}" + ass_text(workspace.config()["brand"]))
    atomic_text(destination / "subtitles.ass", header + "\n".join(events) + "\n")
    atomic_text(destination / "subtitles.srt", "\n".join(srt))
    return {"cue_count": len(cues), "word_count": sum(len(c["words"]) for c in cues), "two_line_cues": two_line_cues, "keyword_count": len(keywords)}


def pcm_hash(path):
    # Streaming avoids holding a long film's decoded PCM in memory.
    with subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", "s16le", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
            checksum.update(chunk)
        error = process.stderr.read()
        if process.wait():
            raise ValueError("Audio decoding failed: " + error.decode(errors="replace")[-1000:])
        return checksum.hexdigest()


def verify_video(source, output):
    before, after = probe(source, True), probe(output, True)
    original = next(s for s in before["streams"] if s["codec_type"] == "video")
    encoded = next(s for s in after["streams"] if s["codec_type"] == "video")
    frames_in, frames_out = int(original["nb_read_frames"]), int(encoded["nb_read_frames"])
    if frames_in != frames_out:
        raise ValueError(f"Decoded frame count changed: {frames_in} -> {frames_out}")
    if (encoded["width"], encoded["height"]) != (1080, 1440):
        raise ValueError("Encoded canvas is not 1080x1440")
    if any(float(entry.get("rotation", 0)) % 360 for entry in encoded.get("side_data_list", [])):
        raise ValueError("Encoded canvas retains an unexpected display rotation")
    duration_in, duration_out = float(before["format"]["duration"]), float(after["format"]["duration"])
    if abs(duration_in-duration_out) > 0.15:
        raise ValueError("Output duration differs materially from the complete source")
    audio_in = next((s for s in before["streams"] if s["codec_type"] == "audio"), None)
    audio_out = next((s for s in after["streams"] if s["codec_type"] == "audio"), None)
    if bool(audio_in) != bool(audio_out):
        raise ValueError("An audio stream was lost or unexpectedly added")
    audio_equal = None
    sync_delta = None
    if audio_in:
        audio_equal = pcm_hash(source) == pcm_hash(output)
        if not audio_equal:
            raise ValueError("Decoded audio differs despite requesting an unchanged source track")
        offset_before = float(audio_in.get("start_time", 0))-float(original.get("start_time", 0))
        offset_after = float(audio_out.get("start_time", 0))-float(encoded.get("start_time", 0))
        sync_delta = abs(offset_before-offset_after)
        if sync_delta > 0.08:
            raise ValueError("Audio/video start-time relationship changed")
    run(["ffmpeg", "-v", "error", "-i", output, "-f", "null", "-"], capture_output=True)
    return {"passed": True, "decoded_frames_in": frames_in, "decoded_frames_out": frames_out, "duration_in": duration_in, "duration_out": duration_out,
            "audio_pcm_equal": audio_equal, "av_offset_delta_seconds": sync_delta, "full_decode": True, "scope": "frame count, duration, PCM identity, stream offsets and full decode; semantic alignment and visual legibility still require review"}


def render_video(workspace, item, destination):
    if not shutil.which("ffmpeg"):
        raise ValueError("FFmpeg is required for video composition")
    if item["source"].get("kind") != "video":
        raise ValueError("Acquire a video before building")
    source = workspace.item_dir(item["id"]) / item["source"]["path"]
    media = probe(source)
    stream = next(s for s in media["streams"] if s["codec_type"] == "video")
    source_start = float(media["format"].get("start_time", 0))
    if abs(source_start) > 0.1:
        raise ValueError("This source has a nonzero timeline origin. Normalize the source explicitly and re-check transcript timings before rendering")
    cues = validate_subtitles(workspace.material(item, "subtitles"), workspace.material(item, "transcript"), item["source"]["duration"])
    keyword_data = workspace.material(item, "keywords", required=False)
    keyword_list = keyword_data.get("entries", []) if keyword_data else []
    typography = write_ass(workspace, item, destination, cues, keyword_list)
    box = fit_box(stream)
    filters = f"scale={box['width']}:{box['height']}:flags=lanczos,setsar=1,pad=1080:1440:{box['x']}:{box['y']}:color=black,ass=subtitles.ass:fontsdir=fonts"
    log = destination / "render.log"
    with log.open("w", encoding="utf-8") as stream_log:
        run(["ffmpeg", "-nostdin", "-hide_banner", "-y", "-i", source, "-map", "0:v:0", "-map", "0:a:0?", "-vf", filters,
             "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-fps_mode", "passthrough", "-c:a", "copy", "-metadata:s:v:0", "rotate=0", "-movflags", "+faststart", "video.mp4"], cwd=destination, stdout=stream_log, stderr=stream_log)
    # libass must select the renamed verified fonts, with no unlicensed fallback.
    font_log = log.read_text(encoding="utf-8", errors="replace")
    if "failed to find any fallback" in font_log.lower() or "Glyph 0x" in font_log:
        raise ValueError("The rendered subtitles contain a missing glyph or font fallback; inspect render.log")
    selected_fonts = [line.split("->", 1)[1] for line in font_log.splitlines() if "fontselect:" in line and "->" in line]
    if not selected_fonts or any("CWBSans-" not in line for line in selected_fonts):
        raise ValueError("libass selected a font outside the verified renamed subset; inspect render.log")
    checks = verify_video(source, destination / "video.mp4")
    checks.update(typography=typography, video_box=box, font_selection_verified=True, cover=cover(workspace, item, destination / "cover.png"))
    thumbnail = item["source"].get("thumbnail")
    if thumbnail:
        original = workspace.item_dir(item["id"]) / thumbnail
        shutil.copy2(original, destination / ("original-cover" + original.suffix.lower()))
    # Representative frames are extracted from the actual encoded file, including two-line English when present.
    times = {min(0.2, item["source"]["duration"]/2), max(0, item["source"]["duration"]-0.2), (max(cues, key=lambda c: len(c["en"]))["start"] + max(cues, key=lambda c: len(c["en"]))["end"])/2}
    first_word = cues[0]["words"][0]
    times.add((first_word["start"]+first_word["end"])/2)
    previews = destination / "previews"
    previews.mkdir()
    for index, moment in enumerate(sorted(times), 1):
        run(["ffmpeg", "-v", "error", "-ss", moment, "-i", destination / "video.mp4", "-frames:v", "1", "-y", previews / f"frame-{index:02d}.png"], capture_output=True)
    checks["preview_times"] = sorted(times)
    return checks
