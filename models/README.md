# Audio8-ASR-Infinite model packages

Private HF repositories hold the model assets; this GitHub repository provides the SDK, Python examples and Web Demo.
Private model access is managed separately by the distributor.

## Model repositories and layout

These are two distinct models with separate private repositories:

- `APLUX-GenAI4/Audio8-ASR-Infinite-160ms`
- `APLUX-GenAI4/Audio8-ASR-Infinite-80ms`

Within each repository, `qnn248_qcs8550/` is the model package for QCS8550 / QNN 2.48. Keep its full contents: the manifest, common files, clock-specific graphs/prefix caches, tokenizer, checksums and licenses. This migration does not modify graph or tensor bytes. Get authorized resources through your distributor.

For one model, place its package at `models/qnn248_qcs8550/manifest.json`; SDK/examples/Web discover it automatically. To keep both models, use separate package roots and pass the desired one explicitly with `--models`. Do not overwrite one model's manifest with the other model's manifest or add an unreferenced second clock directory.

## Model paths and validation

SDK, examples and Web share model discovery, anchored to this checkout. An explicit `--models` or `A8_MODELS` value must point directly at the manifest. Multiple immediate child packages require an explicit path. Discovery does not prove hardware compatibility or file integrity.

Keep every required graph, tensor, vocabulary, prefix cache, configuration and license. The Web application verifies manifest targets and checksums before loading. SDK 0.6.0 uses the single-file prefix-cache format; 0.4.x per-layer packages are incompatible. Model bytes are unchanged by the real-name SDK migration. Exact HF resource revisions are recorded in the internal release pairing.

## Layout

`manifest.json` lists the files of each audio clock; the SDK loads exactly these files and reports a clear error when
one is missing or does not match the model. The SDK, the examples and the web demo use the installed clocks only
(160 ms first).

```
qnn248_<chip>/                   one model package (the SDK's model directory)
├── manifest.json                the files of each audio clock (read by the SDK)
├── SHA256SUMS                   checksums of all files
├── common/                      shared by both audio clocks
│   ├── embedding.npy            token embedding table (CPU lookup)
│   ├── rotation.npy             rotation used when the 30 s context rolls
│   ├── mel_filters.npy          mel filterbank
│   ├── token_bytes.json         UTF-8 bytes of every token
│   ├── vad/                     end-of-turn heads (W.npy, b.npy, meta.json)
│   └── silero_vad.onnx          Silero VAD v5 (silence gate of the demo and of stream_file.py, not the SDK)
├── 160ms/                       one audio clock (80ms/ has the same files)
│   ├── frontend/                config.json (streaming configuration), rows_const.npy (constant audio rows)
│   ├── encoder/                 encoder + adapter (NPU, encrypted .aidem), prefix_kv.bin (constant prefix)
│   └── decoder/                 part_1_of_2 + part_2_of_2 (NPU, encrypted .aidem), prefix_kv_zh.bin, prefix_kv_en.bin
└── 80ms/
```

The NPU models are QNN context binaries, encrypted (`*.serialized.bin.aidem`); AidLite decrypts them when it loads
them. The constant prefixes (`prefix_kv*.bin`) are KV cache files in the layout of the Qualcomm Genie KV cache
(16-byte header, then the keys and the values of all layers), with float32 data.


## Licensing

Keep upstream model attribution and all applicable licenses, including the distributor's scoped model-adaptation terms, with the downloaded package. Required notices are part of the model resource, not a replacement for its files.
