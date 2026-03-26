"""Utility functions for evaluation scripts"""
import os
import sys
import json
import glob
import re
import importlib.util
from typing import Optional, Dict, Any, List, Tuple


def load_task_stages_module(stages_file: str) -> Any:
    """
    Load ``tasks/.../<task>/stages.py`` via importlib.

    Temporarily prepends that task directory to ``sys.path`` so bare imports like
    ``from environment import ...`` resolve to that task's ``environment.py``.
    Without this, dynamic loads (e.g. C_02) can pick up another task's module
    (e.g. C_01/environment.py).
    """
    task_dir = os.path.dirname(os.path.abspath(stages_file))
    sys.path.insert(0, task_dir)
    try:
        spec = importlib.util.spec_from_file_location("_davinci_task_stages", stages_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {stages_file}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if sys.path and sys.path[0] == task_dir:
            sys.path.pop(0)


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
    """Get run suffix (1st, 2nd, 3rd, etc.)."""
    if run_num == 1:
        return '1st'
    elif run_num == 2:
        return '2nd'
    elif run_num == 3:
        return '3rd'
    else:
        return f'{run_num}th'


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


def get_evaluation_results_scratch_dir() -> str:
    """
    Base dir for from-scratch runs and Rememberer/ExpeL category rollout backfill.
    Override with env ``EVALUATION_RESULTS_SCRATCH_DIR`` (absolute path) if scratch lives elsewhere.
    """
    override = os.environ.get("EVALUATION_RESULTS_SCRATCH_DIR", "").strip()
    if override:
        return os.path.abspath(override)
    script_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(script_dir, "evaluation_results_scratch")


def get_scratch_pair_path(
    task_name: str,
    source_env: str,
    model_identifier: str,
    results_scratch_base: Optional[str] = None,
) -> str:
    """
    Path to baseline single-env JSON in evaluation_results_scratch used for pair-based memory.
    Layout: base / cat_dir / task_subdir / model_identifier / baseline / all_{source_env}.json
    When ``results_scratch_base`` is None, uses ``get_evaluation_results_scratch_dir()``.
    """
    from evaluation.prompt import parse_task_name

    base = results_scratch_base or get_evaluation_results_scratch_dir()
    try:
        task_path, _ = parse_task_name(task_name)
        cat_dir, task_subdir = task_path.split("/")
    except Exception:
        cat_dir = "other"
        task_subdir = task_name
    safe_env = (source_env or "Initial").replace("/", "_").strip()
    return os.path.join(
        base,
        cat_dir,
        task_subdir,
        model_identifier,
        "baseline",
        f"all_{safe_env}.json",
    )


def get_training_log_root() -> str:
    """Root directory for Parameter_Policy training logs: scripts/training_log"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, "training_log")


def _safe_training_log_segment(label: str) -> str:
    """Filesystem-safe single path segment for training logs."""
    t = (label or "").strip()
    if not t:
        return "unknown"
    t = re.sub(r"[^\w.\-]+", "_", t)
    return (t[:200] if len(t) > 200 else t) or "unknown"


def get_training_log_dir(
    task_name: str,
    model_id: str,
    method: str,
    mutated_task_label: Optional[str] = None,
) -> str:
    """Directory for one run: training_log/{cat}/{task_subdir}/{model}/{method}/{task_key}/{run_key}/.

    ``task_key`` is derived from ``task_name`` (e.g. category_1_01) so multiple tasks under the same
    S_01 folder do not overwrite logs. ``run_key`` is ``mutated_task_label`` when set, else ``raw``.
    """
    from evaluation.prompt import parse_task_name
    try:
        task_path, _ = parse_task_name(task_name)
        cat_dir, task_subdir = task_path.split("/")
    except Exception:
        cat_dir, task_subdir = "other", task_name
    root = get_training_log_root()
    base = os.path.join(root, cat_dir, task_subdir, model_id, method)
    task_key = _safe_training_log_segment(task_name)
    run_key = _safe_training_log_segment(mutated_task_label) if mutated_task_label else "raw"
    return os.path.join(base, task_key, run_key)


def run_is_complete(
    task_name: str,
    model_type: str,
    model_name: str,
    method: str,
    context: str,
    mutated_task_name: Optional[str] = None,
    results_base_dir: Optional[str] = None,
) -> bool:
    """Check if the single run has the result JSON."""
    from evaluation.prompt import parse_task_name
    try:
        task_path, _ = parse_task_name(task_name)
        cat_dir, task_subdir = task_path.split('/')
    except Exception:
        cat_dir = "other"
        task_subdir = task_name

    model_identifier = get_model_identifier(model_type, model_name)
    json_base_dir = results_base_dir if results_base_dir else get_evaluation_results_dir()
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


def _task_name_to_legacy_key(task_name: str) -> str:
    """
    Convert task name (path or legacy) to legacy key for TASK_MAX_STEPS.
    e.g. Category5_Cybernetics_Control/C_02 -> category_5_02
    """
    key = task_name.strip().lower()
    # Already legacy format (category_X_YY)
    if re.match(r"^category_\d+_\d+$", key):
        return key
    # Path format: Category5_Cybernetics_Control/C_02
    parts = key.split("/")
    if len(parts) == 2:
        m_cat = re.match(r"category(\d+)", parts[0])
        m_task = re.match(r"[a-z]_(\d+)", parts[1])
        if m_cat and m_task:
            return f"category_{m_cat.group(1)}_{m_task.group(1)}"
    return key


def get_max_steps_for_task(task_name: str) -> int:
    """
    Returns the task-specific maximum simulation steps.
    Centralizes discrepancies between default (10,000) and reference test scripts.
    """
    # Mapping of task names to their required max_steps. Single source of truth for
    # evaluate.py and test_reference_solutions.py. When a task has different
    # max_steps per env (e.g. K_01 Initial vs Stage-*), use the maximum.
    TASK_MAX_STEPS = {
        'category_1_03': 1800,   # S_03: 30s (max across stages)
        'category_1_04': 20000,
        'category_1_05': 20000,
        'category_1_06': 15000,
        'category_2_01': 350000,  # K_01: max(Initial 200k, Stage-* 350k)
        'category_2_02': 20000,
        'category_2_03': 20000,
        'category_2_04': 60000,
        'category_2_05': 60000,
        'category_2_06': 150000,
        'category_3_01': 6000,
        'category_3_03': 20000,
        'category_3_04': 15000,
        'category_3_06': 15000,
        'category_4_03': 2400,   # F_03: 40s at 60 fps
        'category_4_05': 10000,  # F_05: align with prompt.py / test_mutated_tasks.py / run_test.py
        'category_5_01': 20000,  # C_01: cart-pole balance; baseline horizon is long (curriculum stages override max_steps)
        # C_02: must match tasks/.../C_02/environment.MAX_EPISODE_STEPS
        'category_5_02': 5000,
        'category_5_04': 250000,  # C_04 The Escaper: maze unlock + exit hold; long horizon for laggy control
        'category_5_05': 35000,  # C_05: align with test_stage_solutions.py (was 12000)
        'category_5_06': 15000,  # C_06: Governor needs enough steps for regulation; Initial & Stage-3 refs
        'category_6_01': 2500,   # E_01: Stage-4 singularity needs more steps than 1200
        'category_6_04': 12000,  # E_04: enough for success; longer runs can cause late joint failure
        'category_6_06': 500,    # E_06: align with test_agent.py
    }
    legacy_key = _task_name_to_legacy_key(task_name)
    return TASK_MAX_STEPS.get(legacy_key, 10000)


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
