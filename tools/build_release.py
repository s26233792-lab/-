"""Create a source release from an explicit public-file allowlist; no private workspaces."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("README.md", "LICENSE", "pyproject.toml", "THIRD_PARTY_NOTICES.md", "CONTRIBUTING.md", ".gitignore", ".gitattributes")
DIRECTORIES = ("skills", "docs", "examples", "tools", "tests", ".github")
ARCHIVE_ROOT = "dongning-media-skill"


def public_files():
    selected = [ROOT / name for name in FILES]
    for name in DIRECTORIES:
        selected.extend(path for path in (ROOT / name).rglob("*") if path.is_file()
                        and "__pycache__" not in path.parts and path.suffix != ".pyc"
                        and not any(part.endswith(".egg-info") for part in path.parts))
    for path in selected:
        if not path.is_file():
            raise ValueError(f"Missing public file: {path.name}")
        if path.suffix.lower() in (".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt", ".ps1"):
            text = path.read_text(encoding="utf-8-sig")
            # Absolute home paths in source/docs are an accidental privacy and portability regression.
            if re.search(r"[A-Za-z]:[/\\]Users[/\\](?!<)", text):
                raise ValueError(f"Personal absolute path in public file: {path.relative_to(ROOT)}")
    return sorted(selected)


def release_version():
    module = ROOT / "skills/content-workbench/scripts/content_workbench/__init__.py"
    version = re.search(r'__version__\s*=\s*"([0-9A-Za-z.+-]+)"', module.read_text(encoding="utf-8"))[1]
    project = re.search(r'^version\s*=\s*"([0-9A-Za-z.+-]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)[1]
    if version != project:
        raise ValueError("Package and project versions differ")
    return version


def main():
    version = release_version()
    directory = ROOT / "dist"
    directory.mkdir(exist_ok=True)
    target = directory / f"{ARCHIVE_ROOT}-v{version}.zip"
    if target.exists():
        suffix = 2
        while (directory / f"{ARCHIVE_ROOT}-v{version}-{suffix}.zip").exists():
            suffix += 1
        target = directory / f"{ARCHIVE_ROOT}-v{version}-{suffix}.zip"
    files = public_files()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, ARCHIVE_ROOT + "/" + path.relative_to(ROOT).as_posix())
        archive.writestr(ARCHIVE_ROOT + "/release-manifest.json", json.dumps({"version": version, "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}, ensure_ascii=False, indent=2))
    print(json.dumps({"archive": str(target), "bytes": target.stat().st_size, "files": len(files), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
