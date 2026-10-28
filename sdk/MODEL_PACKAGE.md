# Audio8 root models.json integration candidate

This contract is being exercised against actual HF downloads and the native, installed Python SDK and Demo. It is not yet the universal Pandora schema.

```json
{
  "format_version": 1,
  "model_name": "Audio8-ASR-Infinite-160ms",
  "audio_clock_ms": 160,
  "targets": [
    {"soc": "qcs8550", "qnn_version": "2.48", "directory": "targets/qcs8550_qnn248"}
  ],
  "tensor_metadata": {
    "embedding.bin": {"dtype": "float32-le", "shape": [151936, 2048], "layout": "row-major"}
  }
}
```

The index declares all available targets; a local installation may contain only one target's graphs. The fixed root paths and Audio8 graph names form this model's packaging convention, not a requirement for every future Pandora model. No separate shared-file registry, per-target descriptor, file-size field or hash field is used. SHA256SUMS owns hashes. Raw embedding metadata is required because the BIN has no header.

The SDK validates schema/model identity/clock and supported target metadata, selects one complete installed target (or A8_TARGET), resolves package-relative paths without permitting escape, and validates common resources and raw embedding byte length before allocating the inference engine. It does not infer hardware compatibility from the directory name. A8_TARGET is process-level startup configuration, not a per-request switch.

The same layout contract is used by native C/C++, the installed Python SDK, examples and Web preflight. Python discovery and `model_files(model_dir, clock_ms)` are public packaging helpers. Web uses the latter for required-file checksum checks, while inference stays in the native SDK. Missing/ambiguous/wrong-target input is rejected explicitly; no temporary legacy manifest or extra model directory is generated.

Existing manifest.json formats 1 and 2 are retained for old resources. If models.json is present it is authoritative; a broken new index is not hidden by silently using a legacy manifest. Schema version and raw tensor parameters must be checked before adding new fields or adopting this contract in another model.
