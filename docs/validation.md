# v0.1 validation

The automated suite exercises collection identity, immutable source copies, revision history, target invalidation, output integrity, no-overwrite export, serialized writes, full-transcript gate binding, truthful timestamp requirements, display aspect ratios, Markdown escaping, inline styling and image handoff.

The offline media demo creates a full >28-second source, checks all decodable frames, full duration, unchanged decoded audio, stream offsets and full-output decoding. On Windows it can create known-timeline English speech using the installed system voice; elsewhere `--tone-only` explicitly uses tones and does not claim speech recognition. This is source construction for tests, not timing inference applied to real interviews.

The demo builds a video, three cards and a WeChat package, verifies unchanged-input reuse, and leaves review pending. An actual reviewer must inspect the produced visuals before exporting. Unit tests use isolated fixture attestations only to test export-state behavior.

These checks do **not** certify an arbitrary translation, source completeness, facts, speaker identity, media reuse rights, platform availability, semantic word alignment, model quality, or WeChat account-specific paste/mobile display. No online video platform or WeChat account is required for the offline test. Do not report a provider as tested merely because its Python module was found by `doctor`.

## Local release check — 2026-11-04

- Windows / Python 3.14: 27 checks passed, including six opt-in real-media cases. The default suite skips those six unless the verified test font directory is provided.
- The self-authored speech demo produced a 35.96-second / 899-frame MP4, with identical decoded source audio, unchanged stream start offsets and a successful full decode. All eight bilingual cues and eight keyword intervals were produced; a long English sentence exercises the two-line layout.
- A public primary webpage was actually collected and extracted. Local Whisper `small` actually covered the complete self-authored speech source; this tests the adapter, not general recognition quality.
- The WeChat local preview was opened at 390px width: the bundled image loaded, no horizontal overflow or body H1 duplication was found, and no scripts were present. This is not a WeChat-account paste test.
- Source/target revision, actual encoded-frame previews and generated card/cover images were inspected. The public ZIP excludes private workspaces, original media, render logs, local plans and machine paths.
- GitHub Actions configuration is supplied for Python 3.10/3.12 on Windows/Linux; those remote jobs have not been run as part of this local check.
- A source ZIP was extracted into an isolated directory, installed into a fresh virtual environment without shared system packages, and used to build video, cards and WeChat output with freshly installed dependencies. The self-contained skill launcher was also installed into a separate test skill directory and initialized successfully.

To include the opt-in cases:

```powershell
$env:CWB_TEST_FONT_DIR = (Resolve-Path './workspace/fonts').Path
python -m unittest discover -s tests -v
```

On POSIX, prefix the test command with `CWB_TEST_FONT_DIR=/path/to/workspace/fonts` instead. Font installation is explicit via `cwb --workspace ./workspace fonts install`.

## v0.1.1 video modes

New checks cover the distinction between a recommended default and a submitted user choice, refusal to produce an unselected video, persisted mode changes, independent top-title text, and video-only invalidation. Sentence-timed subtitles are sufficient for translation/title, while follow mode requires actual word times and keyword entries. An isolated adapter test verifies that only follow requests Whisper word alignment and that translation/title reuse the same segment-timing checkpoint; it does not claim model accuracy.

Opt-in media checks additionally render title mode without word data and follow mode with a real timed highlight/keyword schedule. They inspect generated ASS events as well as actual encoded frame count, source audio, duration and full decoding.

Local v0.1.1 regression: all 36 checks passed on Windows/Python 3.14, including eight opt-in media checks and seven new mode/adapter checks. A mocked Whisper adapter is used only to test selection of segment/word timestamps and cache reuse; actual model recognition quality is outside that check.

The three modes were also rendered from the same explicitly clipped self-authored speech fixture and visually inspected: plain translation has an empty top area and fixed English color; title mode has an actual two-line top title; follow mode has a keyword/gloss and active-word color. All three preserved 3.96 seconds, 99 decoded frames and identical decoded audio relative to that fixture. This short fixture is for mode validation and is not a processing-duration limit.

## v0.1.2 skill and package synchronization

The release includes the updated skill entry point, user-selected card-style instructions, seven newly composed simulated previews, the illustrated usage guide and style overview. Source, archive manifest and a fresh isolated skill installation are compared for file integrity; this checks the distributed skill itself rather than only the README. Documentation link checks and actual GitHub image loading were also checked.

The style library is an instruction and reference library for the host assistant. The local card renderer still provides its documented dark base template; the seven previews do not imply seven automatic renderer themes. Other styles require the host's actual illustration, typography and image-export capabilities.

No media-rendering logic changes in this release. The regular suite covers 28 tests; eight opt-in media tests remain conditional on FFmpeg and a verified font. Earlier media results above remain versioned evidence, not a new media run for v0.1.2.
