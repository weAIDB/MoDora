from huggingface_hub import snapshot_download
import os
import sys

def download_model():
    # Model configuration
    repo_id = "Qwen/Qwen3-VL-8B-Instruct"  
    model_dir = os.path.abspath("./models/Qwen3-VL-8B-Instruct")
    
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
            resume_download=True,          # Support resuming
            ignore_patterns=["*.pt", "*.bin"], # Ignore torch/legacy weights, keep safetensors
        )
        
        print(f"✅ Model successfully downloaded to: {model_dir}")
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_model()
