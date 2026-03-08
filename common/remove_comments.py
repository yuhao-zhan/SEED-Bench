import os
import tokenize
import io
import re

def remove_comments_and_docstrings(source):
    """
    Removes # comments and docstrings from a Python source string and cleans up empty lines.
    """
    try:
        io_obj = io.StringIO(source)
        tokens = list(tokenize.generate_tokens(io_obj.readline))
        
        skip_indices = set()
        for i, tok in enumerate(tokens):
            if tok.type == tokenize.COMMENT:
                skip_indices.add(i)
            if tok.type == tokenize.STRING:
                # A docstring is a STRING token that is preceded by NEWLINE, NL or INDENT
                # and followed by NEWLINE or NL.
                if i > 0 and tokens[i-1].type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.ENCODING):
                    if i + 1 < len(tokens) and tokens[i+1].type in (tokenize.NEWLINE, tokenize.NL):
                        skip_indices.add(i)
        
        # Reconstruct
        res = ""
        last_lineno = 1
        last_col = 0
        
        for i, tok in enumerate(tokens):
            if i in skip_indices:
                continue
            
            if tok.start[0] > last_lineno:
                res += "\n" * (tok.start[0] - last_lineno)
                last_col = 0
            
            if tok.start[1] > last_col:
                res += " " * (tok.start[1] - last_col)
            
            res += tok.string
            last_lineno = tok.end[0]
            last_col = tok.end[1]
            
        # Clean up empty lines
        # 1. Strip trailing whitespace from each line
        lines = [line.rstrip() for line in res.splitlines()]
        res = "\n".join(lines)
        
        # 2. Collapse multiple blank lines into one
        res = re.sub(r'\n\s*\n\s*\n+', '\n\n', res)
        
        # 3. Remove blank lines followed by indentation (keeps blank lines before top-level things)
        res = re.sub(r'\n\s*\n([ ]+)', r'\n\1', res)
        
        # 4. Remove blank lines after lines ending with ':'
        res = re.sub(r':\s*\n\s*\n', ':\n', res)
        
        return res.strip() + "\n"
        
    except Exception as e:
        print(f"Failed to process: {e}")
        return source

def process_agent_files(tasks_dir):
    for root, dirs, files in os.walk(tasks_dir):
        if "agent.py" in files:
            file_path = os.path.join(root, "agent.py")
            print(f"Processing: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            cleaned_content = remove_comments_and_docstrings(content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tasks_dir = os.path.join(base_dir, "tasks")
    process_agent_files(tasks_dir)
