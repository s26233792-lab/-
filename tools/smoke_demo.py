"""Build self-authored offline examples. Deliberately stops before editorial/visual review."""
from __future__ import annotations

import argparse
import array
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "content-workbench" / "scripts"))
from content_workbench.core import Workspace, write_json, read_json
from content_workbench.acquire import run

PHRASES = [
    ("Keep the full original source.", "保留完整原文", "original source", "原始资料"),
    ("So every output can be checked.", "便于逐份核对成品", "can be checked", "能够核对"),
    ("Use evidence to check each claim.", "用证据核对每个主张", "evidence", "支持判断的证据"),
    ("Do this before writing.", "先核实再动笔", "before writing", "写作之前"),
    ("Change the format and keep the meaning.", "改变形式保留原意", "keep the meaning", "保留原意"),
    ("Save the finished files.", "保存完成的文件", "finished files", "已完成的文件"),
    ("And keep the earlier versions.", "也保留之前的版本", "earlier versions", "较早的版本"),
    ("Different output formats can share the same original source.", "多种输出共用原文", "output formats", "输出形式")
]


def cli(workspace, *arguments):
    result = subprocess.run([sys.executable, str(ROOT / "skills/content-workbench/scripts/cwb.py"), "--workspace", str(workspace), *map(str, arguments)], check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def make_audio(output, tone_only):
    words = [word for phrase, _, _, _ in PHRASES for word in phrase.split()]
    write_json(output / "fixture-words.json", words)
    spoken = os.name == "nt" and not tone_only
    if spoken:
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ROOT / "tools/spoken_fixture.ps1", "-WordsFile", output / "fixture-words.json", "-OutputDirectory", output / "word-audio"], capture_output=True)
    rate = 22050
    samples = array.array("h", [0] * int(rate * 0.5))
    word_records = []
    for index, word in enumerate(words):
        if spoken:
            with wave.open(str(output / "word-audio" / f"{index:03d}.wav"), "rb") as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, rate):
                    raise ValueError("Unexpected fixture voice format")
                sound = array.array("h")
                sound.frombytes(source.readframes(source.getnframes()))
            voiced = [i for i, sample in enumerate(sound) if abs(sample) > 100]
            if not voiced:
                raise ValueError("TTS fixture contains no audible word")
            margin = int(rate * 0.015)
            sound = sound[max(0, voiced[0]-margin):min(len(sound), voiced[-1]+margin)]
        else:
            sound = array.array("h", [int(4000 * math.sin(2 * math.pi * (400 + index % 4 * 60) * n / rate)) for n in range(int(rate * 0.32))])
        start = len(samples) / rate
        samples.extend(sound)
        end = len(samples) / rate
        word_records.append({"word": word, "start": round(start, 3), "end": round(end, 3)})
        samples.extend([0] * int(rate * (0.55 if word.endswith(".") else 0.09)))
    # A >28 s source tests that the composer has no inherited demo cutoff.
    samples.extend([0] * max(int(rate), int(rate * 30.4)-len(samples)))
    with wave.open(str(output / "fixture.wav"), "wb") as destination:
        destination.setnchannels(1)
        destination.setsampwidth(2)
        destination.setframerate(rate)
        destination.writeframes(samples.tobytes())
    cues, keywords, offset = [], [], 0
    for phrase, zh, keyword, meaning in PHRASES:
        count = len(phrase.split())
        timing = word_records[offset:offset+count]
        a, b = max(0, timing[0]["start"]-0.07), timing[-1]["end"]+0.1
        cues.append({"start": a, "end": b, "en": phrase, "zh": zh, "words": timing})
        keywords.append({"start": a, "end": b, "word": keyword, "meaning": meaning})
        offset += count
    return len(samples) / rate, cues, keywords, "self-authored synthetic English speech" if spoken else "synthetic tones; layout/encoding fixture only, not speech"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--tone-only", action="store_true", help="Portable fixture without Windows speech synthesis; never represents speech recognition")
    args = p.parse_args()
    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "demo-result.json").exists():
        raise ValueError("Demo output already exists; choose a fresh directory to preserve its review and export records")
    workspace = output / "workspace"
    cli(workspace, "init")
    cli(workspace, "fonts", "install")
    # Use short brand text to stay within the production layout's safe region.
    cli(workspace, "config", "brand", "CWB DEMO")
    duration, cues, keywords, fixture_mode = make_audio(output, args.tone_only)
    media = output / "fixture.mp4"
    run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=640x360:rate=25:duration={duration}", "-i", output / "fixture.wav", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-y", media], capture_output=True)
    video_id = cli(workspace, "collect", media, "--title", "演示｜完整双语视频与同步重点词")["item"]["id"]
    cli(workspace, "fetch", video_id)
    actual = Workspace(workspace).get(video_id)["source"]["duration"]
    transcript = {"provider": "self-authored-fixture", "timing_method": "known synthetic source construction, not ASR", "fixture_mode": fixture_mode, "complete": True, "coverage_start": 0, "covered_until": actual, "segments": [{"start": c["start"], "end": c["end"], "text": c["en"], "words": c["words"]} for c in cues]}
    write_json(output / "transcript.json", transcript)
    write_json(output / "subtitles.json", {"cues": cues})
    write_json(output / "keywords.json", {"entries": keywords})
    evidence = {"scope": fixture_mode + "; known source and timestamp construction for layout/encoding validation; no external interview", "sources": [{"name": "tools/smoke_demo.py", "type": "self-authored synthetic fixture"}], "claims": [{"text": "The source is a self-authored fixture.", "kind": "fact", "source": 0, "locator": "PHRASES and make_audio"}]}
    write_json(output / "video-evidence.json", evidence)
    for kind, file in (("transcript", output/"transcript.json"), ("subtitles", output/"subtitles.json"), ("keywords", output/"keywords.json"), ("evidence", output/"video-evidence.json"), ("cover", ROOT/"examples/cover.json"), ("posts", ROOT/"examples/posts.json")):
        cli(workspace, "put", video_id, kind, file)
    video = cli(workspace, "build", video_id, "video")
    assert cli(workspace, "build", video_id, "video")["cached"] is True
    article_id = cli(workspace, "collect", ROOT/"examples/source.md", "--title", "离线演示｜把素材变成可用的内容")["item"]["id"]
    cli(workspace, "fetch", article_id)
    for kind in ("evidence", "cover", "posts", "cards", "article"):
        suffix = ".md" if kind == "article" else ".json"
        cli(workspace, "put", article_id, kind, ROOT / "examples" / (kind+suffix))
    cards = cli(workspace, "build", article_id, "cards")
    diagram = Path(cards["directory"]) / "card-02.png"
    cli(workspace, "asset", article_id, diagram, "--name", "workflow")
    # An article-only image must not invalidate unrelated card output.
    assert cli(workspace, "build", article_id, "cards")["cached"] is True
    article = cli(workspace, "build", article_id, "wechat")
    result = {"fixture_mode": fixture_mode, "workspace": str(workspace), "video_id": video_id, "article_id": article_id, "video": video, "cards": cards, "wechat": article, "review": "pending actual visual/editorial review", "platform_paste_verified": False}
    write_json(output / "demo-result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
