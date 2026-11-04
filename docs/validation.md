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
