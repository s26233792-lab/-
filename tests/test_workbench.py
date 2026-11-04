import json
import tempfile
import unittest
import os
import subprocess
import sys
from pathlib import Path

from content_workbench.core import Workspace, REQUIRED_CHECKS, canonical_source, safe_name, write_json, atomic_text
from content_workbench.build import validate_evidence
from content_workbench.acquire import ArticleText
from content_workbench.cli import execute, parser
from content_workbench.video import fit_box, validate_subtitles, ass_time


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = Workspace(self.root / "workspace")
        self.workspace.init()
        self.input = self.root / "source.md"
        self.input.write_text("A self-authored source for testing.\n", encoding="utf-8")
        self.item = self.workspace.collect(str(self.input), title="测试／标题") ["item"]

    def tearDown(self):
        self.temporary.cleanup()

    def put(self, kind, content):
        path = self.root / (kind + (".md" if kind == "article" else ".json"))
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            write_json(path, content)
        self.workspace.put(self.item["id"], kind, path)

    def fake_build(self, target="wechat"):
        item = self.workspace.get(self.item["id"])
        signature = self.workspace.signature(item, target)
        destination = self.workspace.build_dir(item, target, signature)
        atomic_text(destination / "article.md", "Checked text.\n")
        self.workspace.record_build(item, target, signature, destination, {"passed": True})
        return destination

    def review(self, target="wechat"):
        self.workspace.review(self.item["id"], target, {"reviewer": "test fixture", "notes": "Checked the deliberately self-authored fixture only.", "checks": {key: True for key in REQUIRED_CHECKS[target]}})

    def test_collect_local_is_independent_copy_and_content_deduplicated(self):
        other = self.root / "moved-copy.txt"
        other.write_bytes(self.input.read_bytes())
        result = self.workspace.collect(str(other), tags=["one"], note="specific note")
        self.assertTrue(result["duplicate"])
        self.assertEqual(result["item"]["id"], self.item["id"])
        self.input.unlink()
        saved = self.workspace.item_dir(self.item["id"]) / self.item["source"]["path"]
        self.assertIn("self-authored", saved.read_text(encoding="utf-8"))

    def test_url_aliases_collect_same_item_without_fetch(self):
        first = self.workspace.collect("https://youtu.be/abcDEF12345?t=10")["item"]
        second = self.workspace.collect("https://www.youtube.com/watch?v=abcDEF12345&list=playlist")
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["id"], second["item"]["id"])
        self.assertEqual(first["source"], {})

    def test_exact_id_prevents_directory_escape(self):
        with self.assertRaises(ValueError):
            self.workspace.get("../outside")

    def test_material_revision_is_preserved_and_unrelated_target_reusable(self):
        self.put("article", "First draft.")
        self.fake_build("video")
        self.fake_build("wechat")
        self.review()
        self.put("article", "Revised draft.")
        item = self.workspace.get(self.item["id"])
        self.assertEqual(self.workspace.status(item)["wechat"], "stale")
        self.assertEqual(self.workspace.status(item)["video"], "needs_review")
        backups = list((self.workspace.item_dir(item["id"]) / "history").glob("article-*"))
        self.assertEqual(len(backups), 1)
        self.assertIn("First", backups[0].read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            self.workspace.export(item["id"], "wechat", self.root / "exports")

    def test_export_is_checked_and_does_not_overwrite(self):
        self.fake_build()
        with self.assertRaises(ValueError):
            self.workspace.export(self.item["id"], "wechat", self.root / "exports")
        self.review()
        one = self.workspace.export(self.item["id"], "wechat", self.root / "exports")
        two = self.workspace.export(self.item["id"], "wechat", self.root / "exports")
        self.assertNotEqual(one["directory"], two["directory"])
        self.assertTrue((Path(one["directory"]) / "package.json").is_file())

    def test_tampered_output_cannot_be_exported(self):
        destination = self.fake_build()
        self.review()
        (destination / "article.md").write_text("tampered", encoding="utf-8")
        self.assertEqual(self.workspace.status(self.workspace.get(self.item["id"]))["wechat"], "damaged")
        with self.assertRaises(ValueError):
            self.workspace.export(self.item["id"], "wechat", self.root / "exports")

    def test_external_source_change_invalidates_review(self):
        self.fake_build()
        self.review()
        source = self.workspace.item_dir(self.item["id"]) / self.item["source"]["path"]
        source.write_text("A different original source", encoding="utf-8")
        self.assertEqual(self.workspace.status(self.workspace.get(self.item["id"]))["wechat"], "stale")

    def test_review_requires_all_real_check_fields(self):
        self.fake_build()
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            self.workspace.review(self.item["id"], "wechat", {"reviewer": "assistant", "notes": "Only checked source", "checks": {"source": True}})

    def test_policy_gate_binds_to_current_full_transcript(self):
        gated = Workspace(self.root / "gated")
        gated.init("dongning")
        item = gated.collect("https://youtube.com/watch?v=abcDEF12345")["item"]
        item["source"]["duration"] = 10.0
        gated.save(item)
        with self.assertRaises(ValueError):
            gated.require_policy(item)
        transcript = self.root / "full.json"
        write_json(transcript, {"complete": True, "coverage_start": 0, "covered_until": 10, "segments": [{"start": 0, "end": 10, "text": "A self-authored fixture"}]})
        gated.put(item["id"], "transcript", transcript)
        review = self.root / "youtube-review.json"
        write_json(review, {"decision": "clear", "reviewer": "test", "notes": "Reviewed complete synthetic fixture", "reviewed_full_source": True, "findings": []})
        execute(parser().parse_args(["youtube-review", item["id"], str(review)]), gated)
        gated.require_policy(gated.get(item["id"]))
        write_json(transcript, {"complete": False, "covered_until": 5, "segments": []})
        gated.put(item["id"], "transcript", transcript)
        with self.assertRaises(ValueError):
            gated.require_policy(gated.get(item["id"]))
        with self.assertRaisesRegex(ValueError, "partial"):
            execute(parser().parse_args(["youtube-review", item["id"], str(review)]), gated)

    def test_workspaces_are_serialized(self):
        with self.workspace.lock():
            with self.assertRaisesRegex(ValueError, "busy"):
                self.workspace.collect(str(self.input))

    def test_json_pipe_is_utf8_even_with_legacy_environment(self):
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        result = subprocess.run([sys.executable, "-m", "content_workbench.cli", "--workspace", str(self.workspace.root), "show", self.item["id"]], capture_output=True, env=env, check=True)
        parsed = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(parsed["item"]["title"], "测试／标题")
        self.assertEqual(parsed["item"]["output_title"], "测试／标题")

    def test_export_timezone_and_unreferenced_asset_do_not_force_render(self):
        self.fake_build("cards")
        item = self.workspace.get(self.item["id"])
        config = self.workspace.config()
        config["timezone"] = "Asia/Taipei"
        write_json(self.workspace.root / "config.json", config)
        item["assets"]["unrelated"] = {"path": "assets/no-reference.png", "sha256": "not used"}
        self.workspace.save(item)
        self.assertEqual(self.workspace.status(item)["cards"], "needs_review")

    def test_failed_build_keeps_specific_resume_information(self):
        from content_workbench.build import build
        with self.assertRaisesRegex(ValueError, "Missing evidence"):
            build(self.workspace, self.item["id"], "wechat")
        item = self.workspace.get(self.item["id"])
        self.assertEqual(self.workspace.status(item)["wechat"], "failed")
        self.assertIn("Missing evidence", item["last_errors"]["wechat"]["message"])


class ContentTests(unittest.TestCase):
    def test_url_identity_retains_meaningful_article_queries(self):
        url, _ = canonical_source("https://example.com/read?lang=zh&id=5&utm_source=x#part")
        self.assertEqual(url, "https://example.com/read?id=5&lang=zh")
        one, _ = canonical_source("https://twitter.com/name/status/123/video/1?s=20")
        two, _ = canonical_source("https://x.com/other/status/123")
        self.assertEqual(one, two)
        with self.assertRaises(ValueError):
            canonical_source("https://secret:password@example.com/")

    def test_safe_names_have_no_traversal_or_reserved_names(self):
        self.assertNotIn("/", safe_name("../bad/name"))
        self.assertEqual(safe_name("CON"), "_CON")

    def test_article_extraction_prefers_main_and_ignores_scripts(self):
        parser = ArticleText()
        parser.feed("<title>Fixture</title><nav>Navigation</nav><main><h1>Actual body</h1><p>Text &amp; detail.</p><script>DO NOT EXECUTE</script></main>")
        text, title = parser.result()
        self.assertEqual(title, "Fixture")
        self.assertIn("Text & detail.", text)
        self.assertNotIn("Navigation", text)
        self.assertNotIn("EXECUTE", text)

    def test_evidence_preserves_claim_types_and_requires_locations(self):
        validate_evidence({"scope": "full", "sources": [{"name": "fixture"}], "claims": [{"text": "A source claim", "kind": "speaker_claim", "source": 0, "locator": "paragraph 1"}]})
        with self.assertRaises(ValueError):
            validate_evidence({"scope": "full", "sources": [], "claims": [{"text": "unsupported", "kind": "fact"}]})

    def test_display_aspect_ratio_includes_sar_and_rotation(self):
        wide = fit_box({"width": 1920, "height": 1080, "sample_aspect_ratio": "1:1"})
        self.assertEqual((wide["width"], wide["height"], wide["x"], wide["y"]), (1080, 608, 0, 416))
        portrait = fit_box({"width": 1080, "height": 1920, "sample_aspect_ratio": "1:1"})
        self.assertEqual(portrait["height"], 608)
        self.assertLess(portrait["width"], 400)
        rotated = fit_box({"width": 1920, "height": 1080, "side_data_list": [{"rotation": 90}]})
        self.assertEqual(rotated["width"], portrait["width"])
        non_square = fit_box({"width": 720, "height": 576, "sample_aspect_ratio": "16:15"})
        self.assertAlmostEqual(non_square["source_display_ratio"], 4/3)

    def test_subtitles_reject_missing_words_overlap_partial_or_omitted_content(self):
        transcript = {"complete": True, "coverage_start": 0, "covered_until": 2, "segments": [{"text": "Hello world."}]}
        valid = {"cues": [{"start": 0, "end": 2, "en": "Hello world.", "zh": "你好世界", "words": [{"word": "Hello", "start": 0.1, "end": 0.7}, {"word": "world.", "start": 0.9, "end": 1.5}]}]}
        self.assertEqual(len(validate_subtitles(valid, transcript, 2)), 1)
        import copy
        missing = copy.deepcopy(valid)
        missing["cues"][0]["words"] = []
        with self.assertRaises(ValueError):
            validate_subtitles(missing, transcript, 2)
        overlapping = copy.deepcopy(valid)
        overlapping["cues"][0]["words"][1]["start"] = 0.5
        with self.assertRaises(ValueError):
            validate_subtitles(overlapping, transcript, 2)
        with self.assertRaises(ValueError):
            validate_subtitles(valid, {**transcript, "covered_until": 1}, 2)
        with self.assertRaises(ValueError):
            validate_subtitles(valid, {**transcript, "segments": [{"text": "Hello world and an omitted explanation"}]}, 2)

    def test_html_has_inline_styles_preserves_punctuation_and_escapes_untrusted_html(self):
        try:
            from markdown_it import MarkdownIt
        except ImportError:
            self.skipTest("Install render extra")
        from content_workbench.wechat import convert, STYLES
        source = "# A title\n\nA sentence。 **重点**\n\n<script>alert(1)</script>\n\n## Next\n\n- First\n- Second\n\n| Name | Value |\n|---|---|\n| x | 2 |\n"
        publish, preview, images = convert(source, "A title", STYLES["minimal"], lambda src: "assets/pic.png")
        self.assertNotIn("<h1", publish)
        self.assertIn("A sentence。", publish)
        self.assertNotIn("<script>", publish)
        self.assertIn("&lt;script&gt;", publish)
        self.assertNotIn("<table", publish)
        self.assertIn("Name：", publish)
        self.assertIn('<li style="', publish)
        self.assertNotIn("class=", publish)
        self.assertEqual(images, [])

    def test_image_preview_and_publication_placeholder_are_distinct(self):
        try:
            import markdown_it
        except ImportError:
            self.skipTest("Install render extra")
        from content_workbench.wechat import convert, STYLES
        publish, preview, images = convert("![diagram](asset:workflow)", "Title", STYLES["minimal"], lambda src: "assets/workflow.png")
        self.assertIn("配图 1", publish)
        self.assertNotIn("<img", publish)
        self.assertIn('src="assets/workflow.png"', preview)
        self.assertEqual(len(images), 1)


if __name__ == "__main__":
    unittest.main()
