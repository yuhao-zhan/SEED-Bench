"""
Science-CodeEvolve method for 2D_exploration: run CodeEvolve per task and convert output to 2D report format.
Uses DaVinciBench/baseline/Inference_time_search/science-codeevolve; supports OpenAI API and local HF.
"""
import os
import sys
import json
import tempfile
import subprocess
import shutil
import yaml
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# Scripts dir = parent of methods/
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# CodeEvolve repo root (from 2D scripts: ../../baseline/Inference_time_search/science-codeevolve)
_CODEEVOLVE_ROOT = os.path.normpath(
    os.path.join(_SCRIPTS_DIR, "..", "..", "baseline", "Inference_time_search", "science-codeevolve")
)
_CODEEVOLVE_SRC = os.path.join(_CODEEVOLVE_ROOT, "src")

EVOLVE_START = "# EVOLVE-BLOCK-START"
EVOLVE_END = "# EVOLVE-BLOCK-END"

# Default solution template: minimal build_agent (only used when first-round generation is disabled or fails and placeholder is allowed)
DEFAULT_SOLUTION_TEMPLATE = f'''{EVOLVE_START}
def build_agent(sandbox):
    """Evolve this function to solve the task."""
    # Minimal placeholder: single body at origin
    body = sandbox.add_beam(x=5.0, y=1.5, width=1.0, height=0.3, density=1.0)
    return body

def agent_action(sandbox, agent_body, step_count):
    pass
{EVOLVE_END}
'''


def _generate_first_round_solution(
    task_prompt: Dict[str, Any],
    model_type: str,
    model_name: str,
    run_number: int,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Generate first-round solution the same way as baseline/alpha_evolve: format_initial_prompt + SolverInterface.generate_code.
    Returns extracted code, or None on failure.
    """
    from evaluation.prompt import format_initial_prompt
    from evaluation.solver_interface import SolverInterface

    prompt = format_initial_prompt(task_prompt)
    try:
        solver = SolverInterface(
            model_type=model_type,
            model_name=model_name,
            api_key=api_key,
        )
        if model_type == "openai" and api_base:
            solver.client.base_url = api_base
        code, _, _ = solver.generate_code(
            prompt, use_conversation=False, reset_conversation=True, seed=42 + run_number
        )
        if not code or len(code.strip()) < 50 or "def build_agent" not in code:
            return None
        return code
    except Exception as e:
        print(f"[science_codeevolve] First-round generation failed: {e}", flush=True)
        return None


def _adapter_evaluate_py_content() -> str:
    """Content of evaluate.py to put in inpt_dir (calls 2D CodeVerifier)."""
    adapter_path = os.path.join(os.path.dirname(__file__), "codeevolve_2d_evaluate_adapter.py")
    with open(adapter_path, "r", encoding="utf-8") as f:
        return f.read()


def _make_inpt_dir(
    task_name: str,
    scripts_dir: str,
    initial_code: Optional[str] = None,
    max_steps: int = 10000,
) -> str:
    """Create a temp inpt_dir with solution.py and evaluate.py. Returns path."""
    inpt = tempfile.mkdtemp(prefix="codeevolve_2d_inpt_")
    solution = initial_code if initial_code else DEFAULT_SOLUTION_TEMPLATE
    # Ensure EVOLVE markers present
    if EVOLVE_START not in solution:
        solution = f"{EVOLVE_START}\n{solution}\n{EVOLVE_END}"
    with open(os.path.join(inpt, "solution.py"), "w", encoding="utf-8") as f:
        f.write(solution)
    with open(os.path.join(inpt, "evaluate.py"), "w", encoding="utf-8") as f:
        f.write(_adapter_evaluate_py_content())
    return inpt


def _make_config_yaml(
    task_name: str,
    task_prompt: Dict[str, Any],
    model_type: str,
    model_name: str,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    seed: int = 42,
    use_api_for_inference: bool = False,
) -> Dict[str, Any]:
    """Build CodeEvolve config dict (repo defaults). Use fitness_key 'fitness'.

    When model_type is 'local' and use_api_for_inference is True (e.g. vLLM server),
    uses API-style config so CodeEvolve uses OpenAILM (no in-process load); one server, all islands call API.
    """
    sys_msg = (
        f"# PROMPT-BLOCK-START\n"
        f"Task: {task_prompt.get('task_description', '')}\n\n"
        f"Success: {task_prompt.get('success_criteria', '')}\n\n"
        f"API: {task_prompt.get('primitives_api', '')}\n"
        f"# PROMPT-BLOCK-END"
    )
    # Local + API (vLLM): no model_type "local" -> CodeEvolve uses OpenAILM, one load on server, N islands call API
    if model_type == "local" and use_api_for_inference:
        ensemble = [
            {
                "model_name": model_name,
                "temp": 0.7,
                "top_p": 0.95,
                "retries": 3,
                "weight": 1,
            }
        ]
        num_islands = 2
    elif model_type == "local":
        model_path = model_name if os.path.isdir(model_name) else model_name
        ensemble = [
            {
                "model_type": "local",
                "model_path": model_path,
                "model_name": model_path,
                "temp": 0.7,
                "top_p": 0.95,
                "weight": 1,
            }
        ]
        num_islands = 1  # in-process load per island -> 1 island to avoid OOM
    else:
        ensemble = [
            {
                "model_name": model_name,
                "temp": 0.7,
                "top_p": 0.95,
                "retries": 3,
                "weight": 1,
            }
        ]
        num_islands = 2
    use_local_sampler = model_type == "local" and not use_api_for_inference
    return {
        "SEED": seed,
        "SYS_MSG": sys_msg,
        "CODEBASE_PATH": ".",
        "INIT_FILE_DATA": {"filename": "solution.py", "language": "python"},
        "EVAL_FILE_NAME": "evaluate.py",
        "EVAL_TIMEOUT": 300,
        "MAX_MEM_BYTES": 2 * 1024 * 1024 * 1024,
        "MEM_CHECK_INTERVAL_S": 0.1,
        "EVOLVE_CONFIG": {
            "fitness_key": "fitness",
            # Default 100 epochs per run; override with env CODEEVOLVE_NUM_EPOCHS for quick test (e.g. 5)
            "num_epochs": int(os.environ.get("CODEEVOLVE_NUM_EPOCHS", "100")),
            "ckpt": 30,
            "max_size": None,
            # AlphaEvolve-style: one initial solution, all mutations from it (single_base_evolution=True)
            "init_pop": 1,
            "single_base_evolution": True,
            "exploration_rate": 0.2,
            "selection_policy": "roulette",
            "selection_kwargs": {"roulette_by_rank": True},
            "early_stopping_rounds": None,
            "num_islands": num_islands,
            "migration_topology": "ring",
            "migration_interval": 40,
            "migration_rate": 0.1,
            # Keep task description / success criteria / API fixed; only evolve code (no prompt evolution).
            "meta_prompting": False,
            "use_embedding": False,
            "use_map_elites": False,
            "num_inspirations": 2,
            "max_chat_depth": 5,
            "mp_start_marker": "# PROMPT-BLOCK-START",
            "mp_end_marker": "# PROMPT-BLOCK-END",
            "evolve_start_marker": EVOLVE_START,
            "evolve_end_marker": EVOLVE_END,
            "use_scheduler": False,
            "type": "PlateauScheduler",
            "scheduler_kwargs": {
                "min_rate": 0.2,
                "max_rate": 0.5,
                "plateau_threshold": 5,
                "increase_factor": 1.05,
                "decrease_factor": 0.95,
            },
        },
        "EXPLORATION_ENSEMBLE": ensemble,
        "EXPLOITATION_ENSEMBLE": ensemble,
        "SAMPLER_AUX_LM": ensemble[0] if use_local_sampler else {**ensemble[0], "retries": 3},
    }


def _run_codeevolve(
    inpt_dir: str,
    cfg_path: str,
    out_dir: str,
    env_extra: Optional[Dict[str, str]] = None,
    codeevolve_python: Optional[str] = None,
    verbose: bool = True,
) -> int:
    """Run codeevolve CLI. Returns exit code. If verbose, streams stdout/stderr in real time."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + _CODEEVOLVE_SRC
    env["PYTHONUNBUFFERED"] = "1"  # so CodeEvolve prints show up in real time when piped
    # CodeEvolve CLI requires API_BASE/API_KEY in env; env_extra from run_single_task sets them
    if "API_BASE" not in env:
        env["API_BASE"] = "http://localhost/v1"
    if "API_KEY" not in env:
        env["API_KEY"] = "dummy"

    python = codeevolve_python or sys.executable
    cmd = [
        python,
        "-m",
        "codeevolve.cli",
        "--inpt_dir", inpt_dir,
        "--cfg_path", cfg_path,
        "--out_dir", out_dir,
        "--load_ckpt", "0",
        "--y",  # skip "Do you wish to continue?" and all interactive prompts
        "--terminal_logging",  # show live progress from CodeEvolve
    ]
    try:
        if verbose:
            proc = subprocess.Popen(
                cmd,
                cwd=_SCRIPTS_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in iter(proc.stdout.readline, ""):
                print(f"[CodeEvolve] {line}", end="", flush=True)
            proc.wait()
            return proc.returncode
        ret = subprocess.run(cmd, cwd=_SCRIPTS_DIR, env=env, timeout=3600 * 24)
        return ret.returncode
    except subprocess.TimeoutExpired:
        return -1
    except FileNotFoundError:
        return -2


def _get_best_code_from_out_dir(out_dir: str) -> Optional[str]:
    """Read best solution from CodeEvolve output (island 0 best_sol)."""
    for name in ("best_sol.py", "best_sol"):
        p = os.path.join(out_dir, "0", name)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return None


def _get_population_history_from_out_dir(out_dir: str) -> list:
    """
    Load CodeEvolve checkpoints and return per-epoch population (code library) for each island.
    Returns a list of {"epoch": int, "islands": {"0": [{"id", "code", "fitness", "eval_metrics", ...}], "1": [...]}}.
    """
    import re
    if _CODEEVOLVE_SRC not in sys.path:
        sys.path.insert(0, _CODEEVOLVE_SRC)
    try:
        from codeevolve.utils.ckpt import load_ckpt
    except ImportError:
        return []

    result = []
    # Each island has its own ckpt dir: out_dir/0/ckpt/, out_dir/1/ckpt/, ...
    if not os.path.isdir(out_dir):
        return []
    pattern = re.compile(r"ckpt_(\d+)\.pkl$")
    epochs_seen = set()
    island_dirs = sorted([d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d)) and d.isdigit()])
    for isl in island_dirs:
        ckpt_dir = os.path.join(out_dir, isl, "ckpt")
        if not os.path.isdir(ckpt_dir):
            continue
        for fname in os.listdir(ckpt_dir):
            m = pattern.match(fname)
            if not m:
                continue
            epoch = int(m.group(1))
            if epoch not in epochs_seen:
                epochs_seen.add(epoch)
                result.append({"epoch": epoch, "islands": {}})
            # Find the dict we're appending to for this epoch
            entry = next((r for r in result if r["epoch"] == epoch), None)
            if not entry:
                continue
            try:
                prompt_db, sol_db, evolve_state, sched = load_ckpt(epoch, ckpt_dir)
                if sol_db is None or not hasattr(sol_db, "programs"):
                    continue
                solutions = []
                for pid, prog in sol_db.programs.items():
                    solutions.append({
                        "id": getattr(prog, "id", pid),
                        "code": getattr(prog, "code", ""),
                        "fitness": getattr(prog, "fitness", 0),
                        "eval_metrics": getattr(prog, "eval_metrics", {}),
                        "iteration_found": getattr(prog, "iteration_found", None),
                        "parent_id": getattr(prog, "parent_id", None),
                        "generation": getattr(prog, "generation", None),
                    })
                entry["islands"][isl] = solutions
            except Exception:
                continue
    # Sort by epoch and merge islands for same epoch (from different island dirs we loaded same epoch once per island)
    result.sort(key=lambda x: x["epoch"])
    return result


def _save_crash_logs_for_debug(out_dir: str, output_dir: str, task_name: str, run_number: int) -> None:
    """When CodeEvolve exits with non-zero, copy crash.log (and island logs) to a persistent dir for debugging."""
    crash_log_dir = os.path.join(output_dir, "_codeevolve_crash_logs")
    os.makedirs(crash_log_dir, exist_ok=True)
    prefix = f"{task_name}_run{run_number}"
    saved = []
    main_crash = os.path.join(out_dir, "crash.log")
    if os.path.isfile(main_crash):
        dest = os.path.join(crash_log_dir, f"{prefix}_crash.log")
        try:
            shutil.copy2(main_crash, dest)
            saved.append(dest)
        except Exception as e:
            print(f"[science_codeevolve] Could not copy crash.log: {e}", file=sys.stderr)
    for i in range(8):
        isl_crash = os.path.join(out_dir, str(i), "crash.log")
        if os.path.isfile(isl_crash):
            dest = os.path.join(crash_log_dir, f"{prefix}_island{i}_crash.log")
            try:
                shutil.copy2(isl_crash, dest)
                saved.append(dest)
            except Exception as e:
                print(f"[science_codeevolve] Could not copy island {i} crash.log: {e}", file=sys.stderr)
    if saved:
        print(f"[science_codeevolve] Crash logs saved for debugging:", file=sys.stderr)
        for p in saved:
            print(f"  {p}", file=sys.stderr)
        print(f"[science_codeevolve] Check the traceback in these files to fix Island crash (e.g. missing env, import error, or evaluator failure).", file=sys.stderr)


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
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    codeevolve_python: Optional[str] = None,
    env_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Run science_codeevolve for one (task_name, run_number). Returns (exit_code, report).
    report has same structure as TaskEvaluator._generate_report for saving.
    """
    from evaluation.prompt import load_task_prompt
    from evaluation.utils import get_model_identifier, get_run_suffix, get_gif_path, get_evaluation_results_dir, get_gif_base_dir
    from evaluation.verifier import CodeVerifier

    scripts_dir = scripts_dir or _SCRIPTS_DIR
    output_dir = output_dir or get_evaluation_results_dir()
    gif_base_dir = gif_base_dir or get_gif_base_dir()

    task_prompt = load_task_prompt(task_name)

    # AlphaEvolve-style: generate first-round solution (baseline-style) when no initial_code given; then all mutations from it.
    if initial_code is None and task_prompt:
        print("[science_codeevolve] Generating first-round solution (baseline-style: format_initial_prompt + SolverInterface.generate_code)...", flush=True)
        first_round_code = _generate_first_round_solution(
            task_prompt=task_prompt,
            model_type=model_type,
            model_name=model_name,
            run_number=run_number,
            api_base=api_base,
            api_key=api_key,
        )
        if first_round_code:
            initial_code = first_round_code
            print(f"[science_codeevolve] First-round solution generated ({len(first_round_code)} chars). Evolution will mutate from this base.", flush=True)
        else:
            print("[science_codeevolve] First-round generation failed. Not running CodeEvolve (no placeholder).", flush=True)
            model_identifier = get_model_identifier(model_type, model_name)
            run_suffix = get_run_suffix(run_number)
            task_model_method_dir = os.path.join(output_dir, task_name, model_identifier, "science_codeevolve")
            os.makedirs(task_model_method_dir, exist_ok=True)
            report = {
                "task_name": task_name,
                "model_type": model_type,
                "model_name": model_name,
                "method": "science_codeevolve",
                "context": context,
                "max_iterations": 0,
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
                "codeevolve_population_by_epoch": [],
                "timestamp": datetime.now().isoformat(),
            }
            pseudo_suffix = "_pseudo" if context == "all" else ""
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
            report_path = os.path.join(task_model_method_dir, filename)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            return (1, report)

    inpt_dir = _make_inpt_dir(task_name, scripts_dir, initial_code=initial_code, max_steps=max_steps)
    try:
        # When model_type is local but API_BASE points to vLLM (or any OpenAI-compatible server),
        # use API for inference so model is loaded once on server and all islands call API.
        effective_api_base = api_base or os.environ.get("API_BASE")
        if model_type == "local" and not effective_api_base:
            effective_api_base = "http://localhost/v1"
        use_vllm_api = (
            model_type == "local"
            and effective_api_base
            and effective_api_base.rstrip("/") != "http://localhost/v1"
        )
        if use_vllm_api:
            print(f"[science_codeevolve] Using vLLM/API for inference (API_BASE={effective_api_base}); one server load, all islands call API.")
            print(f"[science_codeevolve] To run vLLM on specific GPU(s), start the vLLM server with CUDA_VISIBLE_DEVICES (e.g. CUDA_VISIBLE_DEVICES=7 python -m vllm.entrypoints.openai.api_server ...).")
        cfg = _make_config_yaml(
            task_name, task_prompt, model_type, model_name,
            api_base=api_base, api_key=api_key, seed=42 + run_number,
            use_api_for_inference=use_vllm_api,
        )
        cfg_path = os.path.join(inpt_dir, "config.yaml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

        out_dir = os.path.join(inpt_dir, "out")
        os.makedirs(out_dir, exist_ok=True)
        # Same API defaults as solver_interface so user does not need to export
        from evaluation.solver_interface import SolverInterface
        env_extra = {
            "DAVINCI_SCRIPTS_DIR": scripts_dir,
            "DAVINCI_TASK_NAME": task_name,
            "DAVINCI_MAX_STEPS": str(max_steps),
        }
        if env_overrides:
            import json as _json
            env_extra["DAVINCI_ENV_OVERRIDES"] = _json.dumps(env_overrides)
        if model_type == "local" and not use_vllm_api:
            env_extra["API_BASE"] = "http://localhost/v1"
            env_extra["API_KEY"] = "dummy"
        else:
            env_extra["API_BASE"] = effective_api_base or api_base or SolverInterface.BASE_URL
            env_extra["API_KEY"] = api_key or SolverInterface.API_KEY or "dummy"

        num_epochs = cfg.get("EVOLVE_CONFIG", {}).get("num_epochs", 100)
        num_islands = cfg.get("EVOLVE_CONFIG", {}).get("num_islands", 2)
        init_pop = cfg.get("EVOLVE_CONFIG", {}).get("init_pop", 10)
        ckpt_interval = cfg.get("EVOLVE_CONFIG", {}).get("ckpt", 30)
        print(f"[science_codeevolve] Starting CodeEvolve: task={task_name}, run={run_number}")
        print(f"[science_codeevolve] This round = 1 full CodeEvolve run: num_epochs={num_epochs}, num_islands={num_islands}, init_pop={init_pop} (each epoch: LLM meta-prompt + evolve + sim eval; expect ~minutes per epoch).")
        print(f"[science_codeevolve] Quick test: set CODEEVOLVE_NUM_EPOCHS=5 (or 10) to reduce epochs.")
        print(f"[science_codeevolve] Streaming CodeEvolve output below...")
        exit_code = _run_codeevolve(inpt_dir, cfg_path, out_dir, env_extra=env_extra, codeevolve_python=codeevolve_python, verbose=True)
        print(f"[science_codeevolve] CodeEvolve finished (exit_code={exit_code}). Extracting best solution and population history...")
        if exit_code != 0:
            _save_crash_logs_for_debug(out_dir, output_dir, task_name, run_number)
        best_code = _get_best_code_from_out_dir(out_dir) if exit_code == 0 else None
        # CodeEvolve maintains a population (code library) per island; load from checkpoints
        codeevolve_population_by_epoch = _get_population_history_from_out_dir(out_dir) if exit_code == 0 else []

        if not best_code:
            report = {
                "task_name": task_name,
                "model_type": model_type,
                "model_name": model_name,
                "method": "science_codeevolve",
                "context": context,
                "max_iterations": 0,
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
                "codeevolve_population_by_epoch": codeevolve_population_by_epoch,
                "timestamp": datetime.now().isoformat(),
            }
            return (1 if exit_code != 0 else 0, report)

        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides or {})
        model_identifier = get_model_identifier(model_type, model_name)
        run_suffix = get_run_suffix(run_number)
        gif_dir = os.path.join(gif_base_dir, task_name, model_identifier, "science_codeevolve", "raw", f"{run_suffix}_pass")
        os.makedirs(gif_dir, exist_ok=True)
        gif_path = get_gif_path(gif_dir, context, 1)
        success, score, metrics, error = verifier.verify_code(best_code, headless=True, save_gif_path=gif_path)

        report = {
            "task_name": task_name,
            "model_type": model_type,
            "model_name": model_name,
            "method": "science_codeevolve",
            "context": context,
            "max_iterations": 1,
            "total_iterations": 1,
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
            "codeevolve_population_by_epoch": codeevolve_population_by_epoch,
            "timestamp": datetime.now().isoformat(),
        }
        # Save report to evaluation_results (same path pattern as TaskEvaluator.save_report)
        model_identifier = get_model_identifier(model_type, model_name)
        run_suffix = get_run_suffix(run_number)
        task_model_method_dir = os.path.join(output_dir, task_name, model_identifier, "science_codeevolve")
        os.makedirs(task_model_method_dir, exist_ok=True)
        pseudo_suffix = "_pseudo" if context == "all" else ""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
        report_path = os.path.join(task_model_method_dir, filename)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📄 Evaluation report saved: {report_path}")
        return (0, report)
    finally:
        try:
            shutil.rmtree(inpt_dir, ignore_errors=True)
        except Exception:
            pass
