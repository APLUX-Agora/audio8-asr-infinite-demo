# Agora deployment guide

Use normal Git, Git LFS, Python, and shell commands. Agora tasks and direct GitHub users share the same small configuration file. Each task uses an independent workspace and may optionally rent a cloud device.

## Get your configuration

- **Using Agora:** select your content and hardware, download the prefilled agora.env, and save it on the device. You do not need to copy a shell heredoc from the webpage.
- **Using GitHub directly:** download the [same template](../agora/agora.env.example), then edit its values in your preferred editor:

```bash
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/agora/agora.env.example -o agora.env
```

| Parameter | Meaning |
| --- | --- |
| AGORA_WORKSPACE | Your custom workspace path; use one directory per task |
| AGORA_SOC | Target SoC: QCS8550, QCS8625, IQ8, or IQ9 |

GitHub and HF repository URLs appear directly in the commands below. They are not environment variables. The code directory is workspace/code and model data is workspace/resources. The package owns its application defaults. Opening a new terminal? Source the saved agora.env again.

## 1. Check the environment

Save agora.env on the device. In the directory containing the file, source it and check the device. The global configuration declares common deployment information only.

### Load the configuration and check the device

```bash
source ./agora.env
mkdir -p "$AGORA_WORKSPACE"
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/tools/check-environment.py \
  -o "$AGORA_WORKSPACE/check-environment.py"
python3 "$AGORA_WORKSPACE/check-environment.py" --soc "$AGORA_SOC" --ubuntu 22.04
```

The example expects Ubuntu 22.04 for QCS8550/QCS8625. Use --ubuntu 24.04 for IQ8/IQ9. The script checks expected versus actual conditions and ensures the workspace is writable. It does not install packages or generate another configuration file. CHECKED means a static condition matches; fix FAILED items, install NEEDS_SETUP prerequisites in step 3, and review BSP/driver details for REVIEW items. Static checks do not qualify inference.

## 2. Get the code

Clone the code repository and selected branch or tag. Skip cloning for an existing checkout; update it explicitly when needed.

```bash
git clone https://github.com/APLUX-Agora/audio8-asr-infinite-demo.git "$AGORA_WORKSPACE/code"
cd "$AGORA_WORKSPACE/code"
```

An existing destination is not overwritten. Use the existing checkout or choose a different workspace. To update a checkout, preserve your edits and run git pull --ff-only in its code directory. Use native Git commands if you need another branch, tag, or exact commit.

## 3. Set up dependencies

Run commands one at a time. Resolve an error before continuing. Skip system prerequisites that are already installed.

### System runtime: preinstalled on the cloud device

```bash
sudo aid-pkg install aidlite-sdk
sudo aid-pkg install aidlite-qnn248
```

### System utilities: install if missing

```bash
sudo apt-get update
sudo apt-get install -y git ffmpeg libsndfile1 python3-venv
```

### Project virtual environment

```bash
cd "$AGORA_WORKSPACE/code"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --upgrade huggingface_hub
.venv/bin/python -m pip check
```

The cloud board already has AidLite/QNN; skip that installation there. On your own board, follow BSP/vendor prerequisites first. aid-pkg installs one package per command. Wait for an occupied package lock or contact the administrator; do not remove the lock. System installation requires the device account's sudo privileges. The selected system python3 must support venv and be CPython3.10/3.11/3.12. Stop at an installation error rather than assuming a later pip check validates earlier system operations.

## 4. Get model resources

The [160ms model repository](https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-160ms) keeps common resources and all hardware directories together on main. Use the official HF CLI installed in step 3:

```bash
cd "$AGORA_WORKSPACE/code"
.venv/bin/hf download APLUX-Agora/Audio8-ASR-Infinite-160ms --exclude "targets/*" --local-dir "$AGORA_WORKSPACE/resources"
.venv/bin/hf download APLUX-Agora/Audio8-ASR-Infinite-160ms --include "targets/$AGORA_SOC/*" --local-dir "$AGORA_WORKSPACE/resources"
```

The first command gets common resources; the second gets the selected hardware directory. For 80ms, replace both repository IDs with APLUX-Agora/Audio8-ASR-Infinite-80ms. The configuration stays the same. Public downloads need no login. Selected model files occupy about 3.3 GiB; allow at least 8 GiB for the workspace and dependencies. Re-running these commands reuses current files and retrieves missing or changed files. It does not delete unrelated files. No Git LFS, sparse checkout, or hardware branch is needed. See [model setup](MODEL_SETUP.md) and the [official HF CLI guide](https://huggingface.co/docs/huggingface_hub/en/guides/cli).

Optional integrity check:

```bash
cd "$AGORA_WORKSPACE/resources"
sha256sum -c SHA256SUMS --ignore-missing
cd "$AGORA_WORKSPACE/code"
```

Unselected hardware directories are intentionally absent. This verifies downloaded files but does not prove completeness by itself; application preflight also checks required files and hashes.

## 5. Run a test

Choose either the 20-second file example or the Web Demo. The model package declares its audio clock; no clock environment variable is needed.

### 20-second file transcription

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/quickstart_en_20s.wav \
  --models "$AGORA_WORKSPACE/resources" --lang en
```

### Web Demo: start when needed

```bash
demo/run.sh --models "$AGORA_WORKSPACE/resources" --port 8765
```

The SDK reads the audio clock from models.json when --clock-ms is omitted. The Web Demo also selects the clock available in that package. Its port is an application option, shown as --port 8765; change the command when another port is needed, rather than adding an Audio8 option to the global configuration.

The file example reports loading, transcribing, and completion, then prints text and finish_reason/audio/wall. Start with the 20-second sample. Longer files are optional. [Audio attribution](MEDIA_ATTRIBUTION.md#agora-quickstart-audio).

Wait for the web service to finish loading and print its listening address. On the cloud device, open http://localhost:8765/ in the remote desktop browser and enable sound in Agora. On your own board, use its browser or http://<board-ip>:8765/ from the same network. Start begins transcription; Stop ends it. Ctrl+C in the terminal stops the web service. File and Web tests are separate choices.

