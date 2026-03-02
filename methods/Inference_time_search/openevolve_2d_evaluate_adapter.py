"""
Adapter evaluator for OpenEvolve (AlphaEvolve): evaluate(program_path) runs 2D CodeVerifier and returns a dict.
OpenEvolve loads this file and calls evaluate(program_path). Requires env: DAVINCI_SCRIPTS_DIR, DAVINCI_TASK_NAME, DAVINCI_MAX_STEPS.
Optional: DAVINCI_ENV_OVERRIDES (JSON) for Stage-* mutated environment (terrain_config, physics_config).
"""
import json
import os
import sys


def evaluate(program_path: str) -> dict:
    """
    Evaluate a program file for OpenEvolve. Called by openevolve with path to a .py file.
    Returns dict with combined_score (and score, success, metrics, error) for fitness.
    """
    scripts_dir = os.environ.get("DAVINCI_SCRIPTS_DIR")
    task_name = os.environ.get("DAVINCI_TASK_NAME")
    max_steps = int(os.environ.get("DAVINCI_MAX_STEPS", "10000"))

    if not scripts_dir or not task_name:
        return {
            "combined_score": 0.0,
            "score": 0.0,
            "success": False,
            "metrics": {},
            "error": "DAVINCI_SCRIPTS_DIR and DAVINCI_TASK_NAME must be set",
        }

    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    with open(program_path, "r", encoding="utf-8") as f:
        code = f.read()

    from evaluation.verifier import CodeVerifier

    env_overrides = {}
    env_overrides_str = os.environ.get("DAVINCI_ENV_OVERRIDES")
    if env_overrides_str:
        try:
            env_overrides = json.loads(env_overrides_str)
        except (json.JSONDecodeError, TypeError):
            pass
    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
    success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
    score_f = float(score)
    return {
        "combined_score": score_f,
        "score": score_f,
        "success": success,
        "metrics": metrics or {},
        "error": error,
    }
