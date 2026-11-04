"""Local inbox, immutable build records and content-addressed review state."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TARGETS = ("video", "cards", "wechat")
KINDS = {"transcript": ".json", "evidence": ".json", "subtitles": ".json",
         "keywords": ".json", "cards": ".json", "article": ".md", "posts": ".json", "cover": ".json"}
DEPENDENCIES = {"video": ("transcript", "evidence", "subtitles", "keywords", "posts", "cover"),
                "cards": ("evidence", "cards", "posts", "cover"),
                "wechat": ("evidence", "article", "cover")}
REQUIRED_CHECKS = {"video": ("source", "speaker", "translation", "timing", "visual", "copy"),
                   "cards": ("source", "claims", "wording", "visual", "copy"),
                   "wechat": ("source", "claims", "wording", "visual")}
DEFAULT_CONFIG = {"schema_version": 1, "profile": "neutral", "timezone": "UTC",
                  "brand": "", "signature": "", "video_accent": "#2DD4BF",
                  "cover_accent": "#1769FF", "cards_accent": "#F45B3D",
                  "wechat_style": "minimal", "font": "NotoSansSC.ttf",
                  "youtube_full_review": False}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def canonical_source(value: str):
    parts = urlsplit(value)
    if parts.scheme.lower() in ("https", "http"):
        if parts.username or parts.password:
            raise ValueError("Source URLs must not contain credentials")
        host = (parts.hostname or "").lower().removeprefix("www.")
        if not host:
            raise ValueError("URL has no hostname")
        if host in ("youtube.com", "m.youtube.com", "youtu.be"):
            video_id = (parts.path.strip("/").split("/")[0] if host == "youtu.be" else
                        parse_qs(parts.query).get("v", [""])[0])
            match = re.match(r"/(?:shorts|embed|live)/([^/]+)", parts.path)
            if match:
                video_id = match[1]
            if video_id and re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
                return f"https://www.youtube.com/watch?v={video_id}", "youtube"
        if host in ("x.com", "twitter.com", "mobile.twitter.com"):
            match = re.search(r"/status/(\d+)", parts.path)
            if match:
                return f"https://x.com/i/status/{match[1]}", "x"
        query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                       if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid"))
        netloc = host + (f":{parts.port}" if parts.port else "")
        return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", urlencode(query), "")), "web"
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Not a readable local file or HTTP(S) URL: {value}")
    return "sha256:" + file_hash(path), "local"


def safe_name(value: str, limit=96) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")[:limit].rstrip(" .")
    if not name:
        raise ValueError("Title must contain a usable filename")
    if name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = "_" + name
    return name


class Workspace:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()

    @contextlib.contextmanager
    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / ".lock"
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise ValueError("Workspace is busy. If a crashed process left .lock, verify it stopped before removing that file.") from None
        try:
            os.write(descriptor, str(os.getpid()).encode())
            os.close(descriptor)
            yield
        finally:
            path.unlink(missing_ok=True)

    def init(self, profile="neutral"):
        with self.lock():
            if (self.root / "config.json").exists():
                return self.config()
            config = dict(DEFAULT_CONFIG)
            if profile == "dongning":
                config.update(profile=profile, timezone="Asia/Taipei", brand="@冻柠", signature="BY冻柠AI", youtube_full_review=True)
            elif profile != "neutral":
                raise ValueError("Unknown profile")
            write_json(self.root / "config.json", config)
            (self.root / "items").mkdir(exist_ok=True)
            (self.root / "fonts").mkdir(exist_ok=True)
            return config

    def config(self):
        path = self.root / "config.json"
        if not path.exists():
            raise ValueError("Workspace is not initialized; run init first")
        config = read_json(path)
        if set(config) != set(DEFAULT_CONFIG):
            raise ValueError("Configuration contains missing or unsupported fields; keep credentials outside the workspace config")
        for key, default in DEFAULT_CONFIG.items():
            if key not in config or type(config[key]) is not type(default):
                raise ValueError(f"Invalid or missing configuration field: {key}")
        try:
            ZoneInfo(config["timezone"])
        except ZoneInfoNotFoundError:
            raise ValueError("Install tzdata or configure a supported IANA timezone") from None
        for key in ("video_accent", "cover_accent", "cards_accent"):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", config[key]):
                raise ValueError(f"Invalid color: {key}")
        return config

    def item_dir(self, item_id):
        if not re.fullmatch(r"[0-9a-f]{12}", item_id):
            raise ValueError("Item ID must be an exact 12-character ID from list")
        return self.root / "items" / item_id

    def get(self, item_id):
        path = self.item_dir(item_id) / "item.json"
        if not path.is_file():
            raise ValueError(f"Unknown item: {item_id}")
        return read_json(path)

    def save(self, item):
        item["output_title"] = item["title"]
        item["updated_at"] = now()
        write_json(self.item_dir(item["id"]) / "item.json", item)

    def collect(self, value, title=None, tags=(), note=""):
        self.config()
        canonical, platform = canonical_source(value)
        item_id = hashlib.sha256(canonical.encode()).hexdigest()[:12]
        with self.lock():
            if (self.item_dir(item_id) / "item.json").exists():
                item = self.get(item_id)
                item["tags"] = sorted(set(item["tags"]) | set(tags))
                if note and note not in item["notes"]:
                    item["notes"].append(note)
                self.save(item)
                return {"duplicate": True, "item": item}
            directory = self.item_dir(item_id)
            for name in ("source", "drafts", "assets", "history", "builds"):
                (directory / name).mkdir(parents=True, exist_ok=True)
            item = {"schema_version": 1, "id": item_id, "input": value, "canonical": canonical,
                    "platform": platform, "title": title or (Path(value).stem if platform == "local" else "待整理素材"),
                    "tags": sorted(set(tags)), "notes": [note] if note else [], "created_at": now(),
                    "source": {}, "materials": {}, "assets": {}, "builds": {}, "reviews": {}, "exports": [], "hold": False}
            if platform == "local":
                src = Path(value).resolve()
                target = directory / "source" / ("original" + src.suffix.lower())
                shutil.copy2(src, target)
                item["source"] = {"path": str(target.relative_to(directory)), "sha256": file_hash(target), "original_name": src.name}
            self.save(item)
            return {"duplicate": False, "item": item}

    def material_path(self, item, kind):
        return self.item_dir(item["id"]) / "drafts" / (kind + KINDS[kind])

    def put(self, item_id, kind, source):
        if kind not in KINDS:
            raise ValueError(f"Unknown material kind: {kind}")
        source = Path(source).expanduser().resolve()
        raw = source.read_text(encoding="utf-8-sig")
        if not raw.strip():
            raise ValueError("Material must not be empty")
        if KINDS[kind] == ".json":
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("JSON material must be an object")
        with self.lock():
            item = self.get(item_id)
            if kind != "transcript":
                self.require_policy(item)
            destination = self.material_path(item, kind)
            if destination.exists():
                old_hash = file_hash(destination)
                backup = self.item_dir(item_id) / "history" / (kind + "-" + old_hash[:16] + KINDS[kind])
                if not backup.exists():
                    shutil.copy2(destination, backup)
            atomic_text(destination, raw.rstrip() + "\n")
            item["materials"][kind] = {"path": str(destination.relative_to(self.item_dir(item_id))), "sha256": file_hash(destination), "updated_at": now()}
            self.save(item)
            return item["materials"][kind]

    def material(self, item, kind, required=True):
        path = self.material_path(item, kind)
        if not path.is_file():
            if required:
                raise ValueError(f"Missing {kind}; prepare and import it with put")
            return None
        return read_json(path) if KINDS[kind] == ".json" else path.read_text(encoding="utf-8-sig")

    def signature(self, item, target):
        directory = self.item_dir(item["id"])
        source = {k: v for k, v in item["source"].items() if k not in ("path", "original_name")}
        for key in ("path", "text_path", "thumbnail"):
            if item["source"].get(key):
                path = directory / item["source"][key]
                source[key] = file_hash(path) if path.is_file() else "missing"
        materials = {kind: file_hash(self.material_path(item, kind)) for kind in DEPENDENCIES[target] if self.material_path(item, kind).exists()}
        used_assets = set()
        cover_data = self.material(item, "cover", required=False)
        if cover_data and cover_data.get("asset"):
            used_assets.add(cover_data["asset"])
        if target == "cards":
            card_data = self.material(item, "cards", required=False)
            if card_data and isinstance(card_data.get("pages"), list):
                used_assets.update(page["asset"] for page in card_data["pages"] if isinstance(page, dict) and page.get("asset"))
        if target == "wechat":
            article_data = self.material(item, "article", required=False)
            used_assets.update(re.findall(r"asset:([A-Za-z0-9_-]+)", article_data or ""))
        assets = {}
        for name in sorted(used_assets):
            record = item["assets"].get(name)
            path = directory / record["path"] if record else None
            assets[name] = file_hash(path) if path and path.is_file() else "missing"
        font = self.root / "fonts" / self.config()["font"]
        engine = {path.name: file_hash(path) for path in Path(__file__).parent.glob("*.py")}
        settings = {"video": ("brand", "signature", "video_accent", "cover_accent", "font"),
                    "cards": ("signature", "cards_accent", "cover_accent", "font"),
                    "wechat": ("wechat_style", "cover_accent", "font")}
        config = self.config()
        return digest({"engine": engine, "target": target, "title": item["title"], "summary": item.get("summary", "") if target == "wechat" else "", "source": source,
                       "materials": materials, "assets": assets, "config": {key: config[key] for key in settings[target]},
                       "font": file_hash(font) if font.is_file() else "missing"})

    def source_signature(self, item):
        directory = self.item_dir(item["id"])
        content = {}
        for key in ("path", "text_path"):
            if item["source"].get(key):
                path = directory / item["source"][key]
                content[key] = file_hash(path) if path.exists() else "missing"
        path = self.material_path(item, "transcript")
        if path.exists():
            content["transcript"] = file_hash(path)
        return digest(content)

    def require_policy(self, item):
        if item["platform"] != "youtube" or not self.config()["youtube_full_review"]:
            return
        audit = item.get("youtube_review", {})
        if audit.get("source_signature") != self.source_signature(item) or audit.get("decision") not in ("clear", "continue"):
            raise ValueError("This profile requires full YouTube transcript review before editing/rendering. Record findings with youtube-review; a hit or uncertainty pauses the work until the user's explicit decision.")

    def status(self, item):
        result = {}
        for target in TARGETS:
            build = item["builds"].get(target)
            if not build:
                error = item.get("last_errors", {}).get(target, {})
                result[target] = "failed" if error.get("signature") == self.signature(item, target) else "not_started"
            elif build["signature"] != self.signature(item, target):
                result[target] = "stale"
            elif not self.build_intact(item, target):
                result[target] = "damaged"
            elif item["reviews"].get(target, {}).get("signature") == build["signature"]:
                result[target] = "ready"
            else:
                result[target] = "needs_review"
        return result

    def build_intact(self, item, target):
        build = item["builds"].get(target, {})
        files = build.get("files", [])
        return bool(files) and all((self.item_dir(item["id"]) / f["path"]).is_file() and
                                  file_hash(self.item_dir(item["id"]) / f["path"]) == f["sha256"] for f in files)

    def build_dir(self, item, target, signature):
        parent = self.item_dir(item["id"]) / "builds" / target
        parent.mkdir(parents=True, exist_ok=True)
        base = signature[:12]
        destination = parent / base
        index = 1
        while destination.exists():
            destination = parent / f"{base}-{index}"
            index += 1
        destination.mkdir()
        return destination

    def record_build(self, item, target, signature, directory, checks):
        write_json(directory / "checks.json", checks)
        files = [{"path": str(p.relative_to(self.item_dir(item["id"]))), "name": str(p.relative_to(directory)), "sha256": file_hash(p)} for p in sorted(directory.rglob("*")) if p.is_file()]
        item["builds"][target] = {"signature": signature, "directory": str(directory.relative_to(self.item_dir(item["id"]))), "files": files, "checks": checks, "built_at": now()}
        self.save(item)
        return {"cached": False, "directory": str(directory), "checks": checks}

    def review(self, item_id, target, review):
        with self.lock():
            item = self.get(item_id)
            self.require_policy(item)
            if self.status(item)[target] not in ("needs_review", "ready"):
                raise ValueError("Build the current, intact target before recording a review")
            if not review.get("reviewer") or not review.get("notes"):
                raise ValueError("Review needs reviewer and specific notes; this is an attestation, not an automated proof")
            missing = [name for name in REQUIRED_CHECKS[target] if review.get("checks", {}).get(name) is not True]
            if missing:
                raise ValueError("Unreviewed checks: " + ", ".join(missing))
            item["reviews"][target] = {**review, "signature": item["builds"][target]["signature"], "reviewed_at": now()}
            self.save(item)
            return item["reviews"][target]

    def export(self, item_id, target, destination):
        with self.lock():
            item = self.get(item_id)
            self.require_policy(item)
            if self.status(item)[target] != "ready":
                raise ValueError("Only a current, intact and reviewed build can be exported")
            date = datetime.now(ZoneInfo(self.config()["timezone"])).strftime("%Y-%m-%d")
            destination = Path(destination).expanduser().resolve()
            parent = destination / date
            parent.mkdir(parents=True, exist_ok=True)
            title = safe_name(item["title"])
            folder = parent / f"{title}（{target}）"
            n = 2
            while folder.exists():
                folder = parent / f"{title}（{target}，{n}）"
                n += 1
            build = item["builds"][target]
            source = self.item_dir(item_id) / build["directory"]
            if destination == source or source in destination.parents:
                raise ValueError("Export destination must be outside the build directory")
            folder.mkdir()
            for record in build["files"]:
                relative = Path(record["name"])
                # Main media and text filenames use the final title. HTML-relative assets remain stable.
                names = {"video.mp4": title + ".mp4", "cover.png": title + ".png", "subtitles.srt": title + ".srt",
                         "posts.md": title + "（发布文案）.md", "article.md": title + ".md"}
                if relative.name.startswith("original-cover."):
                    names[str(relative)] = title + "（原封面）" + relative.suffix
                out = folder / names.get(str(relative), str(relative))
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.item_dir(item_id) / record["path"], out)
                if file_hash(out) != record["sha256"]:
                    raise ValueError("Export copy failed checksum verification")
            metadata = {"title": item["title"], "output_title": item["title"], "target": target, "created_at": now(), "source": item["canonical"] if item["platform"] != "local" else item["source"].get("original_name", "local file"), "review": item["reviews"][target], "files": [{"name": str(p.relative_to(folder)), "sha256": file_hash(p)} for p in sorted(folder.rglob("*")) if p.is_file()]}
            write_json(folder / "package.json", metadata)
            item["exports"].append({"target": target, "path": str(folder), "signature": build["signature"], "exported_at": now()})
            self.save(item)
            return {"directory": str(folder), "files": len(metadata["files"])}
