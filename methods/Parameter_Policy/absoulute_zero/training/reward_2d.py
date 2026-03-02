"""
2D reward: run CodeVerifier on generated code and return reward (0–1) for training.
"""
import os
import sys
from typing import Tuple, Dict, Any, Optional

# This file is at methods/Parameter_Policy/absoulute_zero/training/reward_2d.py
# Need scripts/ on path for evaluation.verifier imports
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, _SCRIPTS_DIR)

from evaluation.verifier import CodeVerifier


def compute_reward(
    task_name: str,
    code: str,
    max_steps: int = 10000,
    headless: bool = True,
    scale_to_01: bool = True,
    env_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[float, bool, float, Dict[str, Any], Optional[str]]:
    """
    Run CodeVerifier on code for the given task; return reward and details.

    Args:
        task_name: Task name (e.g. "demo/basic", "demo/control_aware", "category_1_01")
        code: Python code with build_agent() function
        env_overrides: Optional dict passed to CodeVerifier to vary terrain/physics.
    Returns:
        (reward_01, success, score_0_100, metrics, error_message)
    """
    if not code or len(code.strip()) < 50 or "def build_agent" not in code:
        return (0.0, False, 0.0, {"error_type": "invalid_code", "error_message": "code too short or missing build_agent"}, "invalid code")

    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
    success, score, metrics, error = verifier.verify_code(code, headless=headless, save_gif_path=None)
    if hasattr(verifier, "cleanup"):
        verifier.cleanup()

    if scale_to_01:
        reward = score / 100.0 if score is not None else (1.0 if success else 0.0)
    else:
        reward = score if score is not None else (100.0 if success else 0.0)
    return (reward, success, float(score) if score is not None else 0.0, metrics or {}, error)
