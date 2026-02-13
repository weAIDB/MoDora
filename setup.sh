#!/bin/bash

# MoDora One-Click Setup Script

set -e

echo "🚀 Starting MoDora Setup..."

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
pip install --upgrade pip

# Install build tools first (needed for flash-attn and others)
echo "🛠️ Installing build tools..."
pip install --upgrade pip
pip install wheel setuptools packaging

# Install PyTorch and Transformers together to satisfy dependencies in one go
# We pin to 2.5.1 to stay within lmdeploy's supported range (<= 2.8.0)
echo "🔥 Installing Stable PyTorch (2.5.1) and Transformers (4.57.3)..."
pip uninstall -y torch torchvision torchaudio nvidia-nccl-cu11 nvidia-nccl-cu12 pynvml transformers triton
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 transformers==4.57.3 --index-url https://download.pytorch.org/whl/cu124

echo "📦 Installing MoDora-backend and remaining requirements..."
pip install nvidia-ml-py
pip install -e .
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Install FlashAttention last as it's the most likely to have environmental issues
echo "⚡ Attempting to install FlashAttention (this may take a while)..."
# Fix: [Errno 18] Invalid cross-device link by using a project-local TMPDIR
mkdir -p ./.pip_tmp
export TMPDIR=$PWD/.pip_tmp
if pip install flash-attn --no-build-isolation --no-cache-dir; then
    echo "✅ FlashAttention installed successfully."
else
    echo "⚠️ FlashAttention installation failed (possibly due to build environment)."
    echo "💡 The system will still work, but inference might be slower."
fi
rm -rf ./.pip_tmp

# Install PaddlePaddle for OCR support
echo "🐼 Installing PaddlePaddle GPU (v3.3.0) for OCR support..."
pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu130/

echo "🐼 Installing paddleocr and its dependencies..."
pip install paddleocr paddlex==3.4.2
# Fix: PPStructureV3 requires additional ocr dependencies in paddlex
pip install "paddlex[ocr]"

# Download LLM Model
echo "📥 Downloading Qwen model..."
# Use HF_ENDPOINT for faster download in China if needed
# export HF_ENDPOINT=https://hf-mirror.com
# Ensure huggingface_hub is installed for the download script
pip install huggingface_hub
python ../download_model.py

echo "✨ Backend setup complete!"
cd ..

# 4. Setup Frontend
echo "📦 Setting up Frontend (MoDora-frontend)..."
cd MoDora-frontend
npm install
cd ..

echo "✨ Setup complete! You can now run the project using ./run.sh"
echo "📝 Note: Don't forget to set your environment variables (e.g., MODORA_API_KEY) before running."
