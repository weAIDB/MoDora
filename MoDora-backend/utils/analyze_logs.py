import json
import re
import sys
from collections import Counter
from pathlib import Path

def analyze_logs(log_dir):
    error_counts = Counter()
    log_files = Path(log_dir).rglob("*.log*")
    
    pattern = re.compile(r"generate_levels failed \(attempt 3/3\) for .*?: (.*)")
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "generate_levels failed (attempt 3/3)" not in line:
                        continue
                    try:
                        data = json.loads(line)
                        message = data.get("message", "")
                        match = pattern.search(message)
                        if match:
                            error = match.group(1)
                            # Simplify error messages to group similar ones
                            if "unterminated string literal" in error:
                                error = "SyntaxError: unterminated string literal"
                            elif "invalid syntax" in error:
                                error = "SyntaxError: invalid syntax"
                            elif "malformed node or string" in error:
                                error = "ValueError: malformed node or string"
                            elif "generate_levels result is not a list" in error:
                                error = "TypeError: result is not a list"
                            elif "HTTP" in error or "Connection" in error:
                                error = "Network/API Error"
                            
                            error_counts[error] += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
            
    print("Error Analysis Report:")
    print("-" * 30)
    for error, count in error_counts.most_common():
        print(f"{count:5d} | {error}")

if __name__ == "__main__":
    analyze_logs("./logs/20260205")
