"""
Adapter script for CodeEvolve: run 2D CodeVerifier on code_path and write JSON to results_path.
CodeEvolve calls: python evaluate.py <code_path> <results_path> with cwd=inpt_dir.
Set env: DAVINCI_SCRIPTS_DIR (scripts root), DAVINCI_TASK_NAME (task name for verifier).
"""
import json
import os
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: evaluate.py <code_path> <results_path>", file=sys.stderr)
        sys.exit(1)
    code_path = sys.argv[1]
    results_path = sys.argv[2]
    scripts_dir = os.environ.get("DAVINCI_SCRIPTS_DIR")
    task_name = os.environ.get("DAVINCI_TASK_NAME")
    if not scripts_dir or not task_name:
        print("DAVINCI_SCRIPTS_DIR and DAVINCI_TASK_NAME must be set", file=sys.stderr)
        sys.exit(1)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    with open(code_path, "r", encoding="utf-8") as f:
        code = f.read()

    from evaluation.verifier import CodeVerifier

    # Default max_steps; CodeEvolve runs in temp dir so we don't have task-specific config here
    max_steps = int(os.environ.get("DAVINCI_MAX_STEPS", "10000"))
    env_overrides = {}
    env_overrides_str = os.environ.get("DAVINCI_ENV_OVERRIDES")
    if env_overrides_str:
        try:
            env_overrides = json.loads(env_overrides_str)
        except (json.JSONDecodeError, TypeError):
            pass
    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
    success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
    fitness = float(score)
    out = {
        "fitness": fitness,
        "success": success,
        "score": score,
        "metrics": metrics or {},
        "error": error,
    }
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    sys.exit(0)


if __name__ == "__main__":
    main()
