"""JSON-output CLI for host assistants and local users."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .core import DEFAULT_CONFIG, KINDS, REQUIRED_CHECKS, TARGETS, VIDEO_MODES, Workspace, now, read_json, write_json, video_options, video_selection_recorded


def doctor(workspace):
    dependencies = {name: bool(importlib.util.find_spec(module)) for name, module in (("pillow", "PIL"), ("fonttools", "fontTools"), ("markdown-it-py", "markdown_it"), ("yt-dlp", "yt_dlp"), ("whisper", "whisper"))}
    ffmpeg, ffprobe = bool(shutil.which("ffmpeg")), bool(shutil.which("ffprobe"))
    subtitle_filter = False
    h264 = False
    if ffmpeg:
        filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        subtitle_filter = any(" ass " in line for line in filters.splitlines())
        h264 = "libx264" in encoders
    font = False
    if (workspace.root / "config.json").exists():
        try:
            from .fonts import font_path
            font_path(workspace)
            font = True
        except ValueError:
            pass
    return {"version": __version__, "python": sys.version.split()[0], "dependencies": dependencies,
            "ffmpeg": ffmpeg, "ffprobe": ffprobe, "libass": subtitle_filter, "libx264": h264, "verified_font": font,
            "capabilities": {"collect": True, "cards": dependencies["pillow"] and dependencies["fonttools"] and font,
                             "wechat": dependencies["pillow"] and dependencies["markdown-it-py"] and font,
                             "video": dependencies["pillow"] and dependencies["fonttools"] and ffmpeg and ffprobe and subtitle_filter and h264 and font,
                             "online_video": dependencies["yt-dlp"] and ffmpeg, "local_asr": dependencies["whisper"] and ffmpeg},
            "host_capabilities": "Research, editorial writing, translation, listening and optional image generation are supplied by the host assistant; this CLI does not claim to have performed them."}


def parser():
    p = argparse.ArgumentParser(description="冻柠自媒体 Skill — collect sources and produce videos, image cards and WeChat articles")
    p.add_argument("--workspace", default=os.environ.get("CWB_WORKSPACE", str(Path.home() / ".content-workbench")))
    p.add_argument("--version", action="version", version=__version__)
    commands = p.add_subparsers(dest="command", required=True)
    q = commands.add_parser("init", help="Initialize a private local workspace")
    q.add_argument("--profile", choices=("neutral", "dongning"), default="neutral")
    commands.add_parser("doctor", help="Inspect installed capabilities without reading credentials")
    q = commands.add_parser("collect", help="Collect only; does not download URLs or invoke models")
    q.add_argument("source")
    q.add_argument("--title")
    q.add_argument("--tag", action="append", default=[])
    q.add_argument("--note", default="")
    q = commands.add_parser("batch", help="Collect newline-separated links or file paths")
    q.add_argument("file")
    q.add_argument("--tag", action="append", default=[])
    q = commands.add_parser("list", help="Read inbox entries and derived target status")
    q.add_argument("--tag")
    q.add_argument("--include-held", action="store_true")
    for command in ("show", "next"):
        q = commands.add_parser(command)
        q.add_argument("id")
    q = commands.add_parser("hold")
    q.add_argument("id")
    q.add_argument("--resume", action="store_true")
    q = commands.add_parser("metadata", help="Record verified attribution and final publication title")
    q.add_argument("id")
    for name in ("title", "speaker", "program", "video-type", "summary"):
        q.add_argument("--" + name)
    q = commands.add_parser("config", help="Set a non-secret workspace setting")
    q.add_argument("key", choices=tuple(DEFAULT_CONFIG))
    q.add_argument("value", help="String or JSON boolean/number; API credentials do not belong here")
    q = commands.add_parser("fetch")
    q.add_argument("id")
    q.add_argument("--kind", choices=("auto", "video", "article"), default="auto")
    q = commands.add_parser("transcribe")
    q.add_argument("id")
    q.add_argument("--model", default="small")
    q.add_argument("--language", default="en")
    q = commands.add_parser("video-options", help="Read available video modes or save the user's selection; default is translation")
    q.add_argument("id")
    q.add_argument("--mode", choices=tuple(VIDEO_MODES))
    q.add_argument("--top-title", help="Title text for title mode; otherwise the final publication title is used")
    q = commands.add_parser("put", help="Import checked draft material; keeps revision history")
    q.add_argument("id")
    q.add_argument("kind", choices=tuple(KINDS))
    q.add_argument("file")
    q = commands.add_parser("asset", help="Import an original or authorized image without changing it")
    q.add_argument("id")
    q.add_argument("file")
    q.add_argument("--name", required=True)
    q = commands.add_parser("youtube-review", help="Record the actual full-transcript policy review")
    q.add_argument("id")
    q.add_argument("file")
    q = commands.add_parser("build", help="Build only the requested output target")
    q.add_argument("id")
    q.add_argument("target", choices=TARGETS)
    q = commands.add_parser("review", help="Record actual source/editorial/visual review, bound to current inputs")
    q.add_argument("id")
    q.add_argument("target", choices=TARGETS)
    q.add_argument("file")
    q = commands.add_parser("export")
    q.add_argument("id")
    q.add_argument("target", choices=TARGETS)
    q.add_argument("--to", required=True)
    q = commands.add_parser("fonts")
    q.add_argument("action", choices=("install",))
    return p


def execute(args, workspace):
    cmd = args.command
    if cmd == "init":
        return {"workspace": str(workspace.root), "config": workspace.init(args.profile)}
    if cmd == "doctor":
        return doctor(workspace)
    workspace.config()
    if cmd == "collect":
        return workspace.collect(args.source, args.title, args.tag, args.note)
    if cmd == "batch":
        results, errors = [], []
        for index, line in enumerate(Path(args.file).read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.strip() and not line.lstrip().startswith("#"):
                try:
                    result = workspace.collect(line.strip(), tags=args.tag)
                    results.append({"id": result["item"]["id"], "duplicate": result["duplicate"]})
                except (ValueError, OSError) as error:
                    errors.append({"line": index, "error": str(error)})
        return {"items": results, "errors": errors, "partial": bool(errors)}
    if cmd == "list":
        entries = []
        for path in sorted((workspace.root / "items").glob("*/item.json")):
            item = read_json(path)
            if (item["hold"] and not args.include_held) or (args.tag and args.tag not in item["tags"]):
                continue
            entries.append({"id": item["id"], "title": item["title"], "platform": item["platform"], "tags": item["tags"], "hold": item["hold"], "status": workspace.status(item), "exports": len(item["exports"])})
        return entries
    if cmd in ("show", "next"):
        item = workspace.get(args.id)
        if cmd == "show":
            return {"item": item, "directory": str(workspace.item_dir(args.id)), "status": workspace.status(item)}
        requirements = {"video": ["transcript", "evidence", "subtitles"], "cards": ["evidence", "cards"], "wechat": ["evidence", "article"]}
        options = video_options(item)
        if options["mode"] == "follow":
            requirements["video"].append("keywords")
        gate = None
        try:
            workspace.require_policy(item)
        except ValueError as error:
            gate = str(error)
        return {"id": args.id, "source_acquired": bool(item["source"].get("fetched_at")), "policy_pause": gate, "status": workspace.status(item), "last_errors": item.get("last_errors", {}), "video_options": options, "video_selection_recorded": video_selection_recorded(item),
                "missing_materials": {target: [kind for kind in kinds if not workspace.material_path(item, kind).exists()] for target, kinds in requirements.items()},
                "review_checks": REQUIRED_CHECKS, "note": "Resume the requested target only; missing material for other targets is not a request to create it."}
    if cmd in ("hold", "metadata", "config"):
        with workspace.lock():
            if cmd == "config":
                config = workspace.config()
                try:
                    value = json.loads(args.value)
                except json.JSONDecodeError:
                    value = args.value
                if type(value) is not type(DEFAULT_CONFIG[args.key]):
                    raise ValueError("Setting type does not match the default configuration")
                if args.key == "schema_version":
                    raise ValueError("schema_version is maintained by the program")
                config[args.key] = value
                old = read_json(workspace.root / "config.json")
                write_json(workspace.root / "config.json", config)
                try:
                    workspace.config()
                except Exception:
                    write_json(workspace.root / "config.json", old)
                    raise
                return config
            item = workspace.get(args.id)
            if cmd == "hold":
                item["hold"] = not args.resume
            else:
                if args.title is not None:
                    if not args.title.strip():
                        raise ValueError("Title must not be blank")
                    item["title"] = args.title.strip()
                if args.summary is not None:
                    item["summary"] = args.summary
                for field in ("speaker", "program", "video_type"):
                    if getattr(args, field) is not None:
                        item["source"][field] = getattr(args, field)
            workspace.save(item)
            return item
    if cmd == "fetch":
        from .acquire import fetch
        return fetch(workspace, args.id, args.kind)
    if cmd == "transcribe":
        from .acquire import transcribe
        return transcribe(workspace, args.id, args.model, args.language)
    if cmd == "video-options":
        if args.mode is not None or args.top_title is not None:
            workspace.set_video_options(args.id, args.mode, args.top_title)
        item = workspace.get(args.id)
        return {"id": args.id, "options": video_options(item), "selection_recorded": video_selection_recorded(item), "choices": [{"mode": key, **value} for key, value in VIDEO_MODES.items()]}
    if cmd == "put":
        # Full YouTube preflight precedes translation, keywords and publishing copy in the personal profile.
        if args.kind != "transcript":
            workspace.require_policy(workspace.get(args.id))
        return workspace.put(args.id, args.kind, args.file)
    if cmd == "asset":
        from .acquire import import_asset
        workspace.require_policy(workspace.get(args.id))
        return import_asset(workspace, args.id, args.file, args.name)
    if cmd == "youtube-review":
        from .video import seconds
        with workspace.lock():
            item = workspace.get(args.id)
            if item["platform"] != "youtube":
                raise ValueError("YouTube-specific review applies only to a YouTube source")
            review = read_json(Path(args.file))
            decision = review.get("decision")
            if decision not in ("clear", "pause", "continue") or not review.get("reviewer") or not review.get("notes"):
                raise ValueError("YouTube review requires decision, reviewer and specific notes")
            if not isinstance(review.get("findings"), list):
                raise ValueError("Review needs a findings list with timestamps, original, explanation and attribution")
            if decision in ("clear", "continue"):
                transcript = workspace.material(item, "transcript")
                if review.get("reviewed_full_source") is not True or transcript.get("complete") is not True or seconds(transcript.get("covered_until", -1)) < item["source"].get("duration", float("inf")) - 0.15:
                    raise ValueError("Cannot clear a partial or unreviewed transcript")
                for finding in review["findings"]:
                    if not all(finding.get(key) is not None for key in ("start", "end", "original", "explanation", "attribution", "classification")):
                        raise ValueError("A finding is missing its supporting context")
                    if finding["classification"] not in ("criticism", "uncertain", "mention"):
                        raise ValueError("Finding classification must be criticism, uncertain or mention")
                    if not 0 <= seconds(finding["start"]) < seconds(finding["end"]) <= item["source"]["duration"] + 0.05:
                        raise ValueError("Finding timestamps are outside the reviewed source")
                if decision == "clear" and any(f.get("classification") in ("criticism", "uncertain") for f in review["findings"]):
                    raise ValueError("A critical or uncertain finding must pause for the user's decision")
                if decision == "continue" and (not isinstance(review.get("user_confirmation"), str) or not review["user_confirmation"].strip()):
                    raise ValueError("Continue requires the user's actual explicit confirmation; never infer it")
            item["youtube_review"] = {**review, "source_signature": workspace.source_signature(item), "recorded_at": now()}
            workspace.save(item)
            return item["youtube_review"]
    if cmd == "build":
        from .build import build
        return build(workspace, args.id, args.target)
    if cmd == "review":
        return workspace.review(args.id, args.target, read_json(Path(args.file)))
    if cmd == "export":
        return workspace.export(args.id, args.target, args.to)
    if cmd == "fonts":
        from .fonts import install
        return install(workspace)
    raise ValueError("Unknown command")


def main(argv=None):
    # Windows pipes otherwise inherit a legacy code page and corrupt JSON Chinese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        result = execute(args, Workspace(args.workspace))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if isinstance(result, dict) and result.get("partial") else 0
    except (ValueError, OSError, KeyError, ImportError, subprocess.CalledProcessError) as error:
        print(json.dumps({"error": str(error), "type": type(error).__name__}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
