"""
ACE method: wrap DaVinciBench/baseline/Memory/ace for 2D_exploration evaluation.
Uses the original ACE package (Reflector, Curator, playbook) via import.
Code generation stays with 2D SolverInterface; playbook is injected into prompt and updated each iteration.
"""
import os
import sys
from typing import Optional, Tuple, Any, List, Dict

# Ensure ACE package is importable (same repo, relative to this file)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# methods/Memory -> methods -> scripts -> 2D_exploration -> DaVinciBench
_DAVINCI_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
_ACE_ROOT = os.path.join(_DAVINCI_ROOT, "baseline", "Memory", "ace")
if os.path.isdir(_ACE_ROOT) and _ACE_ROOT not in sys.path:
    sys.path.insert(0, _ACE_ROOT)

# Default models for Reflector/Curator (same as ACE eval/finance/run.py)
DEFAULT_ACE_REFLECTOR_MODEL = "deepseek-v3.2"
DEFAULT_ACE_CURATOR_MODEL = "deepseek-v3.2"

# Empty playbook template (from ACE.ACE._initialize_empty_playbook)
EMPTY_PLAYBOOK = """## STRATEGIES & INSIGHTS

## FORMULAS & CALCULATIONS

## CODE SNIPPETS & TEMPLATES

## COMMON MISTAKES TO AVOID

## PROBLEM-SOLVING HEURISTICS

## CONTEXT CLUES & INDICATORS

## OTHERS"""


def get_initial_playbook() -> str:
    """Return the empty playbook template (same as ACE._initialize_empty_playbook)."""
    return EMPTY_PLAYBOOK


def _get_ace_clients(api_key: Optional[str] = None, base_url: Optional[str] = None):
    """Create OpenAI clients for Reflector/Curator. If api_key is None, use ACE's initialize_clients('openai')."""
    try:
        import openai
    except ImportError:
        raise ImportError("ACE method requires 'openai'. Install with: pip install openai")
    if api_key is not None:
        url = base_url if base_url else "https://api.openai.com/v1"
        client = openai.OpenAI(api_key=api_key, base_url=url)
        return client, client, client
    from utils import initialize_clients
    return initialize_clients("openai")


def build_ace_reflector_curator(
    reflector_model: str = DEFAULT_ACE_REFLECTOR_MODEL,
    curator_model: str = DEFAULT_ACE_CURATOR_MODEL,
    max_tokens: int = 65536,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
):
    """
    Create Reflector and Curator instances from ACE (for use in 2D iteration loop).
    Returns (reflector, curator, next_global_id).
    """
    # Ensure ACE root is first in path so ACE's utils/playbook_utils/logger/llm are found (not 2D_exploration's evaluation/utils.py)
    if _ACE_ROOT in sys.path:
        sys.path.remove(_ACE_ROOT)
    sys.path.insert(0, _ACE_ROOT)
    # Clear cached modules that would shadow ACE's: 2D evaluation/utils.py has no get_section_slug; ACE's utils does
    for mod in ("utils", "llm", "logger", "playbook_utils"):
        if mod in sys.modules:
            m = sys.modules[mod]
            if mod == "utils" and not getattr(m, "get_section_slug", None):
                del sys.modules[mod]
            elif mod != "utils":
                del sys.modules[mod]
    gen_client, ref_client, cur_client = _get_ace_clients(api_key=api_key, base_url=base_url)
    api_provider = "openai"
    from ace.core.reflector import Reflector
    from ace.core.curator import Curator
    reflector = Reflector(ref_client, api_provider, reflector_model, max_tokens)
    curator = Curator(cur_client, api_provider, curator_model, max_tokens)
    next_global_id = 1
    return reflector, curator, next_global_id


def reflect_on_iteration(
    reflector: Any,
    question: str,
    reasoning_trace: str,
    predicted_answer: str,
    environment_feedback: str,
    bullets_used: str = "",
    use_ground_truth: bool = False,
    use_json_mode: bool = False,
    call_id: str = "reflect",
    log_dir: Optional[str] = None,
) -> Tuple[str, List[Dict[str, str]], Dict[str, Any]]:
    """
    Call ACE Reflector: analyze (code + feedback) and return reflection + bullet tags.
    Returns (reflection_content, bullet_tags, call_info).
    """
    reflection_content, bullet_tags, call_info = reflector.reflect(
        question=question,
        reasoning_trace=reasoning_trace,
        predicted_answer=predicted_answer,
        ground_truth=None,
        environment_feedback=environment_feedback,
        bullets_used=bullets_used,
        use_ground_truth=use_ground_truth,
        use_json_mode=use_json_mode,
        call_id=call_id,
        log_dir=log_dir,
    )
    return reflection_content, bullet_tags, call_info


def update_playbook_after_iteration(
    playbook: str,
    reflection_content: str,
    question_context: str,
    iteration: int,
    max_iterations: int,
    token_budget: int,
    curator: Any,
    bullet_tags: List[Dict[str, str]],
    next_global_id: int,
    use_json_mode: bool = False,
    log_dir: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Update bullet counts from Reflector tags, then run Curator to update playbook.
    Returns (updated_playbook, next_global_id).
    """
    from playbook_utils import update_bullet_counts, get_playbook_stats
    if bullet_tags:
        playbook = update_bullet_counts(playbook, bullet_tags)
    stats = get_playbook_stats(playbook)
    updated_playbook, next_global_id, _ops, _info = curator.curate(
        current_playbook=playbook,
        recent_reflection=reflection_content,
        question_context=question_context,
        current_step=iteration,
        total_samples=max_iterations,
        token_budget=token_budget,
        playbook_stats=stats,
        use_ground_truth=False,
        use_json_mode=use_json_mode,
        call_id=f"curate_iter_{iteration}",
        log_dir=log_dir,
        next_global_id=next_global_id,
    )
    return updated_playbook, next_global_id


def extract_playbook_bullets(playbook: str, bullet_ids: List[str]) -> str:
    """Return a string of bullet lines for the given ids (for Reflector bullets_used)."""
    from playbook_utils import parse_playbook_line
    lines = playbook.strip().split("\n")
    id_set = set(bullet_ids)
    out = []
    for line in lines:
        parsed = parse_playbook_line(line)
        if parsed and parsed.get("id") in id_set:
            out.append(line)
    return "\n".join(out) if out else "(none)"


def restore_playbook_from_base_log(log_data: Optional[Dict[str, Any]]) -> str:
    """
    Restore playbook from base task log so mutated tasks start with T0's playbook.
    Returns initial playbook string (or empty playbook if not found).
    """
    if not log_data:
        return get_initial_playbook()
    playbook = log_data.get("final_playbook")
    if isinstance(playbook, str) and playbook.strip():
        return playbook
    return get_initial_playbook()
