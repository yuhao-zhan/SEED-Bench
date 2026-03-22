#!/usr/bin/env python3
"""
Data-parallel From-Scratch evaluation (same CLI paradigm as run_evaluate_parallel).

- Work items: (task_name, stage_id) — one per task env (Initial, Stage-1, ...). Each task
  has 5 envs (Initial + 4 stages); each env is one process. Run once (no 1st/2nd/3rd pass).
- Local: split work across N GPUs; each GPU runs one (task, stage_id) at a time.
- API: run all work items in parallel via ThreadPoolExecutor.
- Underlying execution: from-scratch (task description + demonstrations + requirements,
  with current env's physical values in the prompt; no reference solution, no mutation).
- Results saved as context_{stage_id}.json (e.g. previous_Initial.json, all_Stage-1.json).

Usage (from DaVinciBench/2D_exploration/scripts/):
  python evaluation/run_evaluate_parallel_from_scratch.py --task category_1 --num-workers 8 \\
    --model-type local --model-name /path/to/model --max-iterations 20 --method baseline --context all

  python evaluation/run_evaluate_parallel_from_scratch.py --task category_1 --api-parallel 16 \\
    --model-type openai --model-name deepseek-v3.2 --max-iterations 20 --method baseline --context all
"""
import os
import signal
import sys
import subprocess
import argparse
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.parallel_launch_gpu import parallel_local_use_tp2


def resolve_task_list(task_spec: str):
    from evaluation.evaluate import resolve_task_list as _resolve
    return _resolve(task_spec)


# From-scratch results go here (same layout as evaluation_results).
SCRATCH_OUTPUT_DIR = "evaluation_results_scratch"


def collect_work_items_from_scratch(task_list, model_type, model_name, method, context):
    """Collect (task_name, stage_id) for runs that are not complete. One per env (Initial + Stage-1..4)."""
    from evaluation.evaluate_cross_mutated import get_all_stages
    from evaluation.utils import run_is_complete

    work_items = []
    for task_name in task_list:
        try:
            all_envs = get_all_stages(task_name)
        except Exception:
            continue
        for env in all_envs:
            stage_id = env.get("stage_id", "Initial")
            if not run_is_complete(
                task_name=task_name,
                model_type=model_type,
                model_name=model_name,
                method=method,
                context=context,
                mutated_task_name=stage_id,
                results_base_dir=SCRATCH_OUTPUT_DIR,
            ):
                work_items.append((task_name, stage_id))
    return work_items


def _gpu_spec_to_cuda_and_device(spec):
    if isinstance(spec, tuple):
        a, b = spec
        return f"{a},{b}", "cuda:0,1", f"{a},{b}"
    return str(spec), "cuda:0", str(spec)


def run_local_workers(gpu_specs, work_chunks, scripts_dir, base_argv):
    """Run one subprocess per (task_name, stage_id) per chunk."""
    results = []
    print_lock = threading.Lock()

    def worker(gpu_spec, chunk):
        cuda_visible, device_str, gpu_label = _gpu_spec_to_cuda_and_device(gpu_spec)
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = cuda_visible
        env["PYTHONUNBUFFERED"] = "1"
        env["VLLM_DISABLE_COMPILE_CACHE"] = "1"
        all_ok = True
        last_code = 0
        last_out_lines = []
        for (task_name, stage_id) in chunk:
            cmd = base_argv + ["--device", device_str] + ["--task", task_name, "--stage-id", stage_id]
            proc = None
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=scripts_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
                for line in iter(proc.stdout.readline, ""):
                    if "Loading weights" in line or "Materializing param" in line:
                        continue
                    with print_lock:
                        print(f"[GPU {gpu_label}] {line}", end="", flush=True)
                proc.wait()
                last_code = proc.returncode
                if last_code != 0:
                    all_ok = False
            except Exception as e:
                all_ok = False
                last_code = -1
                last_out_lines = [str(e)]
                with print_lock:
                    print(f"[GPU {gpu_label}] Exception: {e}", flush=True)
            finally:
                if proc is not None and proc.pid is not None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
        results.append((gpu_label, all_ok, last_code, last_out_lines))

    threads = []
    for gpu_spec, chunk in zip(gpu_specs, work_chunks):
        if not chunk:
            continue
        t = threading.Thread(target=worker, args=(gpu_spec, chunk))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    return results


def run_api_parallel(work_items, args, scripts_dir):
    """Run all (task_name, stage_id) in parallel via ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    evaluate_script = os.path.join("evaluation", "evaluate_from_scratch.py")
    base_argv = _build_base_argv(args, scripts_dir, evaluate_script)
    max_workers = min(len(work_items), getattr(args, "api_parallel", 16))
    results = []

    def run_one(item):
        task_name, stage_id = item
        cmd = base_argv + ["--task", task_name, "--stage-id", stage_id]
        proc = subprocess.run(
            cmd,
            cwd=scripts_dir,
            capture_output=True,
            text=True,
            timeout=3600 * 2,
        )
        return (task_name, stage_id, proc.returncode)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(run_one, item): item for item in work_items}
        for future in as_completed(future_to_item):
            try:
                results.append(future.result())
            except Exception as exc:
                item = future_to_item[future]
                print(f"❌ {item[0]} {item[1]} failed: {exc}")
                results.append((item[0], item[1], 1))
    return results


def _build_base_argv(args, scripts_dir, evaluate_script):
    """Build argv for evaluate_from_scratch.py (same args as backup run_evaluate_parallel)."""
    base = [
        sys.executable,
        evaluate_script,
        "--model-type", args.model_type,
        "--model-name", args.model_name,
        "--max-iterations", str(args.max_iterations),
        "--max-steps", str(args.max_steps),
        "--method", args.method,
        "--context", args.context,
        "--output-dir", SCRATCH_OUTPUT_DIR,
        "--no-save-gif",
    ]
    if args.model_path:
        base += ["--model-path", args.model_path]
    if args.api_key:
        base += ["--api-key", args.api_key]
    if getattr(args, "method", None) == "reflexion" and getattr(args, "reflect_model_name", None):
        base += ["--reflect-model-name", args.reflect_model_name]
    if getattr(args, "method", None) == "textgrad" and getattr(args, "textgrad_engine_name", None):
        base += ["--textgrad-engine-name", args.textgrad_engine_name]
    if getattr(args, "method", None) == "a_mem_sys" and getattr(args, "a_mem_sys_llm_model", None):
        base += ["--a-mem-llm-model", getattr(args, "a_mem_sys_llm_model", "deepseek-v3.2")]
    if getattr(args, "method", None) == "ace":
        base += ["--ace-reflector-model", getattr(args, "ace_reflector_model", "deepseek-v3.2")]
        base += ["--ace-curator-model", getattr(args, "ace_curator_model", "deepseek-v3.2")]
    if getattr(args, "method", None) == "tree_of_thought":
        base += ["--n-select-sample", str(getattr(args, "n_select_sample", 3))]
        base += ["--n-generate-sample", str(getattr(args, "n_generate_sample", 2))]
    if getattr(args, "method", None) == "reasoning_bank":
        base += ["--reasoning-bank-k", str(getattr(args, "reasoning_bank_k", 2))]
    if getattr(args, "method", None) == "ragen":
        base += ["--ragen-n-rollouts", str(getattr(args, "ragen_n_rollouts", 8))]
        base += ["--ragen-ppo-epochs", str(getattr(args, "ragen_ppo_epochs", 2))]
    if getattr(args, "method", None) == "soar":
        base += ["--soar-generations", str(getattr(args, "soar_generations", 2))]
        base += ["--soar-k-candidates", str(getattr(args, "soar_k_candidates", 4))]
    if getattr(args, "method", None) == "discover":
        base += ["--discover-num-epochs", str(getattr(args, "discover_num_epochs", 50))]
        base += ["--discover-group-size", str(getattr(args, "discover_group_size", 8))]
        base += ["--discover-groups-per-batch", str(getattr(args, "discover_groups_per_batch", 64))]
        base += ["--discover-learning-rate", str(getattr(args, "discover_learning_rate", 4e-5))]
        base += ["--discover-adv-estimator", getattr(args, "discover_adv_estimator", "entropic")]
        base += ["--discover-adv-estimator-beta", str(getattr(args, "discover_adv_estimator_beta", 2.0))]
        base += ["--discover-loss-fn", getattr(args, "discover_loss_fn", "importance_sampling")]
        base += ["--discover-lora-rank", str(getattr(args, "discover_lora_rank", 32))]
        base += ["--discover-max-tokens", str(getattr(args, "discover_max_tokens", 65536))]
        base += ["--discover-temperature", str(getattr(args, "discover_temperature", 1.0))]
        base += ["--discover-num-substeps", str(getattr(args, "discover_num_substeps", 1))]
        base += ["--discover-max-expansion-rounds", str(getattr(args, "discover_max_expansion_rounds", 2))]
    if getattr(args, "method", None) == "genome" and getattr(args, "genome_best_lora_path", None):
        base += ["--genome-best-lora-path", args.genome_best_lora_path]
    if getattr(args, "method", None) == "theta_evolve":
        base += ["--theta-evolve-num-rollout", str(getattr(args, "theta_evolve_num_rollout", 10000))]
        base += ["--theta-evolve-rollout-batch-size", str(getattr(args, "theta_evolve_rollout_batch_size", 32))]
    if getattr(args, "method", None) == "expel":
        base += ["--expel-max-rounds", str(getattr(args, "expel_max_rounds", 8))]
        base += ["--expel-max-num-rules", str(getattr(args, "expel_max_num_rules", 20))]
    return base


def main():
    parser = argparse.ArgumentParser(
        description="Run from-scratch evaluation in data-parallel: (task, stage_id) work items, one run per env."
    )
    parser.add_argument("--task", type=str, required=True,
                        help="Task spec: category_X_YY, category_X, or all")
    parser.add_argument(
        "--num-workers",
        type=int,
        default=8,
        help="Parallel worker count for local runs. For Parameter_Policy methods, 32B/30B, or "
        "--tensor-parallel-2: pass exactly 2× this many IDs in --gpus (e.g. --num-workers 1 --gpus 0,1). Default: 8",
    )
    parser.add_argument(
        "--gpus",
        type=str,
        default=None,
        help="Comma-separated GPU IDs. 2-GPU-per-worker mode: exactly 2× --num-workers IDs, consecutive pairs "
        "(Parameter_Policy / 32B–30B / --tensor-parallel-2). If omitted there, uses 0..2*num_workers-1.",
    )
    parser.add_argument("--tensor-parallel-2", action="store_true", dest="tensor_parallel_2")
    parser.add_argument("--api-parallel", type=int, default=16, help="Max parallel API calls for openai. Default: 16")

    parser.add_argument("--model-type", type=str, default="local", choices=["openai", "local", "mock"])
    parser.add_argument("--model-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--method", type=str, default="baseline",
                        choices=["baseline", "sys_feedback", "reflexion", "textgrad", "self_refine", "self_refine_inner_only",
                                  "a_mem_sys", "memento_nonparametric", "rememberer", "expel", "ace", "tree_of_thought",
                                  "reasoning_bank", "absolute_zero_iter", "science_codeevolve",
                                  "alpha_evolve", "theta_evolve", "genome", "seal", "ragen", "soar", "discover"])
    parser.add_argument("--n-select-sample", type=int, default=3, dest="n_select_sample")
    parser.add_argument("--n-generate-sample", type=int, default=2, dest="n_generate_sample")
    parser.add_argument("--reasoning-bank-k", type=int, default=2, dest="reasoning_bank_k")
    parser.add_argument("--ace-reflector-model", type=str, default="deepseek-v3.2", dest="ace_reflector_model")
    parser.add_argument("--ace-curator-model", type=str, default="deepseek-v3.2", dest="ace_curator_model")
    parser.add_argument("--reflect-model-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--textgrad-engine-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--a-mem-llm-model", type=str, default="deepseek-v3.2", dest="a_mem_sys_llm_model")
    parser.add_argument("--genome-iters", type=int, default=50, dest="genome_iters")
    parser.add_argument("--genome-population-size", type=int, default=10, dest="genome_population_size")
    parser.add_argument("--genome-best-lora-path", type=str, default=None, dest="genome_best_lora_path")
    parser.add_argument("--ragen-n-rollouts", type=int, default=8, dest="ragen_n_rollouts")
    parser.add_argument("--ragen-ppo-epochs", type=int, default=2, dest="ragen_ppo_epochs")
    parser.add_argument("--soar-generations", type=int, default=2, dest="soar_generations")
    parser.add_argument("--soar-k-candidates", type=int, default=4, dest="soar_k_candidates")
    parser.add_argument("--discover-num-epochs", type=int, default=50, dest="discover_num_epochs")
    parser.add_argument("--discover-group-size", type=int, default=8, dest="discover_group_size")
    parser.add_argument("--discover-groups-per-batch", type=int, default=64, dest="discover_groups_per_batch")
    parser.add_argument("--discover-learning-rate", type=float, default=4e-5, dest="discover_learning_rate")
    parser.add_argument("--discover-adv-estimator", type=str, default="entropic", dest="discover_adv_estimator")
    parser.add_argument("--discover-adv-estimator-beta", type=float, default=2.0, dest="discover_adv_estimator_beta")
    parser.add_argument("--discover-loss-fn", type=str, default="importance_sampling", dest="discover_loss_fn")
    parser.add_argument("--discover-lora-rank", type=int, default=32, dest="discover_lora_rank")
    parser.add_argument("--discover-max-tokens", type=int, default=65536, dest="discover_max_tokens")
    parser.add_argument("--discover-temperature", type=float, default=1.0, dest="discover_temperature")
    parser.add_argument("--discover-num-substeps", type=int, default=1, dest="discover_num_substeps")
    parser.add_argument("--discover-max-expansion-rounds", type=int, default=2, dest="discover_max_expansion_rounds")
    parser.add_argument("--theta-evolve-num-rollout", type=int, default=10000, dest="theta_evolve_num_rollout",
                        help="ThetaEvolve: number of rollout steps (official scripts use 10000 or 1000000). Default: 10000")
    parser.add_argument("--theta-evolve-rollout-batch-size", type=int, default=32, dest="theta_evolve_rollout_batch_size")
    parser.add_argument("--expel-max-rounds", type=int, default=8, dest="expel_max_rounds")
    parser.add_argument("--expel-max-num-rules", type=int, default=20, dest="expel_max_num_rules")

    parser.add_argument("--context", type=str, default="all",
                        choices=["previous", "all", "last_3", "best_score", "best_score_plus_previous"])
    args = parser.parse_args()

    task_list = resolve_task_list(args.task)
    if not task_list:
        print(f"❌ No tasks found for: {args.task}")
        return 1

    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    evaluate_script = os.path.join("evaluation", "evaluate_from_scratch.py")
    base_argv = _build_base_argv(args, scripts_dir, evaluate_script)

    work_items = collect_work_items_from_scratch(
        task_list, args.model_type, args.model_name, args.method, args.context
    )

    if not work_items:
        print("✅ No missing runs: all (task, env) already have JSON. Nothing to do.")
        return 0

    if args.model_type == "openai":
        print(f"📋 Work items (missing from-scratch runs): {len(work_items)}")
        print(f"🔀 API parallel: max_workers={min(len(work_items), args.api_parallel)}")
        for (t, s) in work_items[:20]:
            print(f"   — {t} {s}")
        if len(work_items) > 20:
            print(f"   ... and {len(work_items) - 20} more")
        print()
        results = run_api_parallel(work_items, args, scripts_dir)
        success = sum(1 for _, _, c in results if c == 0)
        total = len(results)
        print()
        print(f"{'='*60}")
        print(f"📊 API parallel summary: {success}/{total} runs succeeded")
        print(f"{'='*60}")
        return 0 if success == total else 1

    _m = getattr(args, "method", "") or ""
    base_method = _m[:-3] if str(_m).endswith("_CE") else str(_m)
    use_tp2 = parallel_local_use_tp2(args, base_method)

    if use_tp2:
        need = 2 * args.num_workers
        if args.gpus:
            parts = [x.strip() for x in args.gpus.split(",") if x.strip()]
            try:
                gpu_ids = [int(p) for p in parts]
            except ValueError:
                print("❌ TP2: --gpus must be comma-separated integers")
                return 1
            if len(gpu_ids) != need:
                print(
                    f"❌ 2-GPU-per-worker (Parameter_Policy / 32B–30B / --tensor-parallel-2): "
                    f"expected exactly {need} GPU id(s) (2 × --num-workers={args.num_workers}), "
                    f"got {len(gpu_ids)}. Example: --num-workers 1 --gpus 0,1"
                )
                return 1
        else:
            gpu_ids = list(range(need))
        num_workers = args.num_workers
        gpu_specs = [(gpu_ids[2 * i], gpu_ids[2 * i + 1]) for i in range(num_workers)]
        gpu_display = " ".join(f"{a},{b}" for (a, b) in gpu_specs)
    else:
        if args.gpus:
            gpu_ids = [int(x.strip()) for x in args.gpus.split(",")]
        else:
            gpu_ids = list(range(args.num_workers))
        num_workers = len(gpu_ids)
        if num_workers < 1:
            print("❌ Need at least one worker")
            return 1
        gpu_specs = list(gpu_ids)
        gpu_display = ",".join(str(g) for g in gpu_ids)

    work_chunks = [[] for _ in range(num_workers)]
    for i, item in enumerate(work_items):
        work_chunks[i % num_workers].append(item)

    print(f"📋 Work items (missing from-scratch runs): {len(work_items)}")
    tp2_label = " [2 GPUs per worker]" if use_tp2 else ""
    print(f"🔀 Workers: {num_workers} (GPUs: {gpu_display}){tp2_label}")
    for i, (gpu_spec, chunk) in enumerate(zip(gpu_specs, work_chunks)):
        label = f"{gpu_spec[0]},{gpu_spec[1]}" if isinstance(gpu_spec, tuple) else str(gpu_spec)
        preview = [f"{t}:{s}" for (t, s) in chunk[:5]]
        extra = f" ... +{len(chunk)-5}" if len(chunk) > 5 else ""
        print(f"   Worker {i} (GPU {label}): {len(chunk)} run(s) — {preview}{extra}")
    print()

    results = run_local_workers(gpu_specs, work_chunks, scripts_dir, base_argv)

    success = sum(1 for _, ok, _, _ in results if ok)
    total = len(results)
    for gpu_label, ok, code, lines in results:
        status = "✅" if ok else "❌"
        print(f"[GPU {gpu_label}] {status} (exit {code})")
    print()
    print(f"{'='*60}")
    print(f"📊 Data-parallel from-scratch summary: {success}/{total} workers succeeded")
    print(f"{'='*60}")
    return 0 if success == total else 1


if __name__ == "__main__":
    sys.exit(main())
