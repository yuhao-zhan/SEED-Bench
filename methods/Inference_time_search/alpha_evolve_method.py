"""
Alpha Evolve method for 2D_exploration: run OpenEvolve (AlphaEvolve open-source) per task and convert output to 2D report format.
Uses DaVinciBench/baseline/Inference_time_search/openevolve; LLM same as other methods (solver_interface for openai/local).

Follows plan: call run_evolution(..., output_dir, cleanup=False), then take result.best_code from EvolutionResult.

Flow (vs ToT / plain parallel refine):
- Each "iteration" = 1 parent (sampled from DB) + inspirations (context) -> 1 LLM call -> 1 child -> evaluate -> add to DB.
- parallel_evaluations = N means N such iterations run in parallel (N workers); each iteration independently
  samples its own parent from its island. So we get N different parents and N new children per batch, not
  "retrieve N solutions and refine each" (that would be N refines of the same set).

Retrieve/sample (not just by score):
- Parent (which solution to refine): exploration_ratio (default 0.2) = random from island; exploitation_ratio
  (default 0.7) = from MAP-Elites archive (one elite per feature cell); remaining = fitness-weighted from island.
- MAP-Elites: programs binned by feature_dimensions (default ["complexity", "diversity"]); archive = best
  program per (complexity_bin, diversity_bin). So exploitation uses feature-space diversity, not just score.
- Inspirations (prompt context): island best + top by fitness (elite_selection_ratio) + diverse by feature cells
  (nearby in feature space) + random from island.

Checkpoints: every iteration (checkpoint_interval=1) under alphaevolve_checkpoints/{model}/{task}/checkpoints/.

Parallelism (run_evaluate_parallel: one GPU per task):
- OpenEvolve uses ProcessPoolExecutor with parallel_evaluations workers. Each worker runs _run_iteration_worker (sample parent, build prompt, call LLM, evaluate child).
- Local (model_type=local): parallel_evaluations=1 => one worker; that worker loads vLLM once (lazy on first iteration), then does max_iterations rounds of inference in sequence. Single vLLM on one GPU, no OOM.
- OpenAI/API: parallel_evaluations=min(max_iterations,8); workers do HTTP; API accepts concurrent requests.
"""
import os
import sys
import json
import tempfile
import shutil
import glob
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Scripts dir = parent of methods/
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# OpenEvolve repo root (optional: add to path if not installed via pip)
_OPENEVOLVE_ROOT = os.path.normpath(
    os.path.join(_SCRIPTS_DIR, "..", "..", "baseline", "Inference_time_search", "openevolve")
)
# Checkpoints saved under methods/Inference_time_search/alphaevolve_checkpoints/{model}/{task}/checkpoints/
_ALPHAEVOLVE_CHECKPOINTS_BASE = os.path.normpath(os.path.join(os.path.dirname(__file__), "alphaevolve_checkpoints"))

EVOLVE_START = "# EVOLVE-BLOCK-START"
EVOLVE_END = "# EVOLVE-BLOCK-END"

# Initial solution is ONLY from first round (baseline-style: format_initial_prompt + SolverInterface.generate_code).
# No placeholder template: if first round fails, we do not run evolution.


def _generate_first_round_solution(
    task_prompt: Dict[str, Any],
    model_type: str,
    model_name: str,
    run_number: int,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Generate first-round solution the same way as baseline: format_initial_prompt + SolverInterface.generate_code.
    Used for non-local (e.g. openai) models. Returns extracted code, or None on failure.
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
        print(f"[alpha_evolve] First-round generation failed: {e}")
        return None


# First-round generation needs enough tokens for reasoning + full code (same as SolverInterface local: 65536).
# OpenEvolve config uses 4096 which truncates; use this for the one-off first-round call only.
FIRST_ROUND_MAX_TOKENS = 65536


def _generate_first_round_with_hf_llm(
    task_prompt: Dict[str, Any],
    hf_llm: Any,
) -> Optional[str]:
    """
    Generate first-round solution using the same prompt and system message as baseline,
    but via the pre-created OpenEvolve HuggingFaceLLM so we don't load vLLM twice (local only).
    Uses a larger max_tokens so reasoning + full code are not truncated (config default 4096 is too small).
    Returns extracted code, or None on failure.
    """
    from evaluation.prompt import format_initial_prompt
    from evaluation.solver_interface import SolverInterface

    prompt = format_initial_prompt(task_prompt)
    system_message = SolverInterface.SYSTEM_PROMPT
    try:
        raw = hf_llm._sync_generate_with_context(
            system_message=system_message,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=FIRST_ROUND_MAX_TOKENS,
        )
        solver = SolverInterface(model_type="mock", model_name="mock")
        code = solver._extract_code(raw)
        if not code or len(code.strip()) < 50 or "def build_agent" not in code:
            return None
        return code
    except Exception as e:
        print(f"[alpha_evolve] First-round generation (hf_llm) failed: {e}")
        return None



def _ensure_openevolve():
    """Ensure openevolve package is importable (pip install -e or path)."""
    try:
        import openevolve  # noqa: F401
        return
    except ImportError:
        pass
    if os.path.isdir(_OPENEVOLVE_ROOT) and _OPENEVOLVE_ROOT not in sys.path:
        sys.path.insert(0, _OPENEVOLVE_ROOT)
    try:
        import openevolve  # noqa: F401
        return
    except ImportError:
        raise ImportError(
            "openevolve not found. Install with: pip install -e /path/to/DaVinciBench/baseline/Inference_time_search/openevolve"
        )


def _build_openevolve_config(
    model_type: str,
    model_name: str,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    seed: int = 42,
    max_iterations: int = 100,
    task_prompt: Optional[Dict[str, Any]] = None,
):
    _ensure_openevolve()
    from openevolve.config import Config, LLMModelConfig
    from openevolve.prompt.templates import BASE_SYSTEM_TEMPLATE
    from evaluation.solver_interface import SolverInterface

    config = Config()
    config.max_iterations = max_iterations
    config.random_seed = seed
    # When we have baseline-generated initial, we set exclude_initial_from_parent_sampling=False so it gets added to DB.
    # Default True: placeholder not added; bootstrap produces first child. Overridden to False when first round succeeds.
    config.database.exclude_initial_from_parent_sampling = True
    config.evaluator.timeout = 300
    config.evaluator.cascade_evaluation = False
    # Save checkpoint every iteration so prompts from 2nd iteration include history from program database
    config.checkpoint_interval = 1
    # Parallelism: same as OpenEvolve repo (e.g. parallel_evaluations=4). Local model: use serial vLLM requests (load model once, then run all inference requests one-by-one in-process; no process pool).
    if model_type == "local":
        config.evaluator.parallel_evaluations = 4  # same as repo default (default_config.yaml)
        config.evaluator.serial_requests_for_local = True  # in-process, one model load, serial vLLM requests
        config.max_tasks_per_child = None
    else:
        config.evaluator.parallel_evaluations = min(max(max_iterations, 1), 8)

    if model_type == "local":
        # In-process HuggingFace model (same as baseline/sys_feedback): no API, load model directly via init_client
        from methods.Inference_time_search.local_llm_for_openevolve import create_hf_llm
        config.llm.models = [
            LLMModelConfig(
                name=model_name,  # model path or HF name for loading
                init_client=create_hf_llm,
                temperature=0.7,
                top_p=0.95,
                max_tokens=65536,
            )
        ]
    else:
        # openai: use API (solver_interface BASE_URL / API_KEY)
        base = api_base or SolverInterface.BASE_URL
        key = api_key or SolverInterface.API_KEY
        config.llm.models = [
            LLMModelConfig(
                name=model_name,
                api_base=base,
                api_key=key,
                temperature=0.7,
                top_p=0.95,
                max_tokens=65536,
            )
        ]
        config.llm.api_base = base
        config.llm.api_key = key

    # Inject 2D task context into evolution prompt: same task description, success criteria, API, and demo as baseline first round.
    # OpenEvolve sampler prepends task_context + task_context_demo to the user message so every evolution prompt has them.
    if task_prompt:
        task_desc = task_prompt.get("task_description") or ""
        success_criteria = task_prompt.get("success_criteria") or ""
        primitives_api = task_prompt.get("primitives_api") or ""
        task_block = (
            "\n\n# Task Description\n" + task_desc
            + "\n\n# Success Criteria\n" + success_criteria
            + "\n\n# Available API (Primitives)\n" + primitives_api
        )
        config.prompt.system_message = BASE_SYSTEM_TEMPLATE.strip() + task_block
        # User message starts with this (sampler prepends task_context then task_context_demo)
        user_task_block = (
            "# Task (required for evolution)\n\n"
            "# Task Description\n" + task_desc
            + "\n\n# Success Criteria\n" + success_criteria
            + "\n\n# Available Primitives API\n" + primitives_api
        )
        config.prompt.task_context = user_task_block
        try:
            from evaluation.prompt import INITIAL_DEMONSTRATION
            config.prompt.task_context_demo = (INITIAL_DEMONSTRATION or "").strip()
        except ImportError as e:
            print(f"[alpha_evolve] Warning: could not load INITIAL_DEMONSTRATION: {e}")
            config.prompt.task_context_demo = ""
        if not (config.prompt.task_context or "").strip():
            print("[alpha_evolve] Warning: task_context is empty - evolution prompts may lack task description/API")
    # So the initial program shows a clear description instead of "Unknown changes" in evolution prompts
    config.prompt.initial_changes_description = "Initial baseline solution (first round)."
    return config


def _build_failure_report(
    task_name: str,
    model_identifier: str,
    run_suffix: str,
    task_model_method_dir: str,
    error: str,
    task_prompt: Optional[Dict[str, Any]] = None,
    model_type: str = "",
    model_name: str = "",
    context: str = "all",
) -> Dict[str, Any]:
    """Build and save a failure report (e.g. first round failed, no placeholder)."""
    task_prompt = task_prompt or {}
    report = {
        "task_name": task_name,
        "model_type": model_type,
        "model_name": model_name,
        "method": "alpha_evolve",
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
        "evolution_note": error,
        "timestamp": datetime.now().isoformat(),
    }
    pseudo_suffix = "_pseudo" if context == "all" else ""
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
    report_path = os.path.join(task_model_method_dir, filename)
    os.makedirs(task_model_method_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Failure report saved: {report_path}")
    return report


def _make_work_dir(
    task_name: str,
    scripts_dir: str,
    initial_code: str,
    max_steps: int = 10000,
) -> Tuple[str, str, str]:
    """Create temp dir with initial_program.py (baseline-generated initial only) and evaluate.py. Requires initial_code."""
    if not initial_code or not initial_code.strip():
        raise ValueError("initial_code is required (first-round baseline solution); no placeholder.")
    work_dir = tempfile.mkdtemp(prefix="alpha_evolve_2d_")
    solution = initial_code.strip()
    if EVOLVE_START not in solution:
        solution = f"{EVOLVE_START}\n{solution}\n{EVOLVE_END}"
    program_path = os.path.join(work_dir, "initial_program.py")
    with open(program_path, "w", encoding="utf-8") as f:
        f.write(solution)

    # Copy openevolve_2d_evaluate_adapter.py as evaluate.py (openevolve expects evaluate(program_path))
    adapter_path = os.path.join(os.path.dirname(__file__), "openevolve_2d_evaluate_adapter.py")
    evaluator_path = os.path.join(work_dir, "evaluate.py")
    shutil.copy2(adapter_path, evaluator_path)
    return work_dir, program_path, evaluator_path


def _program_to_iteration_entry(
    program: Any,
    iteration: int,
    prompts_by_program: Optional[Dict[str, Dict]] = None,
) -> Dict[str, Any]:
    """Build one iteration_history entry from an OpenEvolve Program (from checkpoint)."""
    prompts = getattr(program, "prompts", None) or (
        (prompts_by_program or {}).get(program.id) if prompts_by_program else None
    )
    user_prompt = None
    raw_llm_output = None
    if prompts:
        if isinstance(prompts, dict):
            for _k, v in prompts.items():
                if isinstance(v, dict):
                    user_prompt = v.get("user") or user_prompt
                    raw_llm_output = v.get("responses", [None])[0] if v.get("responses") else raw_llm_output
                break
        else:
            user_prompt = str(prompts)
    metrics = program.metrics or {}
    score_f = float(metrics.get("combined_score", metrics.get("score", 0.0)))
    if score_f == 0.0 and metrics:
        nums = [v for v in metrics.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums:
            score_f = sum(nums) / len(nums)
    feedback = metrics.get("failure_reason") or metrics.get("error") or (str(metrics) if metrics else None)
    return {
        "iteration": iteration,
        "prompt": user_prompt,
        "code": program.code,
        "raw_llm_output": raw_llm_output,
        "token_usage": {},
        "score": score_f,
        "success": bool(metrics.get("success", False)),
        "error": metrics.get("error"),
        "feedback": feedback,
        "metrics": metrics,
        "metrics_summary": {k: v for k, v in metrics.items() if k != "step_count"},
    }


def _build_iteration_history_from_database(
    database: Any, max_iterations: int
) -> List[Dict[str, Any]]:
    """
    Build iteration_history with one entry per round 0..max_iterations.
    Fills gaps with a placeholder when a round produced no valid program (e.g. LLM returned invalid diff).
    When multiple programs share the same iteration_found, keep the one with best combined_score.
    """
    programs = list(database.programs.values())
    prompts_by = getattr(database, "prompts_by_program", None) or {}
    # Best program per iteration_found (by combined_score)
    by_iter: Dict[int, Any] = {}
    for p in programs:
        i = getattr(p, "iteration_found", 0)
        score = float((p.metrics or {}).get("combined_score", (p.metrics or {}).get("score", 0.0)))
        if i not in by_iter or score > float((by_iter[i].metrics or {}).get("combined_score", (by_iter[i].metrics or {}).get("score", 0.0))):
            by_iter[i] = p
    # One entry per round 1..max_iterations only. Never expose iteration 0 (initial placeholder) in the report.
    result: List[Dict[str, Any]] = []
    for i in range(1, max_iterations + 1):
        if i in by_iter:
            result.append(_program_to_iteration_entry(by_iter[i], i, prompts_by))
        else:
            result.append({
                "iteration": i,
                "prompt": None,
                "code": None,
                "raw_llm_output": None,
                "token_usage": {},
                "score": None,
                "success": False,
                "error": "No valid program (LLM did not return valid SEARCH/REPLACE or evaluation failed).",
                "feedback": "Skipped round: no child added.",
                "metrics": {},
                "metrics_summary": {},
                "skipped": True,
            })
    return result


def _build_solutions_organized(
    database: Any,
    task_name: str,
    model_identifier: str,
    run_suffix: str,
) -> Dict[str, Any]:
    """Build a logically organized export of all solutions (by island and by iteration)."""
    archive = getattr(database, "archive", None) or set()
    islands = getattr(database, "islands", None) or []
    programs = database.programs

    by_island = []
    for island_id, island_set in enumerate(islands):
        pid_list = list(island_set) if hasattr(island_set, "__iter__") and not isinstance(island_set, dict) else []
        island_programs = []
        for pid in pid_list:
            p = programs.get(pid)
            if not p:
                continue
            code_p = getattr(p, "code", "")
            iter_p = getattr(p, "iteration_found", 0)
            island_programs.append({
                "id": p.id,
                "parent_id": getattr(p, "parent_id", None),
                "iteration_found": iter_p,
                "code": code_p,
                "metrics": getattr(p, "metrics", {}),
                "in_archive": pid in archive,
                "is_initial_placeholder": iter_p == 0 and "Minimal placeholder" in (code_p or ""),
            })
        island_programs.sort(key=lambda x: (x["iteration_found"], x["id"]))
        by_island.append({
            "island_id": island_id,
            "program_ids": pid_list,
            "programs": island_programs,
        })

    all_programs_list = list(programs.values())
    all_programs_list.sort(key=lambda p: (getattr(p, "iteration_found", 0), getattr(p, "timestamp", 0), p.id))
    by_iteration = []
    all_programs_with_code = []
    for p in all_programs_list:
        island_id = (p.metadata or {}).get("island")
        by_iteration.append({
            "iteration": getattr(p, "iteration_found", 0),
            "program_id": p.id,
            "parent_id": getattr(p, "parent_id", None),
            "island_id": island_id,
        })
        code = getattr(p, "code", "")
        iter_found = getattr(p, "iteration_found", 0)
        # Mark initial programs that look like placeholder (should not appear when first-round baseline is used)
        is_placeholder = iter_found == 0 and "Minimal placeholder" in (code or "")
        all_programs_with_code.append({
            "id": p.id,
            "parent_id": getattr(p, "parent_id", None),
            "iteration_found": iter_found,
            "island_id": island_id,
            "code": code,
            "metrics": getattr(p, "metrics", {}),
            "in_archive": p.id in archive,
            "is_initial_placeholder": is_placeholder,
        })

    return {
        "metadata": {
            "task_name": task_name,
            "model_identifier": model_identifier,
            "run_suffix": run_suffix,
            "num_programs": len(programs),
            "num_islands": len(islands),
            "archive_size": len(archive),
            "timestamp": datetime.now().isoformat(),
        },
        "all_programs": all_programs_with_code,
        "by_island": by_island,
        "by_iteration": by_iteration,
        "archive_program_ids": list(archive),
    }


def _load_database_from_checkpoint(out_dir: str, config: Any) -> Tuple[Optional[Any], int]:
    """
    Load ProgramDatabase from openevolve's checkpoint dir (output_dir/checkpoints/checkpoint_*).
    Returns (database, total_iterations) or (None, 0) if no checkpoint.
    """
    _ensure_openevolve()
    from openevolve.database import ProgramDatabase

    checkpoint_dir = os.path.join(out_dir, "checkpoints")
    if not os.path.isdir(checkpoint_dir):
        return (None, 0)
    candidates = glob.glob(os.path.join(checkpoint_dir, "checkpoint_*"))
    if not candidates:
        return (None, 0)
    # Latest by iteration number (checkpoint_1, checkpoint_2, ...)
    def iter_num(p: str) -> int:
        try:
            return int(os.path.basename(p).replace("checkpoint_", ""))
        except ValueError:
            return 0
    latest = max(candidates, key=iter_num)
    if not os.path.exists(os.path.join(latest, "metadata.json")):
        return (None, 0)
    try:
        db = ProgramDatabase(config.database)
        db.load(latest)
        total = getattr(db, "last_iteration", 0) or (
            max((p.iteration_found for p in db.programs.values()), default=0)
        )
        return (db, total)
    except Exception:
        return (None, 0)


def run_single_task(
    task_name: str,
    run_number: int,
    model_type: str,
    model_name: str,
    context: str = "all",
    max_iterations: int = 100,
    max_steps: int = 10000,
    scripts_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    gif_base_dir: Optional[str] = None,
    initial_code: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    env_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Run alpha_evolve (OpenEvolve) for one (task_name, run_number). Returns (exit_code, report).
    report has same structure as TaskEvaluator._generate_report for saving.

    Per plan: call run_evolution(initial_program, evaluator, config, iterations=config.max_iterations, output_dir, cleanup=False),
    then take result.best_code from EvolutionResult. When openevolve writes checkpoints to output_dir/checkpoints/,
    we load the latest checkpoint to build iteration_history and save program_database to evaluation_results.
    """
    from evaluation.prompt import load_task_prompt
    from evaluation.utils import get_model_identifier, get_run_suffix, get_gif_path, get_evaluation_results_dir, get_gif_base_dir
    from evaluation.verifier import CodeVerifier

    _ensure_openevolve()
    from openevolve import run_evolution

    scripts_dir = scripts_dir or _SCRIPTS_DIR
    output_dir = output_dir or get_evaluation_results_dir()
    gif_base_dir = gif_base_dir or get_gif_base_dir()
    model_identifier = get_model_identifier(model_type, model_name)
    run_suffix = get_run_suffix(run_number)
    task_model_method_dir = os.path.join(output_dir, task_name, model_identifier, "alpha_evolve")
    os.makedirs(task_model_method_dir, exist_ok=True)

    task_prompt = load_task_prompt(task_name)
    config = _build_openevolve_config(
        model_type=model_type,
        model_name=model_name,
        api_base=api_base,
        api_key=api_key,
        seed=42 + run_number,
        max_iterations=max_iterations,
        task_prompt=task_prompt,
    )

    # Reject minimal placeholder if passed as initial_code (all evolution must be on first-round baseline)
    _PLACEHOLDER_MARKER = "Minimal placeholder"
    if initial_code and _PLACEHOLDER_MARKER in initial_code:
        print(f"[alpha_evolve] Ignoring placeholder initial_code; generating first-round solution instead.")
        initial_code = None
    # First round = same as baseline: format_initial_prompt + same system prompt -> generate_code (one initial solution).
    # For local model: reuse OpenEvolve's LLM so we don't load vLLM twice (avoids OOM on second load).
    # For openai: use SolverInterface.generate_code.
    if initial_code is None and task_prompt:
        if model_type == "local":
            from methods.Inference_time_search.local_llm_for_openevolve import create_hf_llm
            model_cfg = config.llm.models[0]
            pre_created_hf_llm = create_hf_llm(model_cfg)
            config.llm.models[0].init_client = lambda _: pre_created_hf_llm
            print(f"[alpha_evolve] Generating first-round solution (baseline-style, reusing OpenEvolve LLM to avoid double vLLM load)...")
            first_round_code = _generate_first_round_with_hf_llm(task_prompt=task_prompt, hf_llm=pre_created_hf_llm)
        else:
            print(f"[alpha_evolve] Generating first-round solution (baseline-style: format_initial_prompt + SolverInterface.generate_code)...")
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
            print(f"[alpha_evolve] First-round solution generated ({len(first_round_code)} chars). Starting evolution.")
            config.database.exclude_initial_from_parent_sampling = False
        else:
            # First round = baseline-style generation only. No placeholder; do not run evolution.
            print(f"[alpha_evolve] First-round generation failed. Not running evolution (no placeholder).")
            return 1, _build_failure_report(
                task_name=task_name,
                model_identifier=model_identifier,
                run_suffix=run_suffix,
                task_model_method_dir=task_model_method_dir,
                error="First-round (baseline-style) solution generation failed; no evolution run.",
                task_prompt=task_prompt,
                model_type=model_type,
                model_name=model_name,
                context=context,
            )
    else:
        if initial_code is not None:
            config.database.exclude_initial_from_parent_sampling = False
    if initial_code is None:
        print(f"[alpha_evolve] No initial solution (first round failed or no task_prompt). Exiting.")
        return 1, _build_failure_report(
            task_name=task_name,
            model_identifier=model_identifier,
            run_suffix=run_suffix,
            task_model_method_dir=task_model_method_dir,
            error="No initial solution available.",
            task_prompt=task_prompt,
            model_type=model_type,
            model_name=model_name,
            context=context,
        )
    work_dir, program_path, evaluator_path = _make_work_dir(
        task_name, scripts_dir, initial_code=initial_code, max_steps=max_steps
    )
    # Checkpoints under alphaevolve_checkpoints/{model}/{task}/checkpoints/checkpoint_1, ...
    out_dir = os.path.join(_ALPHAEVOLVE_CHECKPOINTS_BASE, model_identifier, task_name)
    os.makedirs(out_dir, exist_ok=True)

    env_before = {}
    result = None
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

        print(f"[alpha_evolve] Starting OpenEvolve: task={task_name}, run={run_number}, iterations={max_iterations}")
        result = run_evolution(
            initial_program=program_path,
            evaluator=evaluator_path,
            config=config,
            iterations=max_iterations,
            output_dir=out_dir,
            cleanup=False,
        )
    finally:
        for k, v in env_before.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    best_code = result.best_code if result else None
    best_metrics = result.metrics if result else {}

    # Build iteration_history and optionally save program_database from openevolve's checkpoint (plan: use run_evolution; history/DB from checkpoint when present)
    iteration_history = []
    total_iterations = max_iterations
    evolution_note = None
    database, loaded_total = (None, 0)
    if config is not None:
        database, loaded_total = _load_database_from_checkpoint(out_dir, config)
    if database and database.programs:
        # Prefer best code from loaded DB (same as result, but ensures we use DB's best_program_id)
        if getattr(database, "best_program_id", None):
            best_in_db = database.get(database.best_program_id)
            if best_in_db and getattr(best_in_db, "code", None):
                best_code = best_in_db.code
                best_metrics = getattr(best_in_db, "metrics", None) or best_metrics
        iteration_history = _build_iteration_history_from_database(database, max_iterations)
        total_iterations = getattr(database, "last_iteration", None) or loaded_total or max_iterations
        # If only the initial program (iteration_found==0) exists, evolution added no children (e.g. all iterations failed)
        num_evolved = sum(1 for p in database.programs.values() if getattr(p, "iteration_found", 0) > 0)
        if num_evolved == 0 and len(database.programs) == 1:
            evolution_note = (
                "No new programs were added during evolution (only the initial program in the database). "
                "This can happen if every iteration failed (e.g. CUDA fork error before using spawn). "
                "Re-run with multiprocessing spawn enabled to get many islands and code variants."
            )
            print(f"Note: {evolution_note}")
        elif database and len(database.programs) < 1 + max_iterations:
            shortfall = (1 + max_iterations) - len(database.programs)
            evolution_note = (
                f"Only {len(database.programs)} programs were added over {max_iterations} iterations "
                f"({shortfall} iterations did not produce a valid SEARCH/REPLACE diff from the LLM, so no child was added). "
                "iteration_history and solutions_organized list one entry per program in the database."
            )
            print(f"Note: {evolution_note}")
        pseudo_suffix = "_pseudo" if context == "all" else ""
        date_str = datetime.now().strftime("%Y%m%d")
        program_db_dir = os.path.join(
            task_model_method_dir,
            f"program_database_{context}_{run_suffix}_pass_{date_str}{pseudo_suffix}",
        )
        try:
            database.save(program_db_dir, iteration=total_iterations)
            print(f"Program database saved: {program_db_dir}")
            # Save all solutions in an organized structure (by island and by iteration)
            try:
                organized = _build_solutions_organized(
                    database, task_name, model_identifier, run_suffix
                )
                organized_path = os.path.join(program_db_dir, "solutions_organized.json")
                with open(organized_path, "w", encoding="utf-8") as f:
                    json.dump(organized, f, indent=2, ensure_ascii=False)
                print(f"Solutions organized export saved: {organized_path}")
            except Exception as e_org:
                print(f"Warning: could not save solutions_organized.json: {e_org}")
        except Exception as e:
            print(f"Warning: could not save program database: {e}")
    if not iteration_history and best_code:
        # Fallback: single entry from EvolutionResult (plan default when no checkpoint)
        score_f = float(best_metrics.get("combined_score", best_metrics.get("score", 0.0)))
        iteration_history = [
            {
                "iteration": 1,
                "prompt": None,
                "code": best_code,
                "raw_llm_output": None,
                "token_usage": {},
                "score": score_f,
                "success": bool(best_metrics.get("success", False)),
                "error": best_metrics.get("error"),
                "feedback": best_metrics.get("failure_reason") or best_metrics.get("error"),
                "metrics": best_metrics,
                "metrics_summary": {k: v for k, v in best_metrics.items() if k != "step_count"},
            }
        ]

    if not best_code:
        report = {
            "task_name": task_name,
            "model_type": model_type,
            "model_name": model_name,
            "method": "alpha_evolve",
            "context": context,
            "max_iterations": max_iterations,
            "total_iterations": total_iterations,
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
            "iteration_history": iteration_history,
            "evolution_scale_note": (
                f"Search scale: parallel_evaluations=4 (serial for local), max_iterations={max_iterations} → at most {1 + max_iterations} programs. "
                "Same as baseline/openevolve; for more search use --max-iterations 100 or API."
            ),
            "timestamp": datetime.now().isoformat(),
        }
        shutil.rmtree(work_dir, ignore_errors=True)
        return (1, report)

    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides or {})
    gif_dir = os.path.join(gif_base_dir, task_name, model_identifier, "alpha_evolve", "raw", f"{run_suffix}_pass")
    os.makedirs(gif_dir, exist_ok=True)
    gif_path = get_gif_path(gif_dir, context, 1)
    success, score, metrics, error = verifier.verify_code(best_code, headless=True, save_gif_path=gif_path)

    # Search scale: one entry per round in iteration_history; "No valid program" = that round had no child (invalid SEARCH/REPLACE or eval failed).
    evolution_scale_note = (
        f"Search scale: parallel_evaluations=4 (same as repo), local uses serial vLLM requests (one model load). max_iterations={max_iterations} → at most {1 + max_iterations} programs. "
        "iteration_history has one entry per round (1..max_iterations); each round adds at most one program. "
        "'No valid program' means that round the LLM did not return valid SEARCH/REPLACE diff or evaluation failed, so no child was added. "
        "Same algorithm as DaVinciBench/baseline/Inference_time_search/openevolve. "
        "For more search: increase --max-iterations (e.g. 100) or use API mode with multiple workers."
    )
    report = {
        "task_name": task_name,
        "model_type": model_type,
        "model_name": model_name,
        "method": "alpha_evolve",
        "context": context,
        "max_iterations": max_iterations,
        "total_iterations": total_iterations,
        "best_score": float(score),
        "final_score": float(score),
        "success": success,
        "best_metrics": metrics or best_metrics,
        "final_metrics": metrics or best_metrics,
        "best_code": best_code,
        "token_statistics": {},
        "task_prompt": {
            "initial_prompt": None,
            "task_description": task_prompt.get("task_description", ""),
            "success_criteria": task_prompt.get("success_criteria", ""),
            "primitives_api": task_prompt.get("primitives_api", ""),
        },
        "iteration_history": iteration_history,
        "evolution_scale_note": evolution_scale_note,
        "timestamp": datetime.now().isoformat(),
    }
    if evolution_note is not None:
        report["evolution_note"] = evolution_note

    pseudo_suffix = "_pseudo" if context == "all" else ""
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{context}_{run_suffix}_pass_{date_str}{pseudo_suffix}.json"
    report_path = os.path.join(task_model_method_dir, filename)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Evaluation report saved: {report_path}")
    shutil.rmtree(work_dir, ignore_errors=True)
    return (0, report)
