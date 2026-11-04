"""User choice, default presentation and timing requirements of the three modes."""
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from content_workbench.core import Workspace, read_json, write_json, video_options
from content_workbench.cli import execute, parser
from content_workbench.build import build
from content_workbench.video import validate_subtitles


class VideoModeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = Workspace(self.root / "workspace")
        self.workspace.init()
        source = self.root / "fixture.txt"
        source.write_text("Known self-authored fixture for state tests.", encoding="utf-8")
        self.item = self.workspace.collect(str(source), title="最终发布标题")["item"]

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_is_offered_but_reading_does_not_make_a_choice(self):
        result = execute(parser().parse_args(["video-options", self.item["id"]]), self.workspace)
        self.assertEqual(result["options"], {"mode": "translation"})
        self.assertFalse(result["selection_recorded"])
        self.assertEqual([c["mode"] for c in result["choices"]], ["translation", "title", "follow"])
        self.assertNotIn("video_options", self.workspace.get(self.item["id"]))
        with self.assertRaisesRegex(ValueError, "explicitly"):
            self.workspace.set_video_options(self.item["id"])
        with self.assertRaisesRegex(ValueError, "Ask the user"):
            build(self.workspace, self.item["id"], "video")
        self.assertEqual(list((self.workspace.item_dir(self.item["id"]) / "builds").iterdir()), [])

    def test_explicit_selection_persists_and_title_has_a_separate_field(self):
        result = execute(parser().parse_args(["video-options", self.item["id"], "--mode", "title", "--top-title", "画面上的短标题"]), self.workspace)
        self.assertTrue(result["selection_recorded"])
        self.assertEqual(result["options"], {"mode": "title", "top_title": "画面上的短标题"})
        self.assertEqual(self.workspace.get(self.item["id"])["output_title"], "最终发布标题")
        self.workspace.set_video_options(self.item["id"], "follow")
        self.assertEqual(video_options(self.workspace.get(self.item["id"])), {"mode": "follow"})

    def test_title_uses_final_title_when_user_did_not_supply_short_copy(self):
        result = self.workspace.set_video_options(self.item["id"], "title")
        self.assertEqual(result["top_title"], "最终发布标题")
        with self.assertRaises(ValueError):
            self.workspace.set_video_options(self.item["id"], "translation", "不应该显示")

    def test_switching_modes_invalidates_only_video(self):
        self.workspace.set_video_options(self.item["id"], "translation")
        item = self.workspace.get(self.item["id"])
        before = {target: self.workspace.signature(item, target) for target in ("video", "cards", "wechat")}
        self.workspace.set_video_options(self.item["id"], "title", "顶部标题")
        item = self.workspace.get(item["id"])
        after = {target: self.workspace.signature(item, target) for target in before}
        self.assertNotEqual(before["video"], after["video"])
        self.assertEqual(before["cards"], after["cards"])
        self.assertEqual(before["wechat"], after["wechat"])

    def test_unused_keyword_changes_do_not_affect_translation(self):
        self.workspace.set_video_options(self.item["id"], "translation")
        before = self.workspace.signature(self.workspace.get(self.item["id"]), "video")
        file = self.root / "keywords.json"
        write_json(file, {"entries": [{"word": "unused", "meaning": "未使用"}]})
        self.workspace.put(self.item["id"], "keywords", file)
        self.assertEqual(before, self.workspace.signature(self.workspace.get(self.item["id"]), "video"))

    def test_translation_accepts_sentence_timing_follow_requires_words(self):
        transcript = {"complete": True, "coverage_start": 0, "covered_until": 2, "segments": [{"text": "Keep the source."}]}
        subtitles = {"cues": [{"start": 0.1, "end": 1.5, "en": "Keep the source.", "zh": "保留原文"}]}
        self.assertEqual(len(validate_subtitles(subtitles, transcript, 2)), 1)
        with self.assertRaisesRegex(ValueError, "actual word timestamps"):
            validate_subtitles(subtitles, transcript, 2, require_words=True)

    def test_asr_only_requests_word_alignment_for_follow_and_reuses_segment_cache(self):
        from content_workbench.acquire import transcribe
        item = self.workspace.get(self.item["id"])
        item["source"].update(kind="video", has_audio=True, duration=1.2)
        self.workspace.save(item)
        calls = []
        class Audio:
            def copy(self):
                return self
        class Model:
            def transcribe(self, audio, **options):
                calls.append(options["word_timestamps"])
                segment = {"start": 0.1, "end": 0.6, "text": "One."}
                if options["word_timestamps"]:
                    segment["words"] = [{"word": "One.", "start": 0.1, "end": 0.6}]
                return {"segments": [segment]}
        fake_numpy = types.SimpleNamespace(float32="float32", frombuffer=lambda *args, **kwargs: Audio())
        fake_whisper = types.SimpleNamespace(load_model=lambda *args, **kwargs: Model())
        with patch.dict(sys.modules, {"numpy": fake_numpy, "whisper": fake_whisper}), patch("content_workbench.acquire.run", return_value=subprocess.CompletedProcess([], 0, stdout=b"fixture")):
            self.workspace.set_video_options(item["id"], "translation")
            first = transcribe(self.workspace, item["id"])
            self.assertFalse(first["cached"])
            self.assertEqual(self.workspace.material(self.workspace.get(item["id"]), "transcript")["timing_method"], "whisper-segment-timestamps")
            self.workspace.set_video_options(item["id"], "follow")
            self.assertFalse(transcribe(self.workspace, item["id"])["cached"])
            self.workspace.set_video_options(item["id"], "title")
            self.assertTrue(transcribe(self.workspace, item["id"])["cached"])
        self.assertEqual(calls, [False, True])


if __name__ == "__main__":
    unittest.main()
