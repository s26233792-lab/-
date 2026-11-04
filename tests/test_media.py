"""Opt-in real FFmpeg checks. Fixtures are synthetic and contain no actual interview."""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from content_workbench.core import Workspace, write_json, file_hash
from content_workbench.acquire import run, fetch
from content_workbench.video import render_video
from content_workbench.fonts import check_glyphs

FONT_DIR = os.environ.get("CWB_TEST_FONT_DIR")
ENABLED = bool(FONT_DIR and shutil.which("ffmpeg") and shutil.which("ffprobe") and importlib.util.find_spec("PIL") and importlib.util.find_spec("fontTools"))


@unittest.skipUnless(ENABLED, "Set CWB_TEST_FONT_DIR to a verified workspace fonts directory and install FFmpeg/render dependencies")
class MediaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = Workspace(self.root / "workspace")
        self.workspace.init()
        for name in ("NotoSansSC.ttf", "OFL-NotoSansSC.txt"):
            shutil.copy2(Path(FONT_DIR) / name, self.workspace.root / "fonts" / name)

    def tearDown(self):
        self.temporary.cleanup()

    def compose(self, shape, filters=None, rotate=False, audio=True):
        media = self.root / "fixture.mp4"
        args = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size={shape}:rate=10:duration=1.2"]
        if audio:
            args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=22050:duration=1.2", "-c:a", "aac"]
        if filters:
            args += ["-vf", filters, "-fps_mode", "vfr"]
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", media]
        run(args, capture_output=True)
        if rotate:
            rotated = self.root / "rotated.mp4"
            run(["ffmpeg", "-v", "error", "-display_rotation:v:0", "90", "-i", media, "-c", "copy", "-y", rotated], capture_output=True)
            media = rotated
        item = self.workspace.collect(str(media), title="合成布局测试")["item"]
        fetch(self.workspace, item["id"])
        item = self.workspace.get(item["id"])
        transcript = self.root / "transcript.json"
        write_json(transcript, {"complete": True, "coverage_start": 0, "covered_until": item["source"]["duration"], "segments": [{"text": "One."}], "provider": "synthetic-test-schedule, not speech"})
        self.workspace.put(item["id"], "transcript", transcript)
        subtitles = self.root / "subtitles.json"
        write_json(subtitles, {"cues": [{"start": 0.1, "end": 1.0, "en": "One.", "zh": "一", "words": [{"word": "One.", "start": 0.15, "end": 0.6}]}]})
        self.workspace.put(item["id"], "subtitles", subtitles)
        destination = self.root / "output"
        destination.mkdir()
        checks = render_video(self.workspace, self.workspace.get(item["id"]), destination)
        self.assertTrue(checks["passed"])
        self.assertEqual(checks["decoded_frames_in"], checks["decoded_frames_out"])
        self.assertTrue(checks["font_selection_verified"])
        self.assertEqual(checks["audio_pcm_equal"], True if audio else None)
        return checks

    def test_portrait_is_complete_and_centered(self):
        checks = self.compose("360x640")
        self.assertEqual(checks["video_box"]["height"], 608)
        self.assertLess(checks["video_box"]["width"], 400)

    def test_non_square_pixels_preserve_display_ratio(self):
        checks = self.compose("720x576", "setsar=16/15")
        self.assertAlmostEqual(checks["video_box"]["source_display_ratio"], 4/3)

    def test_rotation_metadata_is_applied_once(self):
        checks = self.compose("640x360", rotate=True)
        self.assertEqual(abs(checks["video_box"]["rotation"]), 90)
        self.assertLess(checks["video_box"]["width"], 400)

    def test_variable_frame_timing_does_not_duplicate_or_drop_frames(self):
        checks = self.compose("640x360", "select=not(eq(mod(n\\,4)\\,1))")
        self.assertLess(checks["decoded_frames_in"], 12)

    def test_silent_source_does_not_gain_audio(self):
        self.compose("640x360", audio=False)

    def test_unsupported_character_is_reported_without_font_fallback(self):
        with self.assertRaisesRegex(ValueError, "U\\+10FFFF"):
            check_glyphs(self.workspace, "\U0010ffff")


if __name__ == "__main__":
    unittest.main()
