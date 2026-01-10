import os
import shutil

def clear_mmda_cache():
    """
    Clears all files and subdirectories in the cache/MMDA directory.
    """
    # Get the absolute path to the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the cache/MMDA directory
    target_dir = os.path.join(script_dir, 'cache', 'MMDA')

    print(f"Target directory: {target_dir}")

    if not os.path.exists(target_dir):
        print(f"Directory {target_dir} does not exist. Creating it...")
        os.makedirs(target_dir, exist_ok=True)
        return

    # Safety check: ensure we are operating on the intended directory
    if not target_dir.endswith(os.path.join('cache', 'MMDA')):
        print("Safety check failed. Path does not seem to be the correct cache/MMDA directory.")
        return

    print("Starting to clear cache...")
    try:
        # Get list of all files and directories
        items = os.listdir(target_dir)
        if not items:
            print("Directory is already empty.")
            return

        for item in items:
            item_path = os.path.join(target_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                    print(f"Deleted file: {item}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"Deleted directory: {item}")
            except Exception as e:
                print(f"Failed to delete {item_path}. Reason: {e}")
        
        print("Cache cleared successfully.")
        
    except Exception as e:
        print(f"Error accessing directory: {e}")

if __name__ == "__main__":
    clear_mmda_cache()
