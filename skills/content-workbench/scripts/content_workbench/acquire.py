"""Source acquisition. No translation, editorial writing or external model credentials."""
from __future__ import annotations

import ipaddress
import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from .core import atomic_text, digest, file_hash, now, read_json, write_json


def run(command, **kwargs):
    return subprocess.run([str(arg) for arg in command], check=True, **kwargs)


def probe(path, count_frames=False):
    if not shutil.which("ffprobe"):
        raise ValueError("FFprobe is missing; install FFmpeg and place both programs on PATH")
    args = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json"]
    if count_frames:
        args.append("-count_frames")
    result = run(args + [path], capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def public_url(value):
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only credential-free public HTTP(S) URLs can be fetched")
    for address in socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError("Automatic article fetching does not access private or loopback networks; import a local file instead")


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_public(value, max_bytes=20 * 1024 * 1024):
    public_url(value)
    opener = urllib.request.build_opener(PublicRedirect())
    with opener.open(urllib.request.Request(value, headers={"User-Agent": "Content-Workbench/0.1"}), timeout=30) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Source exceeds the 20 MB article-fetch limit")
        return data, response.headers.get_content_charset() or "utf-8", response.geturl()


class ArticleText(HTMLParser):
    """Conservative extraction; retain raw HTML for completeness review."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.all_text, self.main_text, self.title = [], [], []
        self.skip = 0
        self.main = 0
        self.in_title = False
        self.main_seen = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "template"):
            self.skip += 1
        if tag in ("main", "article"):
            self.main += 1
            self.main_seen = True
        if tag == "title":
            self.in_title = True
        if tag in ("p", "h1", "h2", "h3", "li", "br", "blockquote", "div", "section"):
            self.all_text.append("\n")
            if self.main:
                self.main_text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "template"):
            self.skip = max(0, self.skip - 1)
        if tag in ("main", "article"):
            self.main = max(0, self.main - 1)
        if tag == "title":
            self.in_title = False
        if tag in ("p", "li", "h1", "h2", "h3", "blockquote"):
            self.all_text.append("\n")
            if self.main:
                self.main_text.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_title:
            self.title.append(data)
        self.all_text.append(data)
        if self.main:
            self.main_text.append(data)

    def result(self):
        raw = "".join(self.main_text if self.main_seen else self.all_text)
        lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in raw.split("\n")]
        return "\n\n".join(line for line in lines if line), "".join(self.title).strip()


def fetch(workspace, item_id, kind="auto"):
    with workspace.lock():
        item = workspace.get(item_id)
        directory = workspace.item_dir(item_id)
        if item["source"].get("fetched_at"):
            source_path = directory / item["source"]["path"]
            if source_path.is_file() and file_hash(source_path) == item["source"]["sha256"]:
                return {"cached": True, "source": item["source"]}
            raise ValueError("Acquired source changed or is missing. Re-collect the intended local file or restore the original; refusing a silent source replacement")
        is_video = kind == "video" or (kind == "auto" and (item["platform"] in ("youtube", "x") or (item["platform"] == "local" and Path(item["source"]["path"]).suffix in (".mp4", ".mov", ".mkv", ".webm", ".m4v"))))
        if is_video:
            if item["platform"] == "local":
                video = directory / item["source"]["path"]
            else:
                import importlib.util
                if not importlib.util.find_spec("yt_dlp"):
                    raise ValueError("Install content-workbench[download] or supply a local video")
                url = item["canonical"] + ("/video/1" if item["platform"] == "x" else "")
                args = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-progress", "--no-overwrites", "--write-info-json", "--write-thumbnail", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", str(directory / "source" / "original.%(ext)s"), url]
                run(args, stdout=sys.stderr)
                info = read_json(directory / "source" / "original.info.json")
                expected = urlsplit(item["canonical"]).query.removeprefix("v=") if item["platform"] == "youtube" else item["canonical"].split("/")[-1]
                if item["platform"] in ("youtube", "x") and str(info.get("id")) != expected:
                    raise ValueError("Downloaded media ID does not match the requested source; refusing mismatched metadata")
                choices = [p for p in (directory / "source").glob("original.*") if p.suffix in (".mp4", ".mkv", ".webm", ".mov") and not re.search(r"\.f\d+", p.stem)]
                if len(choices) != 1:
                    raise ValueError("Cannot unambiguously identify the downloaded media")
                video = choices[0]
                source = item["source"]
                source.update({key: info.get(key) for key in ("id", "title", "uploader", "channel", "upload_date", "webpage_url")})
                source["speaker"] = ""
                source["program"] = ""
                source["video_type"] = ""
                thumbnails = [p for p in (directory / "source").glob("original.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
                if thumbnails:
                    source["thumbnail"] = str(thumbnails[0].relative_to(directory))
                # Captions are independent: a platform caption error must not discard a valid source.
                caption_args = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,zh.*", "--sub-format", "json3/vtt/best", "-o", str(directory / "source" / "captions.%(ext)s"), url]
                try:
                    run(caption_args, stdout=sys.stderr, stderr=sys.stderr)
                    source["caption_download"] = "attempted; inspect saved files"
                except subprocess.CalledProcessError:
                    source["caption_download"] = "failed; use local ASR and inspect the full audio"
                if item["title"] == "待整理素材" and info.get("title"):
                    item["title"] = info["title"]
            media = probe(video)
            streams = media["streams"]
            if not any(s["codec_type"] == "video" for s in streams):
                raise ValueError("The source has no video stream")
            item["source"].update(kind="video", path=str(video.relative_to(directory)), sha256=file_hash(video), duration=float(media["format"]["duration"]), has_audio=any(s["codec_type"] == "audio" for s in streams), fetched_at=now())
            write_json(directory / "source" / "probe.json", media)
        else:
            if item["platform"] == "local":
                path = directory / item["source"]["path"]
                if path.suffix.lower() not in (".txt", ".md", ".html", ".htm"):
                    raise ValueError("Article inputs support TXT, Markdown or HTML; convert other formats with the host assistant before importing")
                text = path.read_text(encoding="utf-8-sig")
                is_html = path.suffix.lower() in (".html", ".htm")
            else:
                data, encoding, final_url = get_public(item["canonical"])
                try:
                    text = data.decode(encoding)
                except (LookupError, UnicodeDecodeError):
                    raise ValueError("Cannot reliably decode this article; import a verified UTF-8 text copy") from None
                path = directory / "source" / "original.html"
                atomic_text(path, text)
                item["source"]["resolved_url"] = final_url
                is_html = True
            title = ""
            if is_html:
                parser = ArticleText()
                parser.feed(text)
                text, title = parser.result()
            if len(text.strip()) < 20:
                raise ValueError("No substantial article body extracted; use the host browser or import the full text")
            text_path = directory / "source" / "body.txt"
            atomic_text(text_path, text + "\n")
            item["source"].update(kind="article", path=str(path.relative_to(directory)), text_path=str(text_path.relative_to(directory)), sha256=file_hash(path), completeness="unreviewed", fetched_at=now())
            if item["title"] == "待整理素材" and title:
                item["title"] = title
        workspace.save(item)
        return {"cached": False, "source": item["source"]}


def transcribe(workspace, item_id, model_name="small", language="en"):
    # Model use and possible first-time model downloads are explicit via this command.
    with workspace.lock():
        item = workspace.get(item_id)
        if item["source"].get("kind") != "video":
            raise ValueError("Acquire a video before transcribing")
        if not item["source"].get("has_audio"):
            raise ValueError("No audio: do not invent speech; import only independently verified on-screen text")
        try:
            import numpy as np
            import whisper
        except ImportError:
            raise ValueError("Local Whisper is unavailable; install the asr extra or import a complete timed transcript") from None
        directory = workspace.item_dir(item_id)
        video = directory / item["source"]["path"]
        duration = item["source"]["duration"]
        signature = digest({"media": file_hash(video), "model": model_name, "language": language, "chunk_seconds": 180})
        checkpoint = directory / "source" / f"asr-{signature[:12]}.json"
        result = read_json(checkpoint) if checkpoint.exists() else {"segments": [], "complete": False, "covered_until": 0, "source_signature": signature, "provider": "local-whisper", "model": model_name, "language": language, "coverage_start": 0, "timing_method": "whisper-word-timestamps"}
        reused_complete = result["complete"]
        if not result["complete"]:
            print(f"Loading local Whisper {model_name}", file=sys.stderr, flush=True)
            model = whisper.load_model(model_name, device="cpu")
            start = result["covered_until"]
            while start < duration - 0.001:
                length = min(180, duration - start)
                print(f"Transcribing {start:.1f}-{start + length:.1f} / {duration:.1f}s", file=sys.stderr, flush=True)
                pcm = run(["ffmpeg", "-v", "error", "-i", video, "-ss", start, "-t", length, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
                chunk = model.transcribe(np.frombuffer(pcm, dtype=np.float32).copy(), language=None if language == "auto" else language, fp16=False, word_timestamps=True, condition_on_previous_text=False, temperature=0)
                for segment in chunk["segments"]:
                    entry = {"start": max(0, start + segment["start"]), "end": min(duration, start + segment["end"]), "text": segment["text"].strip(), "words": []}
                    for word in segment.get("words", []):
                        a, b = max(0, start + word["start"]), min(duration, start + word["end"])
                        if b > a:
                            entry["words"].append({"word": word["word"].strip(), "start": round(a, 3), "end": round(b, 3)})
                    if entry["end"] > entry["start"] and entry["text"]:
                        result["segments"].append(entry)
                start += length
                result.update(covered_until=start, complete=start >= duration - 0.001)
                write_json(checkpoint, result)
        result["source_duration"] = duration
        # Lock is released before put, which provides its own atomic history update.
    workspace.put(item_id, "transcript", checkpoint)
    return {"cached": reused_complete, "path": str(workspace.material_path(item, "transcript")), "complete": result["complete"], "covered_until": result["covered_until"]}


def import_asset(workspace, item_id, path, name):
    from PIL import Image
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", name):
        raise ValueError("Asset name must be 1-48 ASCII letters, numbers, underscores or hyphens")
    source = Path(path).expanduser().resolve()
    with Image.open(source) as image:
        image.verify()
    suffix = source.suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ValueError("Use PNG, JPEG or WebP images")
    with workspace.lock():
        item = workspace.get(item_id)
        checksum = file_hash(source)
        destination = workspace.item_dir(item_id) / "assets" / (name + "-" + checksum[:12] + suffix)
        if not destination.exists():
            shutil.copy2(source, destination)
        item["assets"][name] = {"path": str(destination.relative_to(workspace.item_dir(item_id))), "sha256": checksum}
        workspace.save(item)
        return item["assets"][name]
