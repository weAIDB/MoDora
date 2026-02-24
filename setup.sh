#!/bin/bash

# MoDora One-Click Setup Script

set -e

echo "🚀 Starting MoDora setup..."
ROOT_DIR="$(pwd)"
CONFIG_PATH="$ROOT_DIR/MoDora-backend/configs/local.json"
EXAMPLE_CONFIG_PATH="$ROOT_DIR/MoDora-backend/configs/local.example.json"
LOCAL_MODEL_DIR="MoDora-backend/models"

if [ ! -f "$CONFIG_PATH" ]; then
    echo "📄 Configuration file not found. Creating it from template..."
    if [ -f "$EXAMPLE_CONFIG_PATH" ]; then
        cp "$EXAMPLE_CONFIG_PATH" "$CONFIG_PATH"
        echo "✅ local.json created."
    else
        echo "❌ Error: Could not find template config: $EXAMPLE_CONFIG_PATH"
        exit 1
    fi
fi

MODEL_INSTANCES_FILE="$(mktemp)"
PIPELINES_FILE="$(mktemp)"
MODEL_INSTANCE_IDS=()
MODEL_INSTANCE_TYPES=()
LOCAL_INSTANCE_PATHS=()
LOCAL_INSTANCE_DIRS=()
LOCAL_INSTANCE_NAMES=()
HAS_LOCAL_INSTANCE=0
INSTANCE_COUNT=0
LOCAL_INSTANCE_COUNT=0
LOCAL_BASE_PORT=9001

while true; do
    if [ "$INSTANCE_COUNT" -eq 0 ]; then
        read -p "Add a model instance now? (Y/n): " ADD_MORE
        if [ "$ADD_MORE" = "n" ] || [ "$ADD_MORE" = "N" ] || [ "$ADD_MORE" = "no" ] || [ "$ADD_MORE" = "NO" ]; then
            echo "You must add at least one model instance."
            continue
        fi
    else
        read -p "Add another model instance? (y/N): " ADD_MORE
        if [ "$ADD_MORE" = "n" ] || [ "$ADD_MORE" = "N" ] || [ "$ADD_MORE" = "no" ] || [ "$ADD_MORE" = "NO" ] || [ -z "$ADD_MORE" ]; then
            break
        fi
    fi

    INSTANCE_TYPE=""
    while true; do
        read -p "Model type (local/remote): " TYPE_INPUT
        if [ "$TYPE_INPUT" = "local" ] || [ "$TYPE_INPUT" = "LOCAL" ]; then
            INSTANCE_TYPE="local"
            HAS_LOCAL_INSTANCE=1
            break
        fi
        if [ "$TYPE_INPUT" = "remote" ] || [ "$TYPE_INPUT" = "REMOTE" ]; then
            INSTANCE_TYPE="remote"
            break
        fi
        echo "Invalid input. Please enter 'local' or 'remote'."
    done

    MODEL_NAME=""
    BASE_URL=""
    API_KEY=""
    INSTANCE_PORT=""
    INSTANCE_DEVICE=""
    if [ "$INSTANCE_TYPE" = "local" ]; then
        read -p "Local model storage directory (relative, default: $LOCAL_MODEL_DIR): " LOCAL_DIR
        if [ -z "$LOCAL_DIR" ]; then
            LOCAL_DIR="$LOCAL_MODEL_DIR"
        fi
        while true; do
            read -p "Local model name (HuggingFace repo id): " MODEL_NAME
            if [ -n "$MODEL_NAME" ]; then
                break
            fi
            echo "Model name is required."
        done
        DEFAULT_PORT=$((LOCAL_BASE_PORT + LOCAL_INSTANCE_COUNT))
        read -p "Local server port (default: $DEFAULT_PORT): " INSTANCE_PORT
        if [ -z "$INSTANCE_PORT" ]; then
            INSTANCE_PORT="$DEFAULT_PORT"
        fi
        read -p "Local device (optional, e.g., 0 or 0,1): " INSTANCE_DEVICE
        LOCAL_INSTANCE_COUNT=$((LOCAL_INSTANCE_COUNT + 1))
    else
        read -p "Remote model_name: " MODEL_NAME
        read -p "Remote base_url: " BASE_URL
        read -s -p "Remote api_key: " API_KEY
        echo ""
    fi

    INSTANCE_ID="$MODEL_NAME"
    if [ "$INSTANCE_TYPE" = "local" ]; then
        MODEL_VALUE="$LOCAL_DIR/$MODEL_NAME"
    else
        MODEL_VALUE="$MODEL_NAME"
    fi
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$INSTANCE_ID" "$INSTANCE_TYPE" "$MODEL_VALUE" "$BASE_URL" "$API_KEY" "$INSTANCE_PORT" "$INSTANCE_DEVICE" >> "$MODEL_INSTANCES_FILE"
    MODEL_INSTANCE_IDS+=("$INSTANCE_ID")
    MODEL_INSTANCE_TYPES+=("$INSTANCE_TYPE")
    if [ "$INSTANCE_TYPE" = "local" ]; then
        LOCAL_INSTANCE_PATHS+=("$MODEL_VALUE")
        LOCAL_INSTANCE_DIRS+=("$LOCAL_DIR")
        LOCAL_INSTANCE_NAMES+=("$MODEL_NAME")
    else
        LOCAL_INSTANCE_PATHS+=("")
        LOCAL_INSTANCE_DIRS+=("")
        LOCAL_INSTANCE_NAMES+=("")
    fi
    INSTANCE_COUNT=$((INSTANCE_COUNT + 1))
done

MODULE_KEYS=("enrichment" "levelGenerator" "metadataGenerator" "retriever" "qaService")
echo "Select model instance for each module:"
for MODULE_KEY in "${MODULE_KEYS[@]}"; do
    echo "Module: $MODULE_KEY"
    for idx in "${!MODEL_INSTANCE_IDS[@]}"; do
        echo "$((idx + 1))) ${MODEL_INSTANCE_IDS[$idx]} (${MODEL_INSTANCE_TYPES[$idx]})"
    done
    read -p "Select instance number (default: 1): " CHOICE
    if [ -z "$CHOICE" ]; then
        CHOICE=1
    fi
    if ! [[ "$CHOICE" =~ ^[0-9]+$ ]] || [ "$CHOICE" -lt 1 ] || [ "$CHOICE" -gt "${#MODEL_INSTANCE_IDS[@]}" ]; then
        CHOICE=1
    fi
    SELECTED_ID="${MODEL_INSTANCE_IDS[$((CHOICE - 1))]}"
    printf "%s\t%s\n" "$MODULE_KEY" "$SELECTED_ID" >> "$PIPELINES_FILE"
done

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    exit 1
fi

# 2. Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed."
    exit 1
fi

# 3. Setup Backend
echo "📦 Setting up Backend (MoDora-backend)..."
cd MoDora-backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created."
fi
source venv/bin/activate
pip install --upgrade pip wheel setuptools packaging

# Install PyTorch with CUDA support first
# We pin to 2.5.1 to stay within lmdeploy's supported range (<= 2.8.0)
echo "🔥 Installing Stable PyTorch (2.5.1), Transformers (4.57.3) and LMDeploy (0.12.0)..."
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 transformers==4.57.3 

# Install PaddlePaddle for OCR support
echo "📦 Installing PaddlePaddle GPU (v3.3.0) for OCR support..."
pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu130/

echo "📦 Installing MoDora-backend and remaining requirements..."
pip install -e .
# Fix: PPStructureV3 requires additional ocr dependencies in paddlex
pip install "paddlex[ocr]"

# Install FlashAttention last as it's the most likely to have environmental issues
echo "⚡ Attempting to install FlashAttention (this may take a while)..."
mkdir -p ./.pip_tmp
export TMPDIR=$PWD/.pip_tmp
if pip install flash-attn --no-build-isolation --no-cache-dir; then
    echo "✅ FlashAttention installed successfully."
else
    echo "⚠️ FlashAttention installation failed (inference might be slower)."
fi
rm -rf ./.pip_tmp

if [ "$HAS_LOCAL_INSTANCE" -eq 1 ]; then
    for idx in "${!MODEL_INSTANCE_TYPES[@]}"; do
        if [ "${MODEL_INSTANCE_TYPES[$idx]}" != "local" ]; then
            continue
        fi
        MODEL_PATH="${LOCAL_INSTANCE_PATHS[$idx]}"
        MODEL_DIR_REL="${LOCAL_INSTANCE_DIRS[$idx]}"
        MODEL_NAME="${LOCAL_INSTANCE_NAMES[$idx]}"
        TARGET_ABS="$ROOT_DIR/$MODEL_PATH"
        if [ -d "$TARGET_ABS" ]; then
            echo "✅ Local model already exists: $MODEL_PATH"
            continue
        fi
        echo "📥 Downloading model to $MODEL_DIR_REL/$MODEL_NAME..."
        MODEL_DIR="$TARGET_ABS" MODEL_REPO_ID="$MODEL_NAME" python ../download_model.py
    done
fi

export MODORA_CONFIG_PATH="$CONFIG_PATH"
export MODORA_MODEL_INSTANCES_FILE="$MODEL_INSTANCES_FILE"
export MODORA_PIPELINES_FILE="$PIPELINES_FILE"
python - <<'PY'
import json
import os

config_path = os.environ.get("MODORA_CONFIG_PATH")
instances_file = os.environ.get("MODORA_MODEL_INSTANCES_FILE")
pipelines_file = os.environ.get("MODORA_PIPELINES_FILE")

if not config_path:
    raise SystemExit("missing config path")

with open(config_path, "r", encoding="utf-8") as f:
    data = json.load(f)

model_instances: dict[str, dict[str, str | None]] = {}
first_local: dict[str, str | None] | None = None
first_remote: dict[str, str | None] | None = None

if instances_file and os.path.exists(instances_file):
    with open(instances_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            instance_id, instance_type, model_name, base_url, api_key = parts[:5]
            port_raw = parts[5] if len(parts) > 5 else ""
            device_raw = parts[6] if len(parts) > 6 else ""
            if instance_type == "local":
                base_url = ""
                api_key = ""
            port = None
            if port_raw:
                try:
                    port = int(port_raw)
                except Exception:
                    port = None
            payload = {
                "type": instance_type,
                "model": model_name or None,
                "base_url": base_url or None,
                "api_key": api_key or None,
                "port": port,
                "device": device_raw or None,
            }
            model_instances[instance_id] = payload
            if instance_type == "local" and first_local is None:
                first_local = payload
            if instance_type == "remote" and first_remote is None:
                first_remote = payload

data["model_instances"] = model_instances

if first_local:
    data["llm_local_model"] = first_local["model"]
    data["llm_local_base_url"] = first_local["base_url"]
    data["llm_local_api_key"] = first_local["api_key"] or "local"
    if first_local.get("port") is not None:
        data["llm_local_port"] = first_local["port"]
    if first_local.get("device") is not None:
        data["llm_local_cuda_visible_devices"] = first_local["device"]

if first_remote:
    data["api_model"] = first_remote["model"]
    data["api_base"] = first_remote["base_url"]
    data["api_key"] = first_remote["api_key"]

pipelines: dict[str, dict[str, str]] = {}
if pipelines_file and os.path.exists(pipelines_file):
    with open(pipelines_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            module_key, instance_id = parts[:2]
            pipelines[module_key] = {"modelInstance": instance_id}

data["ui_settings"] = {
    "schemaVersion": 3,
    "pipelines": pipelines,
}

if first_remote:
    data["api_model"] = first_remote.get("model")
    data["api_base"] = first_remote.get("base_url")
    data["api_key"] = first_remote.get("api_key")
if first_local:
    data["llm_local_model"] = first_local.get("model")
    data["llm_local_base_url"] = first_local.get("base_url")
    api_key = first_local.get("api_key")
    if api_key:
        data["llm_local_api_key"] = api_key

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
PY

rm -f "$MODEL_INSTANCES_FILE" "$PIPELINES_FILE"

echo "✨ Backend setup complete!"
cd ..

# 4. Setup Frontend
echo "📦 Setting up Frontend (MoDora-frontend)..."
cd MoDora-frontend
npm install
cd ..

echo "✨ Setup complete! You can now run the project using ./run.sh"
echo "📝 Note: Remember to set your environment variables (e.g., MODORA_API_KEY) before running."
