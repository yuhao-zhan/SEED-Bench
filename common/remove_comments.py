import os
import tokenize
import io

def remove_comments_and_docstrings(source):
    """
    Removes # comments and docstrings from a Python source string.
    """
    io_obj = io.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0

    tokens = tokenize.generate_tokens(io_obj.readline)
    
    for toktype, ttext, (slineno, scol), (elineno, ecol), ltext in tokens:
        if slineno > last_lineno:
            last_col = 0
        if scol > last_col:
            out += " " * (scol - last_col)
        
        # Remove # comments
        if toktype == tokenize.COMMENT:
            pass
        # Remove docstrings (strings that are not part of an expression)
        elif toktype == tokenize.STRING:
            if prev_toktype == tokenize.INDENT or prev_toktype == tokenize.NEWLINE or prev_toktype == tokenize.NL:
                pass
            else:
                out += ttext
        else:
            out += ttext
            
        prev_toktype = toktype
        last_lineno = elineno
        last_col = ecol
        
    return out

def process_agent_files(tasks_dir):
    for root, dirs, files in os.walk(tasks_dir):
        if "agent.py" in files:
            file_path = os.path.join(root, "agent.py")
            print(f"Processing: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple removal of docstrings and comments using tokenize approach
            # Note: This logic is a bit sensitive, using a more standard approach below
            
            cleaned_content = []
            try:
                io_obj = io.StringIO(content)
                tokens = list(tokenize.generate_tokens(io_obj.readline))
                
                # We need to filter out COMMENT and docstring STRING tokens
                # A docstring is a STRING token that is preceded by NEWLINE, NL or INDENT
                # and followed by NEWLINE or NL.
                
                skip_indices = set()
                for i, tok in enumerate(tokens):
                    if tok.type == tokenize.COMMENT:
                        skip_indices.add(i)
                    if tok.type == tokenize.STRING:
                        # Check if it's likely a docstring
                        # If the previous token was a newline/indent and the next is a newline
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
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(res)
                    
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tasks_dir = os.path.join(base_dir, "tasks")
    process_agent_files(tasks_dir)
