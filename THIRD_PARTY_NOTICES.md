# Third-party components and distribution

Project-authored code and instructions are MIT licensed. No third-party skill is vendored wholesale. The original short-video/event workflows informed the user-authorized scope; private memories and historical project code are not part of the release. Current card-style previews are newly made simulated examples with project-authored prose; see the [preview notice](skills/content-workbench/references/styles/NOTICE.md) and [generation records](docs/images/simulated-samples.md).

| Component | Use | Distribution / license |
|---|---|---|
| Noto Sans SC | Runtime text and sans-serif documentation typography | Font binary downloaded separately from a pinned Google Fonts commit; SIL OFL 1.1 text and SHA-256 manifest included |
| Noto Serif SC | Serif typography in documentation preview PNGs | Locally installed font with embedded SIL OFL 1.1 notice; fingerprint recorded with the preview prompts; no font binary or font file embedded in PNGs is redistributed |
| Pillow | PNG typography and image composition | Optional Python dependency, HPND; see upstream distribution |
| fontTools | Static font instances and subsets | Optional Python dependency, MIT; see upstream distribution |
| markdown-it-py / mdurl | Safe Markdown parsing | Optional Python dependencies, MIT; see upstream distribution |
| tzdata | IANA timezone data, including Windows | Optional Python dependency; upstream Apache-2.0 and database notices |
| yt-dlp | Optional online media acquisition | Separate Python dependency, upstream Unlicense and third-party notices; binaries may include differently licensed components |
| openai-whisper / Torch / NumPy and dependencies | Optional local ASR | Installed separately; retain each upstream package's own license and model notices |
| FFmpeg / libass / libx264 | External media rendering | Not bundled. Actual FFmpeg license depends on build options; libx264-enabled builds include GPL components |
| setuptools | Python build backend | Build dependency, MIT |

Font source: `google/fonts` commit `a85815a42757630ce188fdad368c2dfc444d4773`, `ofl/notosanssc`. See [font manifest](skills/content-workbench/scripts/content_workbench/data/font.json) and [full OFL notice](skills/content-workbench/scripts/content_workbench/data/OFL-NotoSansSC.txt). Static/subset font instances receive a new internal family name (`CWB Sans ...`) and preserve license metadata.

FFmpeg's official license explanation: https://ffmpeg.org/legal.html . This project invokes an external executable and does not redistribute it. Any future binary installer must separately audit the exact binaries, notices and source-distribution obligations rather than copying this project's MIT label onto them.

Example prose and fixture-generation code are project-authored. Windows demo speech, when available, uses the operating system's installed synthesizer and is generated locally; no voice engine is redistributed. Current demo assets and style previews contain no third-party interview, original video thumbnail, real-person portrait or actual social account. Five card illustrations and the usage-guide illustration strip were newly generated with the built-in image tool; the other two card examples use native typography. They are simulations, not documentary evidence or screenshots of an actual software interface. The [video-mode previews](docs/video-examples.md) use an additional newly generated fictional-person still and project-authored synthetic speech: their video layout, titles and subtitles are screenshots extracted from actual rendered MP4 files, not a real interview or a lip-sync demonstration. See the [video preview record](docs/images/video-modes-record.md).

User source media, required attribution, generated visuals, fonts embedded in source footage and third-party model outputs retain their own conditions. The toolkit does not certify their rights or override required attribution.
