# DuolinGal Documentation

DuolinGal is a local-first workflow for extracting, aligning, training, synthesizing, and reinjecting voice assets for KiriKiri Z galgames.

The current repository has already validated a full Senren Banka pipeline:

- extraction and decompilation
- per-speaker dataset export
- GPT-SoVITS single-speaker training
- resumable multi-speaker overnight production
- `wav -> ogg` reinjection staging
- in-game validation through override trees and patch staging

## Primary Language

The main repository README is currently maintained in Chinese:

- [../README.md](../README.md)

## Suggested Reading Order

1. [Structure and Runtime Flow](structure-and-runtime.zh-CN.md)
2. [Dataset Export Guide](dataset-export.zh-CN.md)
3. [GPT-SoVITS Preparation Guide](gptsovits-prep.zh-CN.md)
4. [GPT-SoVITS Training Guide](gptsovits-training.zh-CN.md)
5. [GPT-SoVITS Production Guide](gptsovits-production.zh-CN.md)
6. [Patch Packaging Guide](patch-packaging.zh-CN.md)

## Key Notes

- Real machine-specific paths should stay in local config only.
- Generated character weights should be preserved for future reuse.
- If you later want to build another language dub for the same cast, the default strategy should be:
  - reuse the trained GPT / SoVITS weights first
  - run inference on the new translated text
  - only retrain if the listening result is clearly insufficient

## Important Workflow Policy

Aggressive cleanup of weak utterances, interjections, barks, and non-lexical sounds should be deferred until the **final cleanup stage**, not injected into the main overnight production run.

Why:

- it avoids accidentally deleting good synthesized audio too early
- removing `.ogg` files later naturally falls back to the original Japanese voices in-game
- it keeps the first full production pass as complete as possible
