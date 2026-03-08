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


def get_gif_path(gif_dir: str, context: str, iteration: int) -> str:
    """Generate GIF file path"""
    filename = f"{context}_{iteration}.gif"
    return os.path.join(gif_dir, filename)


def get_gif_base_dir() -> str:
    """Get base directory for GIF files"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, "gif")


def get_evaluation_results_dir() -> str:
    """Get base directory for evaluation results"""
    script_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(script_dir, "evaluation_results")


def run_is_complete(task_name: str, model_type: str, model_name: str, method: str,
                    context: str, mutated_task_name: Optional[str] = None) -> bool:
    """Check if the single run has the result JSON."""
    from evaluation.prompt import parse_task_name
    try:
        task_path, _ = parse_task_name(task_name)
        cat_dir, task_subdir = task_path.split('/')
    except Exception:
        cat_dir = "other"
        task_subdir = task_name

    model_identifier = get_model_identifier(model_type, model_name)
    json_base_dir = get_evaluation_results_dir()
    json_base_path = os.path.join(json_base_dir, cat_dir, task_subdir, model_identifier, method)

    if os.path.exists(json_base_path):
        task_label = mutated_task_name if mutated_task_name else "raw"
        json_filename = f"{context}_{task_label}.json"
        json_path = os.path.join(json_base_path, json_filename)
        
        # Check for new format first
        if os.path.exists(json_path):
            return True
            
        # Fallback to old pattern for backward compatibility if needed (optional)
        if mutated_task_name:
            # Check for specific pair result: {context}_{mutated_task_name}_{date}.json
            json_pattern = os.path.join(json_base_path, f"{context}_{mutated_task_name}_*")
        else:
            # {context}_{date}.json
            json_pattern = os.path.join(json_base_path, f"{context}_20*")
        
        # Also check old task_name structure (not cat_dir/task_subdir)
        old_json_base_path = os.path.join(json_base_dir, task_name, model_identifier, method)
        if os.path.exists(old_json_base_path):
            if mutated_task_name:
                old_json_pattern = os.path.join(old_json_base_path, f"{context}_{mutated_task_name}_*")
            else:
                old_json_pattern = os.path.join(old_json_base_path, f"{context}_20*")
            if bool(glob.glob(json_pattern)) or bool(glob.glob(old_json_pattern)):
                return True

    return False


def get_max_steps_for_task(task_name: str) -> int:
    """
    Returns the task-specific maximum simulation steps.
    Centralizes discrepancies between default (10,000) and reference test scripts.
    """
    # Mapping of task names to their required max_steps based on reference tests
    TASK_MAX_STEPS = {
        'category_1_03': 15000,
        'category_1_04': 20000,
        'category_1_05': 20000,
        'category_1_06': 15000,
        'category_2_01': 90000,
        'category_2_02': 20000,
        'category_2_03': 20000,
        'category_2_04': 60000,
        'category_2_05': 60000,
        'category_2_06': 150000,
        'category_3_03': 20000,
        'category_3_04': 15000,
        'category_3_06': 15000,
        'category_5_05': 12000,
    }
    return TASK_MAX_STEPS.get(task_name.lower(), 10000)


def collect_incomplete_runs(
    task_list: list,
    model_type: str,
    model_name: str,
    method: str,
    context: str = 'previous',
) -> list:
    """Collect task_names for runs that are not complete (missing JSON)."""
    out: List[str] = []
    for task_name in task_list:
        if not run_is_complete(task_name, model_type, model_name, method, context):
            out.append(task_name)
    return out


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
        """
        if not raw_text:
            return raw_text
        
        if '<|channel|>' not in raw_text and '<|message|>' not in raw_text:
            return raw_text
        
        cleaned_parts = []
        message_pattern_end = r'<\|channel\|>([^<]+)<\|message\|>(.*?)<\|end\|>'
        matches_end = list(re.finditer(message_pattern_end, raw_text, re.DOTALL))
        
        message_pattern_return = r'<\|channel\|>([^<]+)<\|message\|>(.*?)<\|return\|>'
        matches_return = list(re.finditer(message_pattern_return, raw_text, re.DOTALL))
        
        all_matches = []
        seen_positions = set()
        
        for match in matches_end + matches_return:
            start_pos = match.start()
            if start_pos not in seen_positions:
                seen_positions.add(start_pos)
                all_matches.append(match)
        
        all_matches.sort(key=lambda m: m.start())
        
        for match in all_matches:
            message_content = match.group(2).strip()
            if message_content:
                cleaned_parts.append(message_content)
        
        if cleaned_parts:
            cleaned = '\n\n'.join(cleaned_parts)
        else:
            cleaned = re.sub(r'<\|channel\|>[^<]*', '', raw_text)
            cleaned = re.sub(r'<\|message\|>', '', cleaned)
            cleaned = re.sub(r'<\|end\|>', '', cleaned)
            cleaned = re.sub(r'<\|start\|>', '', cleaned)
            cleaned = re.sub(r'<\|return\|>', '', cleaned)
        
        return cleaned.strip()
