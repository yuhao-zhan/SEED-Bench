#!/usr/bin/env python3
"""
Data-parallel evaluation with run-level granularity:
- Collect (task, run_number) work items for runs that are NOT complete (missing JSON for 1st/2nd/3rd pass).
- Local/huggingface: split work items across N GPUs; each GPU runs one (task, run_number) at a time, then the next.
- For 32B (or 30B) local models: use 2 GPUs per worker (tensor parallel). --gpus lists IDs in pairs;
  num_workers = len(gpus)//2 (e.g. --gpus 5,7 => 1 worker on 5+7; --gpus 1,2,3,4 => 2 workers).
- OpenAI/anthropic: run all work items in parallel via ThreadPoolExecutor (no GPU).

Usage (from DaVinciBench/2D_exploration/scripts/):
  # Local model: 8 GPUs, only missing runs
  python evaluation/run_evaluate_parallel.py --task category_1 --num-workers 8 \\
    --model-type local --model-name /path/to/Qwen3-14B --max-iterations 20 --method baseline --context all

  # 32B local model: 2 workers, each using 2 GPUs (TP2)
  python evaluation/run_evaluate_parallel.py --task category_1 --num-workers 2 --gpus 1,2,3,4 \\
    --model-type local --model-name /path/to/Qwen3-32B --max-iterations 20 --method baseline --context all

  # API model: parallel API calls (no GPU)
  python evaluation/run_evaluate_parallel.py --task category_1 --api-parallel 16 \\
    --model-type openai --model-name deepseek-v3.2 --max-iterations 20 --method baseline --context all
"""
import os
import signal
import sys
import subprocess
import argparse
import threading

# Point to scripts directory so "evaluation.*" resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_task_list(task_spec: str):
    """Resolve task spec to list of task names (same logic as evaluate.py)."""
    from evaluation.evaluate import resolve_task_list as _resolve
    return _resolve(task_spec)


def model_needs_tp2(args) -> bool:
    """True if this run should use 2-GPU tensor parallel (e.g. 32B model on 2x80GB).
    Enabled by --tensor-parallel-2 or when model name/path suggests 32B/30B."""
    if getattr(args, "tensor_parallel_2", False):
        return True
    name = (args.model_name or "").lower()
    path = (getattr(args, "model_path", None) or "").lower()
    return "32b" in name or "30b" in name or "32b" in path or "30b" in path


def collect_work_items(task_list, model_type, model_name, method, context):
    """Collect (task_name, run_number) for runs that are not complete (same logic as evaluate.py / utils)."""
    from evaluation.utils import collect_incomplete_runs
    return collect_incomplete_runs(task_list, model_type, model_name, method, context)


def _gpu_spec_to_cuda_and_device(spec):
    """Convert gpu_spec (int or tuple of 2 ints) to (CUDA_VISIBLE_DEVICES, --device value, label)."""
    if isinstance(spec, tuple):
        a, b = spec
        return f"{a},{b}", "cuda:0,1", f"{a},{b}"
    return str(spec), "cuda:0", str(spec)


def run_local_workers(gpu_specs, work_chunks, scripts_dir, base_argv):
    """Run one subprocess per (task, run_number) in each chunk; each chunk is bound to one GPU or one GPU pair.
    gpu_specs: list of int (single GPU) or (int,int) (pair for tensor-parallel, e.g. 32B).
    Stream each worker's stdout in real time with [GPU i] or [GPU i,j] prefix."""
    results = []  # list of (gpu_label, chunk_success, failed_exit_code or 0, last_out_lines)
    print_lock = threading.Lock()

    def worker(gpu_spec, chunk):
        cuda_visible, device_str, gpu_label = _gpu_spec_to_cuda_and_device(gpu_spec)
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = cuda_visible
        env["PYTHONUNBUFFERED"] = "1"  # so subprocess stdout is line-buffered
        # Avoid loading corrupted torch.compile cache (checksum mismatch in vLLM/Inductor)
        env["VLLM_DISABLE_COMPILE_CACHE"] = "1"
        all_ok = True
        last_code = 0
        last_out_lines = []
        for (task_name, run_number) in chunk:
            cmd = base_argv + ["--device", device_str] + ["--task", task_name, "--run-number", str(run_number)]
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
                    start_new_session=True,  # own process group so we can kill vLLM workers on exit
                )
                # Stream stdout line by line with [GPU i] prefix; skip noisy model-loading tqdm
                for line in iter(proc.stdout.readline, ""):
                    if "Loading weights" in line or "Materializing param" in line:
                        continue
                    with print_lock:
                        print(f"[GPU {gpu_label}] {line}", end="", flush=True)
                proc.wait()
                last_code = proc.returncode
                if proc.stdout and last_code != 0:
                    last_out_lines = []  # already printed
                if last_code != 0:
                    all_ok = False
            except Exception as e:
                all_ok = False
                last_code = -1
                last_out_lines = [str(e)]
                with print_lock:
                    print(f"[GPU {gpu_label}] Exception: {e}", flush=True)
            finally:
                # Kill process group so orphaned vLLM workers (spawned by evaluate.py) are cleaned up
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

    return results  # list of (gpu_label, all_ok, last_code, last_out_lines)


def run_api_parallel(work_items, args, scripts_dir):
    """Run all (task, run_number) in parallel via ThreadPoolExecutor (like evaluate_mutated). No GPU."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from evaluation.evaluate import evaluate_single_task

    # Build an args-like object for evaluate_single_task (same attributes as evaluate.py parser)
    class EvalArgs:
        pass
    e = EvalArgs()
    e.model_type = args.model_type
    e.model_name = args.model_name
    e.model_path = getattr(args, 'model_path', None)
    e.api_key = getattr(args, 'api_key', None)
    e.max_iterations = args.max_iterations
    e.max_steps = args.max_steps
    e.method = args.method
    e.context = args.context
    e.device = "cpu"  # API models don't use GPU in this runner
    e.reflect_model_name = getattr(args, 'reflect_model_name', 'gpt-4o')  # Reflexion method
    e.textgrad_engine_name = getattr(args, 'textgrad_engine_name', 'deepseek-v3.2')  # TextGrad method
    e.a_mem_sys_llm_model = getattr(args, 'a_mem_sys_llm_model', 'deepseek-v3.2')  # A-mem-sys: memory LLM
    e.ace_reflector_model = getattr(args, 'ace_reflector_model', 'deepseek-v3.2')  # ACE: Reflector model
    e.ace_curator_model = getattr(args, 'ace_curator_model', 'deepseek-v3.2')  # ACE: Curator model
    e.n_select_sample = getattr(args, 'n_select_sample', 3)  # ToT: b
    e.n_generate_sample = getattr(args, 'n_generate_sample', 2)  # ToT: n
    e.reasoning_bank_k = getattr(args, 'reasoning_bank_k', 2)  # ReasoningBank: parallel K
    e.genome_iters = getattr(args, 'genome_iters', 50)
    e.genome_population_size = getattr(args, 'genome_population_size', 10)

    max_workers = min(len(work_items), getattr(args, 'api_parallel', 16))
    results = []  # list of (task_name, run_number, exit_code)

    def run_one(item):
        task_name, run_number = item
        return (task_name, run_number, evaluate_single_task(task_name, e, run_number_override=run_number))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(run_one, item): item for item in work_items}
        for future in as_completed(future_to_item):
            try:
                results.append(future.result())
            except Exception as exc:
                item = future_to_item[future]
                print(f"❌ {item[0]} run {item[1]} failed: {exc}")
                results.append((item[0], item[1], 1))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run evaluation in data-parallel mode: collect missing (task, run) work items, "
                    "then local=split across GPUs, API=parallel thread pool."
    )
    parser.add_argument("--task", type=str, required=True,
                        help="Task spec: category_X_YY, category_X, or all (same as evaluate.py)")
    parser.add_argument("--num-workers", type=int, default=8,
                        help="Number of GPU workers for local. Default: 8")
    parser.add_argument("--gpus", type=str, default=None,
                        help="Comma-separated GPU IDs for local workers (e.g. 0,1,2,3,4,5,6,7). Default: 0..num_workers-1. "
                             "For 32B/TP2: IDs in pairs, num_workers=len(gpus)//2 (e.g. 5,7 => 1 worker; 1,2,3,4 => 2 workers). "
                             "With science_codeevolve+vLLM (API_BASE set): inference runs on the vLLM server's GPU; --gpus only affects this process (e.g. verifier).")
    parser.add_argument("--tensor-parallel-2", action="store_true", dest="tensor_parallel_2",
                        help="Use 2 GPUs per worker (tensor parallel) for large models (e.g. 32B). Auto-enabled when model name/path contains 32b/30b.")
    parser.add_argument("--api-parallel", type=int, default=16,
                        help="Max parallel API calls for openai. Default: 16")
    # Forward evaluate.py args
    parser.add_argument("--model-type", type=str, default="local",
                        choices=["openai", "local", "mock"])
    parser.add_argument("--model-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--method", type=str, default="baseline", choices=["baseline", "sys_feedback", "reflexion", "textgrad", "self_refine", "self_refine_inner_only", "a_mem_sys", "memento_nonparametric", "rememberer", "expel", "ace", "tree_of_thought", "reasoning_bank", "absolute_zero", "absolute_zero_iter", "science_codeevolve", "alpha_evolve", "theta_evolve", "genome", "seal", "ragen", "soar", "discover"])
    parser.add_argument("--n-select-sample", type=int, default=3, dest="n_select_sample",
                        help="ToT: beams to keep per round (b). Default: 3")
    parser.add_argument("--n-generate-sample", type=int, default=2, dest="n_generate_sample",
                        help="ToT: samples per beam per round (n). Default: 2")
    parser.add_argument("--reasoning-bank-k", type=int, default=2, dest="reasoning_bank_k",
                        help="ReasoningBank: parallel trajectories per iteration (k). Default: 2")
    parser.add_argument("--ace-reflector-model", type=str, default="deepseek-v3.2", dest="ace_reflector_model",
                        help="Model for ACE Reflector (only when method=ace). Default: deepseek-v3.2")
    parser.add_argument("--ace-curator-model", type=str, default="deepseek-v3.2", dest="ace_curator_model",
                        help="Model for ACE Curator (only when method=ace). Default: deepseek-v3.2")
    parser.add_argument("--reflect-model-name", type=str, default="deepseek-v3.2",
                        help="Model name for reflection LLM (only used when method=reflexion). Default: deepseek-v3.2")
    parser.add_argument("--textgrad-engine-name", type=str, default="deepseek-v3.2",
                        help="Engine for TextGrad backward/optimizer (only used when method=textgrad). Default: deepseek-v3.2")
    parser.add_argument("--a-mem-llm-model", type=str, default="deepseek-v3.2", dest="a_mem_sys_llm_model",
                        help="LLM for memory module (only when method=a_mem_sys). Default: deepseek-v3.2")
    parser.add_argument("--genome-iters", type=int, default=50, dest="genome_iters",
                        help="GENOME Phase 1: GA iterations. Default: 50")
    parser.add_argument("--genome-population-size", type=int, default=10, dest="genome_population_size",
                        help="GENOME Phase 1: population size. Default: 10")
    parser.add_argument("--ragen-n-rollouts", type=int, default=8, dest="ragen_n_rollouts",
                        help="RAGEN: number of rollout episodes per task. Default: 8")
    parser.add_argument("--ragen-ppo-epochs", type=int, default=2, dest="ragen_ppo_epochs",
                        help="RAGEN: number of PPO epochs per training step. Default: 2")
    parser.add_argument("--soar-generations", type=int, default=2, dest="soar_generations",
                        help="SOAR: self-improvement generations. Default: 2")
    parser.add_argument("--soar-k-candidates", type=int, default=4, dest="soar_k_candidates",
                        help="SOAR: K candidates per iteration. Default: 4")
    parser.add_argument("--discover-num-epochs", type=int, default=50, dest="discover_num_epochs",
                        help="Discover: TTT epochs. Default: 50")
    parser.add_argument("--discover-group-size", type=int, default=8, dest="discover_group_size",
                        help="Discover: rollouts per group. Default: 8")
    parser.add_argument("--discover-groups-per-batch", type=int, default=64, dest="discover_groups_per_batch",
                        help="Discover: groups per batch. Default: 64")
    parser.add_argument("--discover-learning-rate", type=float, default=4e-5, dest="discover_learning_rate",
                        help="Discover: learning rate. Default: 4e-5")
    parser.add_argument("--discover-adv-estimator", type=str, default="entropic", dest="discover_adv_estimator",
                        help="Discover: advantage estimator. Default: entropic")
    parser.add_argument("--discover-adv-estimator-beta", type=float, default=2.0, dest="discover_adv_estimator_beta",
                        help="Discover: entropic beta. Default: 2.0")
    parser.add_argument("--discover-loss-fn", type=str, default="importance_sampling", dest="discover_loss_fn",
                        help="Discover: loss. Default: importance_sampling")
    parser.add_argument("--discover-lora-rank", type=int, default=32, dest="discover_lora_rank",
                        help="Discover: LoRA rank. Default: 32")
    parser.add_argument("--discover-max-tokens", type=int, default=65536, dest="discover_max_tokens",
                        help="Discover: max tokens. Default: 26000")
    parser.add_argument("--discover-temperature", type=float, default=1.0, dest="discover_temperature",
                        help="Discover: temperature. Default: 1.0")
    parser.add_argument("--discover-num-substeps", type=int, default=1, dest="discover_num_substeps",
                        help="Discover: num substeps. Default: 1")
    parser.add_argument("--discover-max-expansion-rounds", type=int, default=2, dest="discover_max_expansion_rounds",
                        help="Discover: max feedback expansion rounds. Default: 2")
    parser.add_argument("--theta-evolve-num-rollout", type=int, default=3000, dest="theta_evolve_num_rollout",
                        help="ThetaEvolve: number of rollout steps. Default: 3000")
    parser.add_argument("--theta-evolve-rollout-batch-size", type=int, default=32, dest="theta_evolve_rollout_batch_size",
                        help="ThetaEvolve: rollout batch size. Default: 32")
    parser.add_argument("--context", type=str, default="all",
                        choices=["previous", "all", "last_3", "best_score", "best_score_plus_previous"])
    parser.add_argument("--expel-max-rounds", type=int, default=8, dest="expel_max_rounds",
                        help="ExpeL: max insight extraction rounds when insights.json is missing (default 8)")
    parser.add_argument("--expel-max-num-rules", type=int, default=20, dest="expel_max_num_rules",
                        help="ExpeL: target max rules for list_full during extraction (default 20)")
    args = parser.parse_args()

    task_list = resolve_task_list(args.task)
    if not task_list:
        print(f"❌ No tasks found for: {args.task}")
        return 1

    # ExpeL/Rememberer: ensure is done inside evaluate.py per task (ensure_expel_data/ensure_rememberer_data
    # for the task's category), so no need to do it here; each evaluate.py run will ensure its category.

    work_items = collect_work_items(
        task_list,
        args.model_type,
        args.model_name,
        args.method,
        args.context,
    )

    if not work_items:
        print("✅ No missing runs: all (task, 1st/2nd/3rd pass) already have JSON. Nothing to do.")
        return 0

    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    evaluate_script = os.path.join("evaluation", "evaluate.py")

    # Build base argv for evaluate.py (no --task / --run-number yet)
    base_argv = [
        sys.executable,
        evaluate_script,
        "--model-type", args.model_type,
        "--model-name", args.model_name,
        "--max-iterations", str(args.max_iterations),
        "--max-steps", str(args.max_steps),
        "--method", args.method,
        "--context", args.context,
    ]
    if args.model_path:
        base_argv += ["--model-path", args.model_path]
    if args.api_key:
        base_argv += ["--api-key", args.api_key]
    if args.method == 'expel':
        if getattr(args, 'expel_max_rounds', None) is not None:
            base_argv += ["--expel-max-rounds", str(args.expel_max_rounds)]
        if getattr(args, 'expel_max_num_rules', None) is not None:
            base_argv += ["--expel-max-num-rules", str(args.expel_max_num_rules)]
    if args.method == 'reflexion':
        base_argv += ["--reflect-model-name", args.reflect_model_name]
    if args.method == 'textgrad':
        base_argv += ["--textgrad-engine-name", args.textgrad_engine_name]
    if args.method == 'a_mem_sys':
        base_argv += ["--a-mem-llm-model", getattr(args, 'a_mem_sys_llm_model', 'deepseek-v3.2')]
    if args.method == 'ace':
        base_argv += ["--ace-reflector-model", getattr(args, 'ace_reflector_model', 'deepseek-v3.2')]
        base_argv += ["--ace-curator-model", getattr(args, 'ace_curator_model', 'deepseek-v3.2')]
    if args.method == 'tree_of_thought':
        base_argv += ["--n-select-sample", str(getattr(args, 'n_select_sample', 3))]
        base_argv += ["--n-generate-sample", str(getattr(args, 'n_generate_sample', 2))]
    if args.method == 'reasoning_bank':
        base_argv += ["--reasoning-bank-k", str(getattr(args, 'reasoning_bank_k', 2))]
    if args.method == 'genome':
        base_argv += ["--genome-iters", str(getattr(args, 'genome_iters', 50))]
        base_argv += ["--genome-population-size", str(getattr(args, 'genome_population_size', 10))]
    if args.method == 'ragen':
        base_argv += ["--ragen-n-rollouts", str(getattr(args, 'ragen_n_rollouts', 8))]
        base_argv += ["--ragen-ppo-epochs", str(getattr(args, 'ragen_ppo_epochs', 2))]
    if args.method == 'soar':
        base_argv += ["--soar-generations", str(getattr(args, 'soar_generations', 2))]
        base_argv += ["--soar-k-candidates", str(getattr(args, 'soar_k_candidates', 4))]
    if args.method == 'theta_evolve':
        base_argv += ["--theta-evolve-num-rollout", str(getattr(args, 'theta_evolve_num_rollout', 3000))]
        base_argv += ["--theta-evolve-rollout-batch-size", str(getattr(args, 'theta_evolve_rollout_batch_size', 32))]
    if args.method == 'discover':
        base_argv += ["--discover-num-epochs", str(getattr(args, 'discover_num_epochs', 50))]
        base_argv += ["--discover-group-size", str(getattr(args, 'discover_group_size', 8))]
        base_argv += ["--discover-groups-per-batch", str(getattr(args, 'discover_groups_per_batch', 64))]
        base_argv += ["--discover-learning-rate", str(getattr(args, 'discover_learning_rate', 4e-5))]
        base_argv += ["--discover-adv-estimator", getattr(args, 'discover_adv_estimator', 'entropic')]
        base_argv += ["--discover-adv-estimator-beta", str(getattr(args, 'discover_adv_estimator_beta', 2.0))]
        base_argv += ["--discover-loss-fn", getattr(args, 'discover_loss_fn', 'importance_sampling')]
        base_argv += ["--discover-lora-rank", str(getattr(args, 'discover_lora_rank', 32))]
        base_argv += ["--discover-max-tokens", str(getattr(args, 'discover_max_tokens', 65536))]
        base_argv += ["--discover-temperature", str(getattr(args, 'discover_temperature', 1.0))]
        base_argv += ["--discover-num-substeps", str(getattr(args, 'discover_num_substeps', 1))]
        base_argv += ["--discover-max-expansion-rounds", str(getattr(args, 'discover_max_expansion_rounds', 2))]
    # memento_nonparametric uses Memento np_memory (Sup-SimCSE); no extra CLI args needed

    if args.model_type == "openai":
        # API: no GPU, run work items in parallel with thread pool
        print(f"📋 Work items (missing runs): {len(work_items)}")
        print(f"🔀 API parallel: max_workers={min(len(work_items), args.api_parallel)}")
        for (t, r) in work_items[:20]:
            print(f"   — {t} run {r}")
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

    # Local/huggingface: split work items across GPUs (round-robin for even load)
    # For 32B/TP2: two GPUs per worker (tensor parallel). With --gpus: num_workers = len(gpus)//2 (pairs).
    # theta_evolve: same (2 GPUs per task to fit 8B model + optimizer in 2x80G).
    # Without --gpus: gpu_ids = 0..2*num_workers-1 for TP2/theta_evolve, else 0..num_workers-1.
    use_tp2 = model_needs_tp2(args) or (getattr(args, "method", None) == "theta_evolve")
    if args.gpus:
        gpu_ids = [int(x.strip()) for x in args.gpus.split(",")]
    else:
        if use_tp2:
            gpu_ids = list(range(2 * args.num_workers))
        else:
            gpu_ids = list(range(args.num_workers))

    if use_tp2:
        if len(gpu_ids) % 2 != 0:
            print("❌ For 32B/TP2/theta_evolve (2 GPUs per worker) --gpus must have an even number of IDs (e.g. 5,7)")
            return 1
        num_workers = len(gpu_ids) // 2  # one worker per pair
        gpu_specs = [(gpu_ids[2 * i], gpu_ids[2 * i + 1]) for i in range(num_workers)]
        gpu_display = " ".join(f"{a},{b}" for (a, b) in gpu_specs)
    else:
        num_workers = len(gpu_ids)
        if num_workers < 1:
            print("❌ Need at least one worker (--num-workers or --gpus)")
            return 1
        gpu_specs = list(gpu_ids)
        gpu_display = ",".join(str(g) for g in gpu_ids)

    # Round-robin assign work items to workers
    work_chunks = [[] for _ in range(num_workers)]
    for i, item in enumerate(work_items):
        work_chunks[i % num_workers].append(item)

    # --device is set per worker in run_local_workers (cuda:0 or cuda:0,1 for TP2)

    print(f"📋 Work items (missing runs): {len(work_items)}")
    tp2_label = " [2 GPUs per worker: TP2 or theta_evolve]" if use_tp2 else ""
    print(f"🔀 Workers: {num_workers} (GPUs: {gpu_display}){tp2_label}")
    for i, (gpu_spec, chunk) in enumerate(zip(gpu_specs, work_chunks)):
        label = f"{gpu_spec[0]},{gpu_spec[1]}" if isinstance(gpu_spec, tuple) else str(gpu_spec)
        preview = [f"{t}:{r}" for (t, r) in chunk[:5]]
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
    print(f"📊 Data-parallel summary: {success}/{total} workers succeeded")
    print(f"{'='*60}")
    return 0 if success == total else 1


if __name__ == "__main__":
    sys.exit(main())
