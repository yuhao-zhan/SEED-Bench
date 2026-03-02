"""Utility functions for evaluation scripts"""
import os
import json
import glob
import re
from typing import Optional, Dict, Any, List, Tuple


def is_cuda_oom(exc: BaseException) -> bool:
    """Check if an exception is CUDA out of memory. Used to fail fast instead of continuing."""
    if exc is None:
        return False
    msg = str(exc).lower()
    if "out of memory" in msg or "cuda out of memory" in msg or "outofmemoryerror" in msg:
        return True
    # Check exception chain (e.g. RuntimeError wrapping torch.cuda.OutOfMemoryError)
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    return cause is not None and is_cuda_oom(cause)


def get_model_identifier(model_type: str, model_name: str) -> str:
    """Generate model identifier from model type and name"""
    if model_type in ['local', 'huggingface']:
        if os.path.isdir(model_name):
            return os.path.basename(model_name)
        elif model_name:
            return model_name.replace('/', '_')
        else:
            return 'local_model'
    else:
        return f"{model_type}_{model_name}".replace('/', '_')


def get_run_suffix(run_num: int) -> str:
    """Get run suffix (1st, 2nd, 3rd, etc.)"""
    if run_num == 1:
        return '1st'
    elif run_num == 2:
        return '2nd'
    elif run_num == 3:
        return '3rd'
    else:
        return f'{run_num}th'


def extract_run_number_from_filename(filename: str) -> Optional[int]:
    """Extract run number from log filename (e.g., 'all_1st_pass_20260208.json' -> 1)"""
    import re
    # 放宽匹配条件，只要包含 _1st_、_2nd_ 即可识别，不再强制要求后面的 _pass_
    match = re.search(r'_(\d+)(?:st|nd|rd|th)_', filename)
    if match:
        return int(match.group(1))
    return None


def get_gif_path(gif_dir: str, context: str, iteration: int) -> str:
    """Generate GIF file path"""
    filename = f"{context}_{iteration}.gif"
    return os.path.join(gif_dir, filename)


def get_gif_base_dir() -> str:
    """Get base directory for GIF files"""
    return "/home/test/test1709/THUNLP/DaVinciBench/2D_exploration/gif"


def get_evaluation_results_dir() -> str:
    """Get base directory for evaluation results"""
    script_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(script_dir, "evaluation_results")


def run_is_complete(task_name: str, model_type: str, model_name: str, method: str,
                    context: str, run_number: int, mutated_task_name: Optional[str] = None) -> bool:
    """Check if a single run (1st/2nd/3rd pass) has the result JSON. Only JSON is required; GIF is optional."""
    model_identifier = get_model_identifier(model_type, model_name)
    json_base_dir = get_evaluation_results_dir()
    json_base_path = os.path.join(json_base_dir, task_name, model_identifier, method)

    run_suffix = get_run_suffix(run_number)
    json_exists = False
    if os.path.exists(json_base_path):
        # 只要前缀匹配 {context}_{run_suffix}_ 即可 (如 all_1st_)，忽略后面的日期和后缀
        json_pattern = os.path.join(json_base_path, f"{context}_{run_suffix}_*")
        json_exists = bool(glob.glob(json_pattern))
    return bool(json_exists)


def collect_incomplete_runs(
    task_list: list,
    model_type: str,
    model_name: str,
    method: str,
    context: str = 'previous',
) -> list:
    """Collect (task_name, run_number) for runs that are not complete (missing JSON).
    Returns list of (task_name, run_number). For tree_of_thought and science_codeevolve only run 1 (1st pass) is considered."""
    out: List[Tuple[str, int]] = []
    run_nums = [1] if method in ('tree_of_thought', 'science_codeevolve', 'alpha_evolve') else [1, 2, 3]
    for task_name in task_list:
        for run_num in run_nums:
            if not run_is_complete(task_name, model_type, model_name, method, context, run_num):
                out.append((task_name, run_num))
    return out


def all_three_runs_complete(task_name: str, model_type: str, model_name: str, method: str,
                            context: str = 'previous', mutated_task_name: Optional[str] = None) -> bool:
    """Check if all 3 runs (1st, 2nd, 3rd pass) exist for the given task/model/method.
    Returns True if all 3 runs have result JSON; False otherwise (only JSON is required)."""
    model_identifier = get_model_identifier(model_type, model_name)
    json_base_dir = get_evaluation_results_dir()
    json_base_path = os.path.join(json_base_dir, task_name, model_identifier, method)

    for run_num in [1, 2, 3]:
        run_suffix = get_run_suffix(run_num)
        json_exists = False
        if os.path.exists(json_base_path):
            # 同样放宽匹配条件
            json_pattern = os.path.join(json_base_path, f"{context}_{run_suffix}_*")
            json_exists = bool(glob.glob(json_pattern))
        if not json_exists:
            return False
    return True


def detect_next_run_number(task_name: str, model_type: str, model_name: str, method: str,
                           context: str = 'previous', mutated_task_name: Optional[str] = None) -> int:
    """Detect next available run number by checking existing JSON files (only JSON is required)."""
    model_identifier = get_model_identifier(model_type, model_name)
    json_base_dir = get_evaluation_results_dir()
    json_base_path = os.path.join(json_base_dir, task_name, model_identifier, method)
    existing_runs = set()

    for run_num in [1, 2, 3]:
        run_suffix = get_run_suffix(run_num)
        json_exists = False
        if os.path.exists(json_base_path):
            # 同样放宽匹配条件
            json_pattern = os.path.join(json_base_path, f"{context}_{run_suffix}_*")
            json_exists = bool(glob.glob(json_pattern))
        if json_exists:
            existing_runs.add(run_num)

    for run_num in [1, 2, 3]:
        if run_num not in existing_runs:
            return run_num

    print("⚠️  Warning: All 3 runs already exist (JSON). Starting from run 1 again.")
    return 1


def load_log_file(log_path: str) -> Optional[Dict[str, Any]]:
    """Load and parse a log file"""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Failed to load log file {log_path}: {e}")
        return None


def load_best_code_from_log(log_path: str) -> tuple[str, dict]:
    """Load best_code from a log file"""
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")
    
    with open(log_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
    
    best_code = log_data.get('best_code')
    if not best_code:
        raise ValueError(f"No 'best_code' found in log file: {log_path}")
    
    return best_code, log_data


def clean_special_tags(raw_text: str) -> str:
        """
        Clean special format tags from model output before storing in conversation history.
        Some models (like gpt-oss-20b) output <|channel|> tags that cause errors when passed back to the API.
        
        This method extracts the actual content from between <|message|> and <|end|> or <|return|> tags,
        removing the special format markers.
        """
        if not raw_text:
            return raw_text
        
        # Check if the text contains special tags
        if '<|channel|>' not in raw_text and '<|message|>' not in raw_text:
            # No special tags, return as-is
            return raw_text
        
        # Extract content from <|message|> to <|end|> or <|return|> blocks
        # Pattern: <|channel|>TYPE<|message|>CONTENT<|end|> or <|return|>
        cleaned_parts = []
        
        # Find all message blocks (ending with either <|end|> or <|return|>)
        # First try with <|end|>
        message_pattern_end = r'<\|channel\|>([^<]+)<\|message\|>(.*?)<\|end\|>'
        matches_end = list(re.finditer(message_pattern_end, raw_text, re.DOTALL))
        
        # Also try with <|return|>
        message_pattern_return = r'<\|channel\|>([^<]+)<\|message\|>(.*?)<\|return\|>'
        matches_return = list(re.finditer(message_pattern_return, raw_text, re.DOTALL))
        
        # Combine matches, avoiding duplicates
        all_matches = []
        seen_positions = set()
        
        for match in matches_end + matches_return:
            start_pos = match.start()
            if start_pos not in seen_positions:
                seen_positions.add(start_pos)
                all_matches.append(match)
        
        # Sort by position
        all_matches.sort(key=lambda m: m.start())
        
        for match in all_matches:
            channel_type = match.group(1).strip()
            message_content = match.group(2).strip()
            
            # Include all channels' content (both analysis and final)
            if message_content:
                cleaned_parts.append(message_content)
        
        # If we found message blocks, join them
        if cleaned_parts:
            cleaned = '\n\n'.join(cleaned_parts)
        else:
            # Fallback: remove all special tags but keep the content
            cleaned = re.sub(r'<\|channel\|>[^<]*', '', raw_text)
            cleaned = re.sub(r'<\|message\|>', '', cleaned)
            cleaned = re.sub(r'<\|end\|>', '', cleaned)
            cleaned = re.sub(r'<\|start\|>', '', cleaned)
            cleaned = re.sub(r'<\|return\|>', '', cleaned)
        
        return cleaned.strip()