# Real-model delivery migration

Audio8-ASR-Infinite-80ms and Audio8-ASR-Infinite-160ms are two model resources with separate private HF repositories under APLUX-GenAI4. QNN versions and SoCs are directory dimensions, for example `qnn248_qcs8550/`. The new GitHub delivery target is the private repository `APLUX-Pandora/audio8-asr-infinite-demo`, shared by both models. The historical GitHub repository `APLUX-Pandora/live-transcribe-01` is retained without overwriting its delivery. The Pandora page slug remains `live-transcribe-01`.

## Interface change

| Old delivery | Unified real-model delivery |
|---|---|
| `liblive_transcribe_01.so` | `libaudio8_asr.so` |
| `live_transcribe_01.h` | `audio8_asr.h` |
| `from live_transcribe_01 import Engine, LT01Error` | `from audio8_asr import Engine, A8Error` |
| `lt01_*` C ABI | `a8_*` C ABI |
| `LT01_*` macros and Demo settings | `A8_*` |
| `LIVE_TRANSCRIBE_01_LIB` | `AUDIO8_ASR_LIB` |

This naming change is incompatible with old consumers. Use the matching header, Python module and library together. Old tags are preserved. The SDK no longer builds an identity-renaming forwarding layer; the source, header, Python binding and library use the same names.

## Model resources

- `APLUX-GenAI4/Audio8-ASR-Infinite-80ms`
- `APLUX-GenAI4/Audio8-ASR-Infinite-160ms`

Each repository is private and contains complete packages by QNN/SoC directory, manifests, checksums, tokenizer and applicable licenses. No HF README/model card is added. Graph, quantization, tensor and prefix bytes are preserved. Existing source model resources and old repository history are retained.

The workflow verifies HF privacy, exact revisions and file completeness. CMS editing and mms availability are out of scope. GitHub delivers the shared SDK, examples, Web Demo and public README; it does not carry the C++ inference implementation or private release evidence.

Older tags retain their original SDK. Do not mix interface files or libraries across the naming boundary.
