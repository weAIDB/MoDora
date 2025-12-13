import os
from preprocess import preprocess
from cctree import build_tree
from constants import BASE_DIR, CACHE_DIR

# Define the list of files to process
input_files = ["1.pdf", "2.pdf", "3.pdf"]

# Calculate cache directory to match main.py logic
cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))

print(f"Batch processing: {input_files}")
print(f"Base Directory: {BASE_DIR}")
print(f"Cache Directory: {cache_base}")

for input_file in input_files:
    source_path = os.path.join(BASE_DIR, input_file)
    print(f"\n{'='*40}")
    print(f"Processing {input_file}...")
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

print("\nBatch processing completed.")
print("You can now start the backend server via 'python main.py' and request these files.")
