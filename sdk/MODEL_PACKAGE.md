# Configurable models.json package

The root models.json is the interface between HF resources and the native/Python SDK. Version2 declares all paths; no resource registry of implicit filenames or per-target target.json is required.

```json
{
  "format_version": 2,
  "model_name": "Audio8-ASR-Infinite-160ms",
  "audio_clock_ms": 160,
  "targets": [
    {
      "soc": "qcs8550",
      "qnn_version": "2.48",
      "directory": "targets/qcs8550_qnn248",
      "files": {
        "encoder": "targets/qcs8550_qnn248/encoder.aidem",
        "adapter": "targets/qcs8550_qnn248/adapter.aidem",
        "decoder_1": "targets/qcs8550_qnn248/decoder_1.aidem",
        "decoder_2": "targets/qcs8550_qnn248/decoder_2.aidem"
      }
    }
  ],
  "resources": {
    "frontend_config": "frontend/config.json",
    "audio_constants": "frontend/rows_const.npy",
    "mel_filters": "mel_filters.npy",
    "vocabulary": "token_bytes.json",
    "tokenizer": "tokenizer.json",
    "rotation": "rotation.npy",
    "token_vectors": {
      "path": "embedding.bin",
      "dtype": "float32-le",
      "shape": [
        151936,
        2048
      ],
      "layout": "row-major"
    },
    "prefix": {
      "encoder": "prefix/encoder.bin",
      "decoder_zh": "prefix/decoder_zh.bin",
      "decoder_en": "prefix/decoder_en.bin"
    },
    "semantic_vad": {
      "weight": "semantic_vad/weight.npy",
      "bias": "semantic_vad/bias.npy",
      "config": "semantic_vad/config.json"
    }
  }
}
```

All paths are relative to the model-package root, including target graph paths. Resource keys express semantic purposes rather than filenames. Ordinary resources use strings; token_vectors additionally declares its raw binary representation. Hashes are maintained exclusively in SHA256SUMS. Target directory is an explicitly configured grouping used for selective download/completeness; graphs must remain within that directory. Renaming common files, graph files or the target directory only requires updating configuration and checksums.

A local installation may download only one declared target. The SDK validates model identity, audio clock and supported SoC/QNN metadata; selects one complete target or an explicit A8_TARGET; rejects missing roles, invalid/escaping paths, ambiguous targets and incorrect raw-vector data; then loads all files from the configuration. There are no silent filename fallbacks. A8_TARGET is process-level startup configuration, not a per-request control, and it is not automatic hardware identification.

The same semantics are exercised in native C++, installed Python SDK, examples and Web preflight. Public model_files(model_dir, clock_ms) supplies resolved runtime paths to application preflight without implementing inference. C ABI and task APIs are unchanged. Legacy manifest formats1/2 are supported for old assets; prototype models.json format1 is intentionally rejected rather than silently ignoring its absent path declarations.
