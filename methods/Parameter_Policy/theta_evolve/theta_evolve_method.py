"""
ThetaEvolve method for 2D_exploration: test-time RL with Ray/slime/sglang + evolving gym.
Uses DaVinciBench/baseline/Parameter_Policy/ThetaEvolve; local model only.

Run flow: build work dir (initial_program, evaluator, config) -> set env -> invoke ThetaEvolve
train.py (subprocess) -> load best program from evolving_gym database -> build report (JSON + GIF).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# Scripts dir = parent of methods/
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# ThetaEvolve repo: DaVinciBench/baseline/Parameter_Policy/ThetaEvolve (one level above 2D_exploration)
_THETA_EVOLVE_REPO = os.path.normpath(
    os.path.join(_SCRIPTS_DIR, "..", "..", "..", "baseline", "Parameter_Policy", "ThetaEvolve")
)

# Same minimal 2D agent as alpha_evolve
DEFAULT_SOLUTION_TEMPLATE = """def build_agent(sandbox):
    '''Evolve this function to solve the task.'''
    body = sandbox.add_beam(x=5.0, y=1.5, width=1.0, height=0.3, density=1.0)
    return body

def agent_action(sandbox, agent_body, step_count):
    pass
"""

# 2D evaluator content: same contract as openevolve_2d_evaluate_adapter (evaluate(program_path) -> dict with combined_score)
_EVALUATOR_TEMPLATE = '''"""
2D evaluator for ThetaEvolve evolving gym: evaluate(program_path) -> dict with combined_score.
Requires env: DAVINCI_SCRIPTS_DIR, DAVINCI_TASK_NAME, DAVINCI_MAX_STEPS.
Optional: DAVINCI_ENV_OVERRIDES (JSON) for mutated stages.
"""
import json
import os
import sys


def evaluate(program_path: str) -> dict:
    scripts_dir = os.environ.get("DAVINCI_SCRIPTS_DIR")
    task_name = os.environ.get("DAVINCI_TASK_NAME")
    max_steps = int(os.environ.get("DAVINCI_MAX_STEPS", "10000"))
    if not scripts_dir or not task_name:
        return {"combined_score": 0.0, "score": 0.0, "success": False, "metrics": {}, "error": "DAVINCI_* not set"}
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    with open(program_path, "r", encoding="utf-8") as f:
        code = f.read()
    from evaluation.verifier import CodeVerifier
    env_overrides = {}
    s = os.environ.get("DAVINCI_ENV_OVERRIDES")
    if s:
        try:
            env_overrides = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            pass
    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
    success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
    return {"combined_score": float(score), "score": float(score), "success": success, "metrics": metrics or {}, "error": error}
'''


def _resolve_model_path(model_name: str, model_path: Optional[str] = None) -> str:
    """Resolve model name to existing path (same logic as ragen/seal)."""
    if model_path and os.path.exists(model_path):
        return model_path
    if os.path.exists(model_name):
        return model_name
    for prefix in ["/home/test/testdata/models/", os.path.expanduser("~/models/")]:
        candidate = os.path.join(prefix, os.path.basename(model_name))
        if os.path.exists(candidate):
            return candidate
    return model_path or model_name


def _make_work_dir(
    task_name: str,
    scripts_dir: str,
    initial_code: Optional[str] = None,
    max_steps: int = 10000,
) -> Tuple[str, str, str, str]:
    """Create temp dir with initial_program.py, evaluator.py, config.yaml. Returns (work_dir, initial_path, evaluator_path, config_path)."""
    work_dir = tempfile.mkdtemp(prefix="theta_evolve_2d_")
    code = initial_code if initial_code else DEFAULT_SOLUTION_TEMPLATE
    initial_path = os.path.join(work_dir, "initial_program.py")
    with open(initial_path, "w", encoding="utf-8") as f:
        f.write(code)
    evaluator_path = os.path.join(work_dir, "evaluate.py")
    with open(evaluator_path, "w", encoding="utf-8") as f:
        f.write(_EVALUATOR_TEMPLATE)
    # Minimal gym config (evaluator timeout, diff_based_evolution; prompt injected by gym)
    config_path = os.path.join(work_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(
            "diff_based_evolution: true\nmax_code_length: 10000\nrandom_seed: 42\n"
            "evaluator:\n  timeout: 300\n  cascade_evaluation: false\n  max_retries: 0\n"
            "database:\n  use_bulk_io: true\n"
        )
    return work_dir, initial_path, evaluator_path, config_path


def _find_latest_evolving_gym_database(save_dir: str) -> Optional[str]:
    """Find latest evolving_gym_database_* directory under save_dir/rollout/."""
    rollout_dir = os.path.join(save_dir, "rollout")
    if not os.path.isdir(rollout_dir):
        return None
    pattern = os.path.join(rollout_dir, "evolving_gym_database_*")
    db_dirs = glob.glob(pattern)
    if not db_dirs:
        return None
    # Sort by number in suffix (evolving_gym_database_0, 1, 2, ...)
    def key(p):
        try:
            return int(p.rsplit("_", 1)[-1])
        except (ValueError, IndexError):
            return -1
    db_dirs.sort(key=key)
    return db_dirs[-1]


def _load_best_code_from_database(db_path: str) -> Optional[str]:
    """Load best program code from saved evolving_gym database (metadata.json + programs_bulk.json)."""
    metadata_path = os.path.join(db_path, "metadata.json")
    if not os.path.isfile(metadata_path):
        return None
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    best_id = metadata.get("best_program_id")
    if not best_id:
        # Fallback: program with highest combined_score
        bulk_path = os.path.join(db_path, "programs_bulk.json")
        if not os.path.isfile(bulk_path):
            return None
        with open(bulk_path, "r", encoding="utf-8") as f:
            programs_data = json.load(f)
        best_score = -1e9
        best_code = None
        for pid, p in programs_data.items():
            sc = (p.get("metrics") or {}).get("combined_score")
            if sc is not None and isinstance(sc, (int, float)) and sc > best_score:
                best_score = sc
                best_code = p.get("code")
        return best_code
    bulk_path = os.path.join(db_path, "programs_bulk.json")
    if os.path.isfile(bulk_path):
        with open(bulk_path, "r", encoding="utf-8") as f:
            programs_data = json.load(f)
        if best_id in programs_data:
            return programs_data[best_id].get("code")
    # Legacy: programs/<id>.json
    prog_path = os.path.join(db_path, "programs", f"{best_id}.json")
    if os.path.isfile(prog_path):
        with open(prog_path, "r", encoding="utf-8") as f:
            p = json.load(f)
        return p.get("code")
    return None


def _run_theta_evolve_train(
    work_dir: str,
    initial_program: str,
    evaluator_file: str,
    config_path: str,
    save_dir: str,
    hf_checkpoint: str,
    num_rollout: int = 3000,
    rollout_batch_size: int = 32,
    seed: int = 42,
    device: Optional[str] = None,
) -> int:
    """Invoke ThetaEvolve train.py with evolving_gym args. Returns exit code."""
    train_py = os.path.join(_THETA_EVOLVE_REPO, "train.py")
    if not os.path.isfile(train_py):
        print(f"[theta_evolve] ThetaEvolve repo not found at {_THETA_EVOLVE_REPO}; cannot run train.py")
        return 1
    # Preflight: train.py imports sglang; fail fast with clear instructions if missing
    try:
        import sglang.srt.constants  # noqa: F401
    except ImportError as e:
        print(
            "[theta_evolve] ThetaEvolve requires 'sglang'. Install ThetaEvolve deps in the repo, e.g.:\n"
            f"  cd {_THETA_EVOLVE_REPO} && pip install -e .\n"
            "  pip install sglang   # or: pip install \"sglang[all]\"\n"
            "Or use the official Docker: docker pull slimerl/slime:v0.5.0rc0-cu126"
        )
        print(f"[theta_evolve] ImportError: {e}")
        return 1
    # Build argv aligned to official ThetaEvolve scripts (scripts_evolve/*/general.sh):
    # Nemotron-1.5B/general.sh: num_rollout 10k, rollout_batch_size 32, n_samples_per_prompt 16,
    #   rollout_max_response_len 16384, rollout_temperature 1.0, save_interval 10.
    # DeepSeek-R1-Qwen3-8B/general.sh: same except num_rollout 1M, save_interval 5.
    # Use --colocate so actor+rollout share GPU(s). When device is cuda:0,1 (2 GPUs), use 2 GPUs per node.
    # With 2 GPUs use tensor parallel (TP=2) so model is sharded across cards; otherwise each rank loads full 9B and OOMs.
    _num_gpus = 2 if (device and "," in device) else 1
    argv = [
        sys.executable,
        "train.py",
        "--actor-num-nodes", "1",
        "--actor-num-gpus-per-node", str(_num_gpus),
    ]
    if _num_gpus == 2:
        argv += ["--tensor-model-parallel-size", "2", "--pipeline-model-parallel-size", "1"]
    # Official slime/utils/arguments.py defaults: evolving_gym_max_concurrent_evals=8,
    # evolving_gym_lazy_output_penalty_level=2, evolving_gym_reward_process_type=original_reward.
    save_interval_official = 10  # match Nemotron general.sh; DeepSeek uses 5
    argv += [
        "--colocate",
        "--no-rope-fusion",  # avoid requiring Transformer Engine (TE >= 1.4)
        "--transformer-impl", "local",  # do not use transformer_engine (TE not installed in env)
        "--no-persist-layer-norm",  # required when using torch LayerNorm (no Apex/TE)
        "--no-gradient-accumulation-fusion",  # required when Apex cuda_ext not installed (fused_weight_gradient_mlp_cuda)
        # Single-GPU 80G OOM: model is on the correct GPU but 8B + fp32 main params + Adam states > 80G.
        # To fit: install Transformer Engine and add "--use-precision-aware-optimizer", "--main-params-dtype", "fp16";
        # or run with 2 GPUs (e.g. --gpus 5,7).
        "--disable-rollout-global-dataset",
        "--evolving-gym",
        "--evolving-gym-initial-program", initial_program,
        "--evolving-gym-evaluator-file", evaluator_file,
        "--evolving-gym-config-path", config_path,
        "--evolving-gym-max-concurrent-evals", "8",
        "--evolving-gym-seed", str(seed),
        "--evolving-gym-reward-process-type", "original_reward",
        "--evolving-gym-lazy-output-penalty-level", "2",
        "--apply-chat-template",
        "--rm-type", "evolving-gym",
        "--reward-key", "reward",
        "--num-rollout", str(num_rollout),
        "--rollout-batch-size", str(rollout_batch_size),
        "--n-samples-per-prompt", "16",  # official scripts_evolve/*/general.sh use 16
        "--rollout-max-response-len", "16384",  # official scripts use 16384
        "--rollout-temperature", "1.0",  # official scripts use 1.0
        "--num-steps-per-rollout", "1",
        "--hf-checkpoint", hf_checkpoint,
        "--load", os.path.join(save_dir, "checkpoint"),
        "--save", save_dir,
        "--save-interval", str(save_interval_official),
    ]
    env = os.environ.copy()
    # Ray workers must see the same CUDA/nvidia libs as this process when importing torch.
    # Prepend only torch's lib (do NOT prepend conda/lib: that breaks Ray's bash via libtinfo).
    _ld = []
    try:
        import torch as _torch
        _torch_lib = os.path.join(os.path.dirname(_torch.__file__), "lib")
        if os.path.isdir(_torch_lib):
            _ld.append(_torch_lib)
    except Exception:
        pass
    for _p in ["/usr/local/cuda-12/lib64", "/usr/local/cuda/lib64"]:
        if os.path.isdir(_p):
            _ld.append(_p)
            break
    if _ld:
        _existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(_ld) + (":" + _existing if _existing else "")
    # Do not overwrite CUDA_VISIBLE_DEVICES when parent already set it (e.g. run_evaluate_parallel sets
    # it to the assigned physical GPU like 5). Overwriting with "0" would make the child use physical
    # GPU 0 and OOM if that card is occupied.
    if device and device.startswith("cuda:") and not os.environ.get("CUDA_VISIBLE_DEVICES"):
        gpu = device.replace("cuda:", "").strip()
        env["CUDA_VISIBLE_DEVICES"] = gpu
    # Reduce OOM at optimizer init: use expandable segments to limit fragmentation (single-GPU only).
    # With 2 GPUs we use TP + offload; TorchMemorySaver does not support expandable_segments yet, so leave unset.
    if _num_gpus != 2:
        env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    # Megatron TP/CP require this for correct NCCL behavior (assert in validate_args).
    if _num_gpus == 2:
        env["CUDA_DEVICE_MAX_CONNECTIONS"] = "1"
    try:
        proc = subprocess.run(
            argv,
            cwd=_THETA_EVOLVE_REPO,
            env=env,
            timeout=86400,  # 24h max per task
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        print("[theta_evolve] train.py timed out (24h)")
        return 1
    except Exception as e:
        print(f"[theta_evolve] train.py failed: {e}")
        return 1


def _write_theta_evolve_training_log(
    training_log_dir: str,
    task_name: str,
    model_name: str,
    exit_code: int,
    num_rollout: int,
    rollout_batch_size: int,
    seed: int,
    report: Dict[str, Any],
) -> None:
    """Write training_config.json and training_summary.txt for theta_evolve run."""
    import os
    os.makedirs(training_log_dir, exist_ok=True)
    config = {
        "method": "theta_evolve",
        "task_name": task_name,
        "model_name": model_name,
        "exit_code": exit_code,
        "num_rollout": num_rollout,
        "rollout_batch_size": rollout_batch_size,
        "seed": seed,
        "success": report.get("success", False),
        "best_score": report.get("best_score", 0.0),
    }
    config_path = os.path.join(training_log_dir, "training_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    lines = [
        "Method: theta_evolve",
        f"Task: {task_name}",
        f"Exit code: {exit_code}",
        f"Num rollout: {num_rollout}",
        f"Rollout batch size: {rollout_batch_size}",
        f"Success: {report.get('success')}",
        f"Best score: {report.get('best_score')}",
    ]
    summary_path = os.path.join(training_log_dir, "training_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_single_task(
    task_name: str,
    run_number: int,
    model_type: str,
    model_name: str,
    context: str = "all",
    max_steps: int = 10000,
    scripts_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    gif_base_dir: Optional[str] = None,
    initial_code: Optional[str] = None,
    model_path: Optional[str] = None,
    device: Optional[str] = None,
    env_overrides: Optional[Dict[str, Any]] = None,
    theta_evolve_num_rollout: int = 10000,
    theta_evolve_rollout_batch_size: int = 32,
    training_log_dir: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Run ThetaEvolve for one (task_name, run_number). Returns (exit_code, report).
    report has same structure as TaskEvaluator._generate_report for saving.
    Local model only.
    """
    from evaluation.prompt import load_task_prompt
    from evaluation.utils import get_model_identifier, get_run_suffix, get_gif_path, get_evaluation_results_dir, get_gif_base_dir
    from evaluation.verifier import CodeVerifier

    if model_type != "local":
        raise ValueError("theta_evolve only supports --model-type local")
    scripts_dir = scripts_dir or _SCRIPTS_DIR
    output_dir = output_dir or get_evaluation_results_dir()
    gif_base_dir = gif_base_dir or get_gif_base_dir()
    task_prompt = load_task_prompt(task_name)
    work_dir, initial_path, evaluator_path, config_path = _make_work_dir(
        task_name, scripts_dir, initial_code=initial_code, max_steps=max_steps
    )
    save_dir = os.path.join(work_dir, "theta_evolve_save")
    os.makedirs(save_dir, exist_ok=True)
    hf_checkpoint = _resolve_model_path(model_name, model_path)
    env_before = {}
    try:
        env_before["DAVINCI_SCRIPTS_DIR"] = os.environ.get("DAVINCI_SCRIPTS_DIR")
        env_before["DAVINCI_TASK_NAME"] = os.environ.get("DAVINCI_TASK_NAME")
        env_before["DAVINCI_MAX_STEPS"] = os.environ.get("DAVINCI_MAX_STEPS")
        env_before["DAVINCI_ENV_OVERRIDES"] = os.environ.get("DAVINCI_ENV_OVERRIDES")
        os.environ["DAVINCI_SCRIPTS_DIR"] = scripts_dir
        os.environ["DAVINCI_TASK_NAME"] = task_name
        os.environ["DAVINCI_MAX_STEPS"] = str(max_steps)
        if env_overrides:
            os.environ["DAVINCI_ENV_OVERRIDES"] = json.dumps(env_overrides)
        else:
            os.environ.pop("DAVINCI_ENV_OVERRIDES", None)
        seed = 1234 + run_number  # official parser default 1234; add run_number for per-run reproducibility
        print(f"[theta_evolve] Starting ThetaEvolve: task={task_name}, run={run_number}, num_rollout={theta_evolve_num_rollout}, seed={seed}")
        exit_code = _run_theta_evolve_train(
            work_dir=work_dir,
            initial_program=initial_path,
            evaluator_file=evaluator_path,
            config_path=config_path,
            save_dir=save_dir,
            hf_checkpoint=hf_checkpoint,
            num_rollout=theta_evolve_num_rollout,
            rollout_batch_size=theta_evolve_rollout_batch_size,
            seed=seed,
            device=device,
        )
    finally:
        for k, v in env_before.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    best_code = None
    if exit_code == 0:
        db_path = _find_latest_evolving_gym_database(save_dir)
        if db_path:
            best_code = _load_best_code_from_database(db_path)
    if not best_code:
        report = {
            "task_name": task_name,
            "model_type": model_type,
            "model_name": model_name,
            "method": "theta_evolve",
            "context": context,
            "max_iterations": 20,
            "total_iterations": 0,
            "best_score": 0.0,
            "final_score": 0.0,
            "success": False,
            "best_metrics": {},
            "final_metrics": {},
            "best_code": "",
            "token_statistics": {},
            "task_prompt": {
                "initial_prompt": None,
                "task_description": task_prompt.get("task_description", ""),
                "success_criteria": task_prompt.get("success_criteria", ""),
                "primitives_api": task_prompt.get("primitives_api", ""),
            },
            "iteration_history": [],
            "timestamp": datetime.now().isoformat(),
        }
        if training_log_dir:
            _write_theta_evolve_training_log(
                training_log_dir, task_name, model_name,
                exit_code, theta_evolve_num_rollout, theta_evolve_rollout_batch_size,
                1234 + run_number, report,
            )
        shutil.rmtree(work_dir, ignore_errors=True)
        return (1 if exit_code != 0 else 1, report)
    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides or {})
    model_identifier = get_model_identifier(model_type, model_name)
    run_suffix = get_run_suffix(run_number)
    gif_dir = os.path.join(gif_base_dir, task_name, model_identifier, "theta_evolve", "raw", f"{run_suffix}_pass")
    os.makedirs(gif_dir, exist_ok=True)
    gif_path = get_gif_path(gif_dir, context, 1)
    success, score, metrics, error = verifier.verify_code(best_code, headless=True, save_gif_path=gif_path)
    report = {
        "task_name": task_name,
        "model_type": model_type,
        "model_name": model_name,
        "method": "theta_evolve",
        "context": context,
        "max_iterations": 20,
        "total_iterations": theta_evolve_num_rollout,
        "best_score": float(score),
        "final_score": float(score),
        "success": success,
        "best_metrics": metrics or {},
        "final_metrics": metrics or {},
        "best_code": best_code,
        "token_statistics": {},
        "task_prompt": {
            "initial_prompt": None,
            "task_description": task_prompt.get("task_description", ""),
            "success_criteria": task_prompt.get("success_criteria", ""),
            "primitives_api": task_prompt.get("primitives_api", ""),
        },
        "iteration_history": [
            {
                "iteration": 1,
                "prompt": None,
                "code": best_code,
                "raw_llm_output": None,
                "token_usage": {},
                "score": float(score),
                "success": success,
                "error": error,
                "feedback": None,
                "metrics": metrics or {},
                "metrics_summary": {k: v for k, v in (metrics or {}).items() if k != "step_count"},
            }
        ],
        "timestamp": datetime.now().isoformat(),
    }
    task_model_method_dir = os.path.join(output_dir, task_name, model_identifier, "theta_evolve")
    os.makedirs(task_model_method_dir, exist_ok=True)
    pseudo_suffix = "_pseudo" if context == "all" else ""
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
    report_path = os.path.join(task_model_method_dir, filename)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Evaluation report saved: {report_path}")
    if training_log_dir:
        _write_theta_evolve_training_log(
            training_log_dir, task_name, model_name,
            0, theta_evolve_num_rollout, theta_evolve_rollout_batch_size,
            1234 + run_number, report,
        )
    shutil.rmtree(work_dir, ignore_errors=True)
    return (0, report)
