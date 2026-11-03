# Agora deployment guide

The global configuration format is shared by Agora and developers using GitHub. It contains only common deployment declarations. This project owns its model-file selection and application options; it does not turn them into global Agora parameters.

## Get your configuration

- **Using Agora:** select your content and hardware, download the prefilled agora.env, and save it on the device. You do not need to copy a shell heredoc from the webpage.
- **Using GitHub directly:** download the [same template](../agora/agora.env.example), then edit its values in your preferred editor:

```bash
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/agora/agora.env.example -o agora.env
```

| Parameter | Meaning |
| --- | --- |
| AGORA_WORKSPACE | Custom workspace path |
| AGORA_CONTENT_ID | Selected content identifier |
| AGORA_CODE_REPO | Code repository URL |
| AGORA_CODE_REF | Code branch or tag, main by default |
| AGORA_RESOURCE_REPO | HF resource repository |
| AGORA_RESOURCE_REF | HF resource revision, main by default |
| AGORA_SOC | Target SoC |
| AGORA_OS | Operating system ID, such as ubuntu |
| AGORA_OS_VERSION | Operating system version |

Code always goes to workspace/code; the selected model package goes to workspace/resources. These directories are conventions, not additional configuration fields. Use one workspace per content/hardware combination. For the 80ms variant, select its resource repository; no separate audio-clock parameter is necessary. If you change hardware or model variant, use a fresh workspace to avoid mixing target files.

The code and resources are public. No GitHub SSH key or HF token is needed. Open a new terminal? Source the same saved agora.env before continuing. Run normal commands in order, and fix a failed command before executing the next one.

## 1. Check the environment

Save agora.env on the device. In the directory containing the file, source it and check the device. The global configuration declares common deployment information only.

### Load the configuration and check the device

```bash
source ./agora.env
mkdir -p "$AGORA_WORKSPACE"
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/tools/check-environment.py \
  -o "$AGORA_WORKSPACE/check-environment.py"
python3 "$AGORA_WORKSPACE/check-environment.py"
```

The script checks expected versus actual conditions and ensures the workspace is writable. It does not install packages or generate another configuration file. CHECKED means a static condition matches; fix FAILED items, install NEEDS_SETUP prerequisites in step 3, and review BSP/driver details for REVIEW items. Static checks do not qualify inference.

## 2. Get the code

Clone the code repository and selected branch or tag. Skip cloning for an existing checkout; update it explicitly when needed.

```bash
git clone --branch "$AGORA_CODE_REF" "$AGORA_CODE_REPO" "$AGORA_WORKSPACE/code"
cd "$AGORA_WORKSPACE/code"
```

An existing destination is not overwritten. Use the existing checkout or choose a different workspace. To update a checkout, preserve your edits and run git pull --ff-only in its code directory. AGORA_CODE_REF is a branch or tag for this clone command; use native Git commands separately if you need an exact commit.

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
.venv/bin/python -m pip check
```

The cloud board already has AidLite/QNN; skip that installation there. On your own board, follow BSP/vendor prerequisites first. aid-pkg installs one package per command. Wait for an occupied package lock or contact the administrator; do not remove the lock. System installation requires the device account's sudo privileges. The selected system python3 must support venv and be CPython3.10/3.11/3.12. Stop at an installation error rather than assuming a later pip check validates earlier system operations.

## 4. Get model resources

The project resource declaration selects the files for AGORA_SOC. The global configuration does not contain file lists or Audio8 runtime parameters. A target is about 3.3 GiB; allow at least 8 GiB for the workspace.

```bash
source agora/resources.env
.venv/bin/python -m pip install huggingface_hub
.venv/bin/hf download "$AGORA_RESOURCE_REPO" --revision "$AGORA_RESOURCE_REF" \
  --local-dir "$AGORA_WORKSPACE/resources" --include "${AUDIO8_DOWNLOAD_PATTERNS[@]}"
```

Source agora/resources.env from the code checkout. This project-owned file maps AGORA_SOC to an Audio8 target and maintains the HF include patterns. It does not install anything or change global declarations. Unsupported SoCs are rejected; do not continue downloading after that error.

The standard HF command downloads common files and the selected target into one package root. No unpacking or manual moves are needed. Pass workspace/resources, not its targets subdirectory, to --models. For optional hash verification:

```bash
cd "$AGORA_WORKSPACE/resources"
sha256sum --ignore-missing -c SHA256SUMS
cd "$AGORA_WORKSPACE/code"
```

--ignore-missing verifies present files and allows unselected target files to be absent; it does not prove completeness. Web startup checks required resources and hashes. AGORA_RESOURCE_REF supports a branch, tag, or immutable HF commit.

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

