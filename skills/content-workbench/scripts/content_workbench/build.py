"""Build dispatch and shared source/copy records."""
from __future__ import annotations

from .core import TARGETS, atomic_text, write_json, now


def validate_evidence(evidence):
    if not evidence.get("scope") or not isinstance(evidence.get("sources"), list) or not isinstance(evidence.get("claims"), list):
        raise ValueError("Evidence needs scope, sources and claims; see the material contract")
    allowed = {"fact", "speaker_claim", "vendor_demo", "analysis", "advice"}
    for claim in evidence["claims"]:
        if claim.get("kind") not in allowed or not claim.get("text"):
            raise ValueError("Each claim needs text and an evidence kind")
        if claim["kind"] in ("fact", "speaker_claim", "vendor_demo"):
            source = claim.get("source")
            if isinstance(source, bool) or not isinstance(source, int) or not 0 <= source < len(evidence["sources"]) or not claim.get("locator"):
                raise ValueError("Factual claims, speaker claims and demos need a valid source index and locator")


def write_posts(workspace, item, destination):
    import re
    posts = workspace.material(item, "posts", required=False)
    if posts is None:
        return False
    lines = []
    for key, label in (("douyin", "抖音"), ("xiaohongshu", "小红书"), ("x", "X")):
        text = posts.get(key)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Posts JSON needs douyin, xiaohongshu and x as complete strings")
        if re.search(r"(?im)^\s*(?:标题|内容|正文|TAG)\s*[:：]", text):
            raise ValueError("Publication copy must not contain title/body/TAG field labels")
        lines.extend([f"## {label}", "", text.strip(), ""])
    atomic_text(destination / "posts.md", "\n".join(lines))
    return True


def build(workspace, item_id, target):
    if target not in TARGETS:
        raise ValueError("Unknown output target")
    with workspace.lock():
        item = workspace.get(item_id)
        workspace.require_policy(item)
        signature = workspace.signature(item, target)
        prior = item["builds"].get(target)
        if prior and prior["signature"] == signature and workspace.build_intact(item, target):
            return {"cached": True, "directory": str(workspace.item_dir(item_id) / prior["directory"]), "checks": prior["checks"]}
        try:
            return _build(workspace, item, target, signature)
        except Exception as error:
            item.setdefault("last_errors", {})[target] = {"message": str(error), "type": type(error).__name__, "signature": signature, "at": now()}
            workspace.save(item)
            raise


def _build(workspace, item, target, signature):
    evidence = workspace.material(item, "evidence")
    validate_evidence(evidence)
    destination = workspace.build_dir(item, target, signature)
    # These records remain outside platform copy and retain provenance for inspection.
    write_json(destination / "source-record.json", {"source": item["canonical"] if item["platform"] != "local" else item["source"].get("original_name", "local file"), "metadata": {k: item["source"].get(k) for k in ("title", "uploader", "speaker", "program", "video_type", "upload_date", "source_range") if item["source"].get(k)}, "evidence": evidence})
    if target == "video":
        from .video import render_video
        checks = render_video(workspace, item, destination)
    elif target == "cards":
        from .graphics import render_cards
        checks = render_cards(workspace, item, destination)
    else:
        from .wechat import render_wechat
        checks = render_wechat(workspace, item, destination)
    if target in ("video", "cards"):
        checks["posts_included"] = write_posts(workspace, item, destination)
    checks["semantic_review"] = "pending"
    if checks.get("passed") is not True:
        raise ValueError("Build did not pass mechanical checks")
    item.get("last_errors", {}).pop(target, None)
    return workspace.record_build(item, target, signature, destination, checks)
