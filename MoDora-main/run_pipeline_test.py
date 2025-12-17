import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from preprocess import preprocess
from cctree import build_tree
from constants import BASE_DIR, CACHE_DIR

# Define the list of files to process
input_files = ["100.pdf"]  # Only test 100.pdf

# Correct base directory for datasets
# Note: User's BASE_DIR in constants might be pointing to MMDA, let's check
# If BASE_DIR is .../datasets/MMDA, then we can just use "100.pdf"

print(f"Batch processing: {input_files}")
print(f"Base Directory: {BASE_DIR}")
print(f"Cache Directory: {CACHE_DIR}")

for input_file in input_files:
    source_path = os.path.join(BASE_DIR, input_file)
    # If BASE_DIR is not MMDA, try to append MMDA
    if not os.path.exists(source_path):
         source_path = os.path.join(os.path.dirname(BASE_DIR), "datasets/MMDA", input_file)
    
    # Calculate cache base properly
    # cache_base needs to be a directory where the folder "100" (basename of pdf) will be created inside
    cache_base = CACHE_DIR

    print(f"\n{'='*40}")
    print(f"Processing {input_file}...")
    print(f"Source Path: {source_path}")
    print(f"Cache Base: {cache_base}")
    print(f"{'='*40}")

    if not os.path.exists(source_path):
        print(f"Error: Source file not found at {source_path}")
        continue
    
    try:
        # Preprocess
        print(f"Running preprocess for {source_path}...")
        cp_dict = preprocess(source_path, cache_base)
        print(f"Preprocess result keys: {cp_dict.keys() if cp_dict else 'None'}")
        
        # Build Tree
        print(f"Building tree for {source_path}...")
        build_tree(source_path, cache_base)
        
        print(f"Successfully processed {input_file}")
        
    except Exception as e:
        print(f"Failed to process {input_file}: {e}")
        import traceback
        traceback.print_exc()

print("\nTest completed.")
