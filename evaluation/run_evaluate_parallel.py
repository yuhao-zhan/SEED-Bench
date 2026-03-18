#!/usr/bin/env python3
"""
Resilient Data-Parallel Evaluator.
Optimized for visibility during local model loading and stability under heavy simulation.
"""
import os
import re
import sys
import json
import subprocess
import argparse
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fcntl

def _safe_init_sdl():
    """Use a TRUE global file lock to ensure sequential initialization across subprocesses"""
    lock_file = "/tmp/seed_bench_sdl_init.lock"
    with open(lock_file, 'w') as f:
        try:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(f, fcntl.LOCK_EX)
            
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
            os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
            if "DISPLAY" in os.environ:
                del os.environ["DISPLAY"]
            
            # Short delay to let the OS/Driver settle
            time.sleep(0.5)
            
        finally:
            # Release lock
            fcntl.flock(f, fcntl.LOCK_UN)

# GLOBAL INITIALIZATION for stability
_safe_init_sdl()

def resolve_task_list(task_spec: str):
    from evaluation.evaluate import resolve_task_list as _resolve
    return _resolve(task_spec)

import concurrent.futures

def _verify_pair_safe(args):
    """Worker function for parallel pre-verification of cross-mutation pairs"""
    task_name, source, target, ref_source = args
    try:
        from evaluation.evaluate_cross_mutated import get_all_stages
        from evaluation.verifier import CodeVerifier
        from evaluation.utils import get_max_steps_for_task
        
        # Load env_j here to avoid pickling functions
        all_envs = get_all_stages(task_name)
        env_j = next(e for e in all_envs if e["stage_id"] == target)
        
        env_overrides = {
            "terrain_config": env_j.get("terrain_config", {}),
            "physics_config": env_j.get("physics_config", {}),
        }
        # Use task-specific max_steps for pre-verification
        max_steps = get_max_steps_for_task(task_name)
        verifier = CodeVerifier(task_name, max_steps=max_steps, env_overrides=env_overrides)
        success, _, _, _ = verifier.verify_code(ref_source, headless=True)
        verifier.cleanup()
        return (task_name, source, target, success)
    except:
        return (task_name, source, target, False)

def collect_work_items(task_list, model_type, model_name, method, context):
    from evaluation.evaluate_cross_mutated import get_all_stages, get_reference_solution
    from evaluation.utils import run_is_complete
    
    work_items = []
    candidates = []
    
    for task_name in task_list:
        if not task_name.startswith('category_'):
            if not run_is_complete(task_name, model_type, model_name, method, context):
                work_items.append((task_name, None, None))
            continue
        try:
            all_envs = get_all_stages(task_name)
            for i, env_i in enumerate(all_envs):
                source = env_i["stage_id"]
                try:
                    ref_source = get_reference_solution(task_name, source)
                except: continue
                for j, env_j in enumerate(all_envs):
                    if i == j: continue
                    target = env_j["stage_id"]
                    
                    pair_name = f"{source}_to_{target}"
                    if not run_is_complete(task_name, model_type, model_name, method, context, mutated_task_name=pair_name):
                        # Do not pass env_j directly to avoid PicklingError with functions
                        candidates.append((task_name, source, target, ref_source))
        except: pass

    if candidates:
        print(f"🧪 Pre-verifying {len(candidates)} cross-mutation pairs to filter out easy cases...")
        # Use a safe number of workers to avoid overwhelming the system
        num_workers = min(len(candidates), os.cpu_count() or 4)
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(tqdm(executor.map(_verify_pair_safe, candidates), total=len(candidates), desc="Pre-check"))
            for task_name, source, target, success in results:
                if not success:
                    work_items.append((task_name, source, target))
                else:
                    # We don't add to work_items, so it's effectively skipped
                    pass
                    
    return work_items


def collect_8B_success_pairs():
    """
    Scan evaluation_results for Qwen3-8B/baseline dirs; for each pair JSON with success=True,
    return a set of (task_path, source, target) so we can filter work_items by 8B baseline success.
    task_path is e.g. 'Category1_Statics_Equilibrium/S_01' (same as parse_task_name(task_name)[0]).
    """
    from evaluation.utils import get_evaluation_results_dir
    results_root = get_evaluation_results_dir()
    eight_b_baseline = "Qwen3-8B"
    method = "baseline"
    pattern = re.compile(r"^all_(.+)_to_(.+)\.json$")
    out = set()
    for root, dirs, files in os.walk(results_root, topdown=True):
        # Only process dirs that are exactly .../Qwen3-8B/baseline
        if os.path.basename(root) != method or os.path.basename(os.path.dirname(root)) != eight_b_baseline:
            continue
        # root is like .../evaluation_results/Category1_Statics_Equilibrium/S_01/Qwen3-8B/baseline
        rel = os.path.relpath(root, results_root)
        parts = rel.split(os.sep)
        if len(parts) >= 2:
            task_path = f"{parts[0]}/{parts[1]}"
        else:
            task_path = rel
        for fn in files:
            m = pattern.match(fn)
            if not m:
                continue
            source, target = m.group(1), m.group(2)
            p = os.path.join(root, fn)
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                if data.get("success") is True:
                    out.add((task_path, source, target))
            except Exception:
                pass
        dirs.clear()  # do not recurse under baseline
    return out


def _run_single_task_resilient(cmd, env, task_name, pair_label, worker_pbar, print_lock, max_retries=5):
    """Internal helper to run a task with auto-restart on Segfault and live log monitoring"""
    last_successful_iter = 0
    for attempt in range(max_retries):
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                text=True, bufsize=1, env=env)
        
        # Monitor initialization logs to show user it's alive
        init_lines_captured = 0
        for line in iter(proc.stdout.readline, ""):
            # Print first 20 lines of logs to show model loading status
            if init_lines_captured < 20:
                with print_lock:
                    # Clean the line and show which core it's from
                    clean_line = line.strip()
                    if clean_line and not "Iteration" in clean_line:
                        # Move cursor to end of screen area to avoid tqdm mess
                        sys.stdout.write(f"\033[K[{task_name[-8:]}] {clean_line}\n")
                        sys.stdout.flush()
                init_lines_captured += 1

            # Always echo iteration progress and save confirmation (so redirect to file still shows them)
            if "Iteration " in line and "/" in line:
                with print_lock:
                    sys.stdout.write(f"\033[K[{task_name[-8:]}] {line}")
                    sys.stdout.flush()
                try:
                    current_iter = int(line.split("Iteration ")[1].split("/")[0])
                    if current_iter > last_successful_iter:
                        worker_pbar.update(current_iter - last_successful_iter)
                        last_successful_iter = current_iter
                except: pass
            if "Evaluation report saved:" in line or "✅ Task" in line:
                with print_lock:
                    sys.stdout.write(f"\033[K[{task_name[-8:]}] {line}")
                    sys.stdout.flush()
            
            # Fatal API check
            if any(k in line for k in ["Insufficient quota", "Rate limit reached", "insufficient_quota", " 429 "]):
                proc.terminate()
                return 99 # Fatal
        
        proc.wait()
        if proc.returncode == -11 and last_successful_iter < worker_pbar.total:
            with print_lock:
                print(f"\n💥 Segfault in {task_name} {pair_label}. Restarting (Attempt {attempt+1}/{max_retries})...")
            time.sleep(random.uniform(2, 5))
            continue 
        return proc.returncode
    return 1

def run_local_workers(gpu_specs, work_chunks, scripts_dir, base_argv, max_iters):
    """Handles Local Model (GPU) parallelism"""
    print_lock = threading.Lock()
    print(f"🔥 Launching {len(gpu_specs)} GPU Workers (CPU-bound simulation will run in parallel)...")
    
    def worker_thread(gpu_spec, chunk, worker_idx):
        cuda_visible = str(gpu_spec)
        env = os.environ.copy()
        env.update({"CUDA_VISIBLE_DEVICES": cuda_visible, "SDL_VIDEODRIVER": "dummy", 
                    "SDL_AUDIODRIVER": "dummy", "PYTHONUNBUFFERED": "1"})
        if "DISPLAY" in env: del env["DISPLAY"]

        for item in chunk:
            task_name, src, tgt = item
            pair_label = f"{src or 'init'}->{tgt or 'init'}"
            pbar = tqdm(total=max_iters, desc=f"GPU-{gpu_spec} | {task_name[-12:]} | {pair_label}", 
                        position=worker_idx + 1, leave=False)
            
            # For local models, we use model_name as path
            cmd = base_argv + ["--task", task_name, "--device", "cuda:0", "--model-path", base_argv[5]]
            if src and tgt: cmd += ["--source-env", src, "--target-env", tgt]
            
            _run_single_task_resilient(cmd, env, task_name, pair_label, pbar, print_lock)
            pbar.close()

    threads = []
    for i, (spec, chunk) in enumerate(zip(gpu_specs, work_chunks)):
        if not chunk: continue
        t = threading.Thread(target=worker_thread, args=(spec, chunk, i))
        t.start()
        threads.append(t)
    for t in threads: t.join()

def run_api_parallel(work_items, args, scripts_dir):
    """Handles API-based (OpenAI/DeepSeek) parallelism"""
    evaluate_script = os.path.join(scripts_dir, "evaluation", "evaluate.py")
    base_cmd = [sys.executable, evaluate_script, "--model-type", args.model_type, "--model-name", args.model_name,
                "--max-iterations", str(args.max_iterations), "--method", args.method, "--context", args.context]
    if args.api_key: base_cmd += ["--api-key", args.api_key]
    if getattr(args, "method", None) == "reflexion" and getattr(args, "reflect_model_name", None):
        base_cmd += ["--reflect-model-name", args.reflect_model_name]
    
    max_workers = min(len(work_items), args.api_parallel)
    stop_event = threading.Event()
    results = []
    print_lock = threading.Lock()
    master_pbar = tqdm(total=len(work_items), desc="Overall Progress", position=0)

    def run_worker_thread(item, pos):
        if stop_event.is_set(): return
        task_name, src, tgt = item
        pair_label = f"{src or 'init'}->{tgt or 'init'}"
        pbar = tqdm(total=args.max_iterations, desc=f"C{pos:02d} | {task_name[-12:]} | {pair_label}", 
                    position=pos+1, leave=False)
        
        cmd = base_cmd + ["--task", task_name]
        if src and tgt: cmd += ["--source-env", src, "--target-env", tgt]
        
        env = os.environ.copy()
        env.update({"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "PYTHONUNBUFFERED": "1"})
        if "DISPLAY" in env: del env["DISPLAY"]

        code = _run_single_task_resilient(cmd, env, task_name, pair_label, pbar, print_lock)
        if code == 99: stop_event.set()
        pbar.close()
        master_pbar.update(1)
        results.append((task_name, src, tgt, code))

    active_pos = list(range(max_workers))
    def run_with_pos(item):
        pos = active_pos.pop(0)
        try: run_worker_thread(item, pos)
        finally: active_pos.append(pos); active_pos.sort()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for item in work_items: executor.submit(run_with_pos, item)
    master_pbar.close()
    if stop_event.is_set(): sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Resilient Data-Parallel Evaluator")
    parser.add_argument("--task", type=str, required=True)
    parser.add_argument("--model-type", type=str, default="openai", choices=["openai", "local", "mock"])
    parser.add_argument("--model-name", type=str, required=True)
    parser.add_argument("--num-workers", type=int, default=8, help="Number of GPU workers")
    parser.add_argument("--gpus", type=str, default=None, help="Comma-separated GPU IDs")
    parser.add_argument("--api-parallel", type=int, default=16, help="API Parallelism")
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--method", type=str, default="baseline")
    parser.add_argument("--context", type=str, default="all")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--save-gif", action="store_true", default=True)
    parser.add_argument(
        "--skip-8B-success",
        type=str,
        default="none",
        choices=["skip", "only", "none"],
        help="Filter by Qwen3-8B baseline success: skip=skip pairs that 8B already passed; only=only run those pairs; none=no filter (default)",
    )
    parser.add_argument("--genome-best-lora-path", type=str, default=None, dest="genome_best_lora_path",
                        help="GENOME: path to Phase 1 best LoRA. Passed to workers when --method genome.")
    parser.add_argument("--reflect-model-name", type=str, default="deepseek-v3.2", dest="reflect_model_name",
                        help="Reflexion: reflection LLM model name (API). Passed to workers when --method reflexion. Default: deepseek-v3.2.")

    args = parser.parse_args()
    if args.method.endswith('_CE'):
        print(f"📡 Change Exposed (CE) Mode detected for method: {args.method[:-3]}")
    task_list = resolve_task_list(args.task)
    work_items = collect_work_items(task_list, args.model_type, args.model_name, args.method, args.context)
    if not work_items: print("✅ All runs complete."); return 0

    # Optional filter by Qwen3-8B baseline success (skip / only / none)
    if args.skip_8B_success != "none":
        from evaluation.prompt import parse_task_name
        eight_b_success = collect_8B_success_pairs()
        n_before = len(work_items)
        filtered = []
        for item in work_items:
            task_name, src, tgt = item
            try:
                task_path, _ = parse_task_name(task_name)
            except Exception:
                task_path = task_name
            key = (task_path, src, tgt)
            in_8b = key in eight_b_success
            if args.skip_8B_success == "skip":
                if not in_8b:
                    filtered.append(item)
            else:  # "only"
                if in_8b:
                    filtered.append(item)
        work_items = filtered
        print(f"🔀 8B filter ({args.skip_8B_success}): {n_before} -> {len(work_items)} pairs (8B_success set size: {len(eight_b_success)})")
        if not work_items:
            print("✅ No work items after 8B filter.")
            return 0

    # REMEMBERER / EXPEL (pair-based): ensure memory data from evaluation_results_scratch for each pair's source env
    base_method = args.method[:-3] if args.method.endswith("_CE") else args.method
    if base_method in ("rememberer", "expel"):
        from evaluation.utils import get_model_identifier, get_evaluation_results_scratch_dir
        model_identifier = get_model_identifier(args.model_type, args.model_name)
        scratch_base = get_evaluation_results_scratch_dir()
        for item in work_items:
            task_name, src, tgt = item
            if src and tgt:
                if base_method == "rememberer":
                    from methods.Memory.rememberer_method import ensure_rememberer_data_from_scratch
                    ensure_rememberer_data_from_scratch(task_name, src, model_identifier, scratch_base)
                else:
                    from methods.Memory.expel_method import ensure_expel_data_from_scratch
                    from evaluation.solver_interface import get_aux_llm_credentials
                    import os as _os
                    _k, _u = get_aux_llm_credentials(getattr(args, "api_key", None))
                    ensure_expel_data_from_scratch(
                        task_name, src, model_identifier, scratch_base,
                        api_key=_k,
                        base_url=_u,
                        insight_model=_os.environ.get("EXPEL_INSIGHT_MODEL"),
                    )

    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.model_type == "local":
        all_gpus = [x.strip() for x in args.gpus.split(",")] if args.gpus else [str(i) for i in range(args.num_workers)]
        num_workers = args.num_workers
        
        # Group GPUs for each worker
        gpu_groups = []
        gpus_per_worker = max(1, len(all_gpus) // num_workers)
        for i in range(num_workers):
            start = i * gpus_per_worker
            # Last worker gets all remaining GPUs to ensure none are left out
            end = (i + 1) * gpus_per_worker if i < num_workers - 1 else len(all_gpus)
            if start < len(all_gpus):
                gpu_groups.append(",".join(all_gpus[start:end]))
        
        # Adjust num_workers if we have fewer groups than requested
        num_workers = len(gpu_groups)
        work_chunks = [work_items[i::num_workers] for i in range(num_workers)]
        # We pass model_name as both name and path for simplicity in local mode
        base_argv = [sys.executable, os.path.join(scripts_dir, "evaluation", "evaluate.py"), 
                     "--model-type", "local", "--model-name", args.model_name, 
                     "--max-iterations", str(args.max_iterations), "--method", args.method, "--context", args.context]
        if getattr(args, "method", None) == "genome" and getattr(args, "genome_best_lora_path", None):
            base_argv += ["--genome-best-lora-path", args.genome_best_lora_path]
        if getattr(args, "method", None) == "reflexion" and getattr(args, "reflect_model_name", None):
            base_argv += ["--reflect-model-name", args.reflect_model_name]
        run_local_workers(gpu_groups, work_chunks, scripts_dir, base_argv, args.max_iterations)
    else:
        run_api_parallel(work_items, args, scripts_dir)

if __name__ == "__main__":
    main()
