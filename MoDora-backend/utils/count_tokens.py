import json
import glob
from pathlib import Path
import tiktoken

def count_tokens():
    # Use cache_v4 as seen in previous commands
    base_dir = Path("/home/yukai/project/MoDora/MoDora-backend/cache_v4")
    # Also check cache_v5 since user mentioned it in first message
    base_dir_v5 = Path("/home/yukai/project/MoDora/MoDora-backend/cache_v5")
    
    co_files = list(base_dir.rglob("*/co.json")) + list(base_dir_v5.rglob("*/co.json"))
    
    print(f"Found {len(co_files)} co.json files")
    
    # Use cl100k_base encoding (common for GPT-4/Gemini approximation)
    enc = tiktoken.get_encoding("cl100k_base")
    
    max_tokens = 0
    max_file = ""
    max_title_count = 0
    
    token_counts = []
    
    for co_path in co_files:
        try:
            with open(co_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Simulate the title list extraction logic from hierarchy.py
            # text_components = [co for co in cp.body if co.type == "text"]
            # located = [co for co in text_components if co.location]
            # title_list = [co.title for co in located]
            
            titles = []
            if "body" in data:
                for item in data["body"]:
                    if item.get("type") == "text" and item.get("location"):
                        title = item.get("title", "")
                        if title:
                            titles.append(title)
            
            if not titles:
                continue
                
            # Calculate tokens for the raw list string representation
            # The prompt uses: level_title_prompt.format(raw_list=title_list)
            # So we approximate the token count of the stringified list
            list_str = str(titles)
            tokens = len(enc.encode(list_str))
            
            token_counts.append(tokens)
            
            if tokens > max_tokens:
                max_tokens = tokens
                max_file = str(co_path)
                max_title_count = len(titles)
                
        except Exception as e:
            # print(f"Error processing {co_path}: {e}")
            pass
            
    token_counts.sort()
    
    print(f"\nToken Analysis Report (Approximate using cl100k_base):")
    print(f"Total files analyzed: {len(token_counts)}")
    print(f"Max tokens found: {max_tokens} (in {max_file})")
    print(f"Max title count: {max_title_count}")
    
    if token_counts:
        p50 = token_counts[len(token_counts)//2]
        p90 = token_counts[int(len(token_counts)*0.9)]
        p95 = token_counts[int(len(token_counts)*0.95)]
        p99 = token_counts[int(len(token_counts)*0.99)]
        
        print(f"Median tokens (P50): {p50}")
        print(f"P90 tokens: {p90}")
        print(f"P95 tokens: {p95}")
        print(f"P99 tokens: {p99}")

    # Estimate output tokens needed
    # Output is essentially the input list with '#' characters added
    # So output tokens ~= input tokens + overhead
    print(f"\nEstimated Output Token Requirement (Input + 20% buffer): {int(max_tokens * 1.2)}")
    print(f"Is 8192 sufficient? {'YES' if 8192 > max_tokens * 1.5 else 'NO (RISKY)'}")

if __name__ == "__main__":
    count_tokens()
