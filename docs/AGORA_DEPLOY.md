# Agora deployment guide

Example configuration: streaming ASR / 160ms / QCS8550 / Ubuntu 22.04. Use standard Git, Python venv, the HF CLI, and project commands. No Agora CLI is required.

**One parameter file, sourced once, followed by normal commands.** Edit `agora.env` to select your workspace, repositories, SoC, operating system, directories, audio clock, and port. The model-file array declares the common files and selected target. The file contains parameters, not installation logic or credentials. Open a new terminal? Source it again before continuing.

The code and both model repositories are public. No SSH key or HF token is needed. Run commands one at a time and resolve errors before proceeding. Existing checkouts and updates are your responsibility; these commands do not reset your work. Choose a new workspace when migrating from an older Pandora checkout.

```text
~/my-asr-demo/                         # Choose your own name and location
├── agora.env                         # Deployment parameters
├── check-environment.py              # Checks only; no installation
├── audio8-asr-infinite-demo/          # Code and project .venv
└── models/audio8-160ms/               # Separate model package root
```

## 1. Check the environment

Define parameters once in agora.env. Source it in the current Bash terminal, then check the device. Later steps use the loaded variables.

### Create the configuration file: agora.env

```bash
mkdir -p "$HOME/my-asr-demo"
cat > "$HOME/my-asr-demo/agora.env" <<'AGORA_CONFIG'
export AGORA_WORKSPACE="$HOME/my-asr-demo"
export AGORA_CODE_REPO='https://github.com/APLUX-Agora/audio8-asr-infinite-demo.git'
export AGORA_CODE_DIR="$AGORA_WORKSPACE/audio8-asr-infinite-demo"
export AGORA_SOC='QCS8550'
export AGORA_UBUNTU='22.04'
export AGORA_PYTHON=python3
export AGORA_MODEL_REPO='APLUX-Agora/Audio8-ASR-Infinite-160ms'
export AGORA_MODEL_TARGET='qcs8550_qnn248'
export AGORA_MODELS_DIR="$AGORA_WORKSPACE/models/audio8-160ms"
export A8_CLOCK_MS=160
export A8_PORT=8765

AGORA_MODEL_FILES=(
  README.md models.json agora-model.json SHA256SUMS NOTICE "LICENSES/*"
  embedding.bin mel_filters.npy rotation.npy token_bytes.json tokenizer.json
  "frontend/*" "prefix/*" "semantic_vad/*" "targets/$AGORA_MODEL_TARGET/*"
)
AGORA_CONFIG
```

### Load the configuration and check the device

```bash
source "$HOME/my-asr-demo/agora.env"
mkdir -p "$AGORA_WORKSPACE"
curl -fL https://raw.githubusercontent.com/APLUX-Agora/audio8-asr-infinite-demo/main/tools/check-environment.py \
  -o "$AGORA_WORKSPACE/check-environment.py"
"$AGORA_PYTHON" "$AGORA_WORKSPACE/check-environment.py"
```

Agora fills the values from your selections. When using the repository directly, edit the [same template](../agora/agora.env.example) yourself. Use Bash because the model-file list is a Bash array. After changing parameters, source the file again and repeat the check. CHECKED means a static condition matches; fix FAILED items, install NEEDS_SETUP prerequisites in step 3, and review BSP/driver details for REVIEW items. The check does not prove inference compatibility.

## 2. Get the code

Clone the public repository for the first installation. Skip cloning if you already have a checkout; update it explicitly when needed.

```bash
git clone "$AGORA_CODE_REPO" "$AGORA_CODE_DIR"
cd "$AGORA_CODE_DIR"
```

Skip clone for an existing checkout. To update, enter the code directory, preserve or commit your changes, then run `git pull --ff-only`. If the destination already exists, use that checkout or choose a new workspace; do not delete user files just to make clone succeed.

## 3. Set up dependencies

Run commands in order. Resolve an error before continuing. Skip system dependencies that are already installed, and use a project venv.

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
cd "$AGORA_CODE_DIR"
"$AGORA_PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

The cloud board already has the shared AidLite/QNN runtime, so skip the runtime installation there. On your own device, follow the BSP/vendor requirements first. aid-pkg installs one package per command. If it reports a lock, wait for the current operation or contact the administrator; do not remove its lock file. System installation uses the device account's sudo privileges. Skip apt installation for existing tools. Select Python 3.10, 3.11, or 3.12 with matching venv support. A successful pip check does not prove earlier system installations succeeded.

## 4. Get model resources

A single target is about 3.3 GiB. Allow at least 8 GiB for the workspace. Public model downloads do not require authentication; repositories, target files, and paths are declared in the configuration.

```bash
.venv/bin/python -m pip install huggingface_hub
.venv/bin/hf download "$AGORA_MODEL_REPO" \
  --local-dir "$AGORA_MODELS_DIR" --include "${AGORA_MODEL_FILES[@]}"
```

The HF command downloads common files and only the selected target in one snapshot. Downloads can reuse the cache. Pass the root containing models.json to --models, not its targets directory. Keep 80ms and 160ms in separate directories. For optional integrity verification:

```bash
cd "$AGORA_MODELS_DIR"
sha256sum --ignore-missing -c SHA256SUMS
cd "$AGORA_CODE_DIR"
```

--ignore-missing checks present files and permits unselected SoC files to be absent; it does not prove package completeness. Web startup also checks required resources and hashes. Use native Git/HF revision options if you need a fixed historical version; the standard guide follows main.

## 5. Run a test

Choose either the 20-second file example or the Web Demo. The file example reports loading, transcription, and completion. Stop the foreground web service with Ctrl+C.

### 20-second file transcription

```bash
.venv/bin/python examples/python/transcribe_file.py examples/audio/quickstart_en_20s.wav \
  --models "$AGORA_MODELS_DIR" --clock-ms "$A8_CLOCK_MS" --lang en
```

### Web Demo: start when needed

```bash
demo/run.sh --models "$AGORA_MODELS_DIR" --port "$A8_PORT"
```

The file example prints [1/3] Loading model, [2/3] Transcribing, and [3/3] Transcription complete, followed by text and finish_reason/audio/wall. File text is returned on completion; vendor messages may appear between stages. Start with the 20-second sample, then optionally use the longer recordings.

The Web Demo checks resources and loads the model before opening its port. Wait for the listening message. On a cloud device, open http://localhost:8765/ in the remote desktop browser and enable sound in the Agora session page. On your own board, use localhost on the board or http://<board-ip>:8765/ from a computer on the same network; use the configured port if changed. Start begins transcription, Stop ends it, and Ctrl+C in the service terminal stops the server. File and Web tests are separate choices.

See [sample attribution](MEDIA_ATTRIBUTION.md#agora-quickstart-audio) for the 20-second audio source, license, and changes.

