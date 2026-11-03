# Agora deployment guide

Use normal Git, Python, and shell commands. Agora and direct GitHub users follow
the same steps. Each task uses an independent workspace.

## 1. Check the environment

Set these two variables in the device terminal. The workspace path/name is yours;
Agora fills in the selected SoC. No configuration file transfer is required.

```bash
export AGORA_WORKSPACE="$HOME/my-asr-demo"
export AGORA_SOC='QCS8550'
```

```bash
mkdir -p "$AGORA_WORKSPACE" &&
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/tools/check-environment.py \
  -o "$AGORA_WORKSPACE/check-environment.py" &&
python3 "$AGORA_WORKSPACE/check-environment.py" --soc "$AGORA_SOC" --ubuntu 22.04
```

Use Ubuntu 22.04 for QCS8550/QCS8625 and 24.04 for IQ8/IQ9 in this demo.
`CHECKED` matches an expected static condition. Stop at `FAILED`, correct the
hardware/system selection or workspace problem, then rerun the check. Resolve
`NEEDS_SETUP` in step 3 and confirm `REVIEW` items against the board documentation.
Static checks do not qualify model inference. Opening a new terminal? Set the
same two variables again before activating the project's venv.

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
source .venv/bin/activate
pip install -r requirements.txt
pip install --upgrade huggingface_hub
pip check
```

Keep using this activated terminal for the remaining steps. In a new terminal, set the same two variables from step 1, change to "$AGORA_WORKSPACE/code", and run source .venv/bin/activate before continuing.

The cloud board already has AidLite/QNN; skip that installation there. On your own board, follow BSP/vendor prerequisites first. aid-pkg installs one package per command. Wait for an occupied package lock or contact the administrator; do not remove the lock. System installation requires the device account's sudo privileges. The selected system python3 must support venv and be CPython3.10/3.11/3.12. Stop at an installation error rather than assuming a later pip check validates earlier system operations.

## 4. Get model resources

The [160ms model repository](https://huggingface.co/APLUX-Agora/Audio8-ASR-Infinite-160ms) keeps common resources and all hardware directories together on main. Use the official HF CLI installed in step 3:

### Download common resources

```bash
hf download APLUX-Agora/Audio8-ASR-Infinite-160ms \
  --exclude "targets/*" --local-dir "$AGORA_WORKSPACE/resources"
```

### Download the SoC model

```bash
hf download APLUX-Agora/Audio8-ASR-Infinite-160ms \
  --include "targets/$AGORA_SOC/*" --local-dir "$AGORA_WORKSPACE/resources"
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
python examples/python/transcribe_file.py examples/audio/quickstart_en_20s.wav \
  --models "$AGORA_WORKSPACE/resources" --lang en
```

### Web Demo: start when needed

```bash
demo/run.sh --models "$AGORA_WORKSPACE/resources" --port 8765
```

The SDK reads the audio clock from models.json when --clock-ms is omitted. The Web Demo also selects the clock available in that package. Its port is an application option, shown as --port 8765; change the command when another port is needed, rather than adding an Audio8 option to the global configuration.

The file example reports loading, transcribing, and completion, then prints text and finish_reason/audio/wall. Start with the 20-second sample. Longer files are optional. [Audio attribution](MEDIA_ATTRIBUTION.md#agora-quickstart-audio).

Wait for the web service to finish loading and print its listening address. On the cloud device, open http://localhost:8765/ in the remote desktop browser and enable sound in Agora. On your own board, use its browser or http://<board-ip>:8765/ from the same network. Start begins transcription; Stop ends it. Ctrl+C in the terminal stops the web service. File and Web tests are separate choices.

