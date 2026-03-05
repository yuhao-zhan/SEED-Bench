import os
import tokenize
import io
from pathlib import Path

def remove_comments_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    
    last_lineno = -1
    last_col = 0
    
    out = ""
    try:
        for tok in tokens:
            tok_type, tok_string, (start_line, start_col), (end_line, end_col), _ = tok
            
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                out += (" " * (start_col - last_col))
                
            if tok_type == tokenize.COMMENT:
                pass # Skip comment token
            else:
                out += tok_string
                
            last_lineno = end_line
            last_col = end_col
    except tokenize.TokenError as e:
        print(f"Token error in {file_path}: {e}")
        return
        
    # Remove trailing whitespace from each line which might be left over
    clean_lines = [line.rstrip() for line in out.splitlines()]
    
    # Optional: Remove completely empty lines if you want the code to be compact
    # clean_lines = [line for line in clean_lines if line.strip() != ""]
    
    final_out = "\n".join(clean_lines) + "\n"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_out)

if __name__ == "__main__":
    # Target directory
    tasks_dir = Path("/Users/zhanyuxiao/Desktop/GitHub/SEED-Bench/tasks")
    
    # Find all agent.py files recursively
    agent_files = list(tasks_dir.rglob("agent.py"))
    
    if not agent_files:
        print("No agent.py files found in tasks directory.")
    else:
        for file in agent_files:
            print(f"Removing comments from: {file}")
            remove_comments_from_file(file)
        print("Successfully removed comments from all agent.py files!")
