from huggingface_hub import snapshot_download
import os
import sys
import argparse


def download_model():
    parser = argparse.ArgumentParser(description="Download a model from Hugging Face Hub")
    parser.add_argument(
        "--repo_id", 
        type=str, 
        default="Qwen/Qwen3-VL-8B-Instruct",
        help="The Hugging Face repository ID (e.g., Qwen/Qwen3-VL-8B-Instruct)"
    )
    parser.add_argument(
        "--local_dir", 
        type=str, 
        default="./MoDora-backend/models/Qwen3-VL-8B-Instruct",
        help="The local directory to save the model"
    )

    args = parser.parse_status = parser.parse_args()
    
    repo_id = args.repo_id
    model_dir = os.path.abspath(args.local_dir)

    print(f"🚀 Starting download for {repo_id}...")
    print(f"📁 Target directory: {model_dir}")

    try:
        # Ensure directory exists
        os.makedirs(model_dir, exist_ok=True)

        # Download model
        snapshot_download(
            repo_id=repo_id,
            local_dir=model_dir,
            local_dir_use_symlinks=False,  # Direct download
            resume_download=True,  # Support resuming
            ignore_patterns=[
                "*.pt",
                "*.bin",
            ],  # Ignore torch/legacy weights, keep safetensors
        )

        print(f"\n✅ Model successfully downloaded to: {model_dir}")
        print(f"💡 You can now configure this path in your local.json under 'model_instances'.")
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_model()
