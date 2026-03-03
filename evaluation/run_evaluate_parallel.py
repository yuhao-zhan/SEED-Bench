#!/usr/bin/env python3
"""
Data-parallel evaluation with pair-level granularity.
Each (T_ij, T_ik) pair is run ONLY ONCE.
"""
import os
import signal
import sys
import subprocess
import argparse
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_task_list(task_spec: str):
    from evaluation.evaluate import resolve_task_list as _resolve
    return _resolve(task_spec)


def collect_work_items(task_list, model_type, model_name, method, context):
    """
    Collect individual cross-mutation pairs (T_ij, T_ik) as work items.
    Each item: (task_name, source_env, target_env)
    """
    from evaluation.evaluate_cross_mutated import get_all_stages, get_model_identifier
    from evaluation.utils import get_evaluation_results_dir, run_is_complete
    
    work_items = []
    
    for task_name in task_list:
        if not task_name.startswith('category_'):
            # Non-category tasks: (task_name, None, None)
            if not run_is_complete(task_name, model_type, model_name, method, context):
                work_items.append((task_name, None, None))
            continue
            
        try:
            all_envs = get_all_stages(task_name)
            from evaluation.evaluate_cross_mutated import get_reference_solution
            for i, env_i in enumerate(all_envs):
                source = env_i["stage_id"]
                try:
                    # Check if reference solution exists for source env
                    get_reference_solution(task_name, source)
                except Exception as e:
                    print(f"⏭️  Skipping all pairs with source {source} in {task_name}: {e}")
                    continue

                for j, env_j in enumerate(all_envs):
                    if i == j: continue
                    
                    target = env_j["stage_id"]
                    pair_name = f"{source}_to_{target}"
                    
                    if not run_is_complete(task_name, model_type, model_name, method, context, mutated_task_name=pair_name):
                        work_items.append((task_name, source, target))
        except Exception as e:
            print(f"⚠️  Failed to collect pairs for {task_name}: {e}")
            
    return work_items


def _gpu_spec_to_cuda_and_device(spec):
    if isinstance(spec, tuple):
        a, b = spec
        return f"{a},{b}", "cuda:0,1", f"{a},{b}"
    return str(spec), "cuda:0", str(spec)


def run_local_workers(gpu_specs, work_chunks, scripts_dir, base_argv):
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
        
        for (task_name, source, target) in chunk:
            cmd = base_argv + ["--device", device_str] + ["--task", task_name]
            if source and target:
                cmd += ["--source-env", source, "--target-env", target]
                
            pair_label = f" [{source}->{target}]" if source else ""
            
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
                        print(f"[GPU {gpu_label}]{pair_label} {line}", end="", flush=True)
                proc.wait()
                last_code = proc.returncode
                if last_code != 0:
                    all_ok = False
            except Exception as e:
                all_ok = False
                last_code = -1
                with print_lock:
                    print(f"[GPU {gpu_label}]{pair_label} Exception: {e}", flush=True)
            finally:
                if proc is not None and proc.pid is not None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
        results.append((gpu_label, all_ok, last_code))

    threads = []
    for gpu_spec, chunk in zip(gpu_specs, work_chunks):
        if not chunk: continue
        t = threading.Thread(target=worker, args=(gpu_spec, chunk))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    return results


def run_api_parallel(work_items, args, scripts_dir):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from evaluation.evaluate import evaluate_single_task

    class EvalArgs: pass
    e = EvalArgs()
    for attr in ["model_type", "model_name", "model_path", "api_key", "max_iterations", "max_steps", "method", "context"]:
        setattr(e, attr, getattr(args, attr, None))
    
    # Defaults for EvalArgs
    e.device = "cpu"
    e.reflect_model_name = getattr(args, 'reflect_model_name', 'deepseek-v3.2')
    e.textgrad_engine_name = getattr(args, 'textgrad_engine_name', 'deepseek-v3.2')
    e.a_mem_sys_llm_model = getattr(args, 'a_mem_sys_llm_model', 'deepseek-v3.2')
    e.ace_reflector_model = getattr(args, 'ace_reflector_model', 'deepseek-v3.2')
    e.ace_curator_model = getattr(args, 'ace_curator_model', 'deepseek-v3.2')
    e.n_select_sample = getattr(args, 'n_select_sample', 3)
    e.n_generate_sample = getattr(args, 'n_generate_sample', 2)
    e.reasoning_bank_k = getattr(args, 'reasoning_bank_k', 2)
    e.genome_iters = getattr(args, 'genome_iters', 50)
    e.genome_population_size = getattr(args, 'genome_population_size', 10)
    e.ragen_n_rollouts = getattr(args, 'ragen_n_rollouts', 8)
    e.ragen_ppo_epochs = getattr(args, 'ragen_ppo_epochs', 2)
    e.soar_generations = getattr(args, 'soar_generations', 2)
    e.soar_k_candidates = getattr(args, 'soar_k_candidates', 4)
    e.discover_num_epochs = getattr(args, 'discover_num_epochs', 50)
    e.discover_group_size = getattr(args, 'discover_group_size', 8)
    e.discover_groups_per_batch = getattr(args, 'discover_groups_per_batch', 64)
    e.discover_learning_rate = getattr(args, 'discover_learning_rate', 4e-5)
    e.discover_adv_estimator = getattr(args, 'discover_adv_estimator', 'entropic')
    e.discover_adv_estimator_beta = getattr(args, 'discover_adv_estimator_beta', 2.0)
    e.discover_loss_fn = getattr(args, 'discover_loss_fn', 'importance_sampling')
    e.discover_lora_rank = getattr(args, 'discover_lora_rank', 32)
    e.discover_max_tokens = getattr(args, 'discover_max_tokens', 65536)
    e.discover_temperature = getattr(args, 'discover_temperature', 1.0)
    e.discover_num_substeps = getattr(args, 'discover_num_substeps', 1)
    e.discover_max_expansion_rounds = getattr(args, 'discover_max_expansion_rounds', 2)
    e.theta_evolve_num_rollout = getattr(args, 'theta_evolve_num_rollout', 3000)
    e.theta_evolve_rollout_batch_size = getattr(args, 'theta_evolve_rollout_batch_size', 32)
    e.expel_max_rounds = getattr(args, 'expel_max_rounds', 8)
    e.expel_max_num_rules = getattr(args, 'expel_max_num_rules', 20)

    max_workers = min(len(work_items), getattr(args, 'api_parallel', 16))
    results = []

    def run_one(item):
        task_name, source, target = item
        thread_e = EvalArgs()
        for k, v in e.__dict__.items(): setattr(thread_e, k, v)
        thread_e.source_env = source
        thread_e.target_env = target
        return (task_name, source, target, evaluate_single_task(task_name, thread_e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(run_one, item): item for item in work_items}
        for future in as_completed(future_to_item):
            try:
                results.append(future.result())
            except Exception as exc:
                item = future_to_item[future]
                print(f"❌ {item[0]} [{item[1]}->{item[2]}] failed: {exc}")
                results.append((item[0], item[1], item[2], 1))

    return results


def main():
    parser = argparse.ArgumentParser(description="Run evaluation in data-parallel mode.")
    parser.add_argument("--task", type=str, required=True)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--gpus", type=str, default=None)
    parser.add_argument("--tensor-parallel-2", action="store_true")
    parser.add_argument("--api-parallel", type=int, default=16)
    parser.add_argument("--model-type", type=str, default="local", choices=["openai", "local", "mock"])
    parser.add_argument("--model-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--method", type=str, default="baseline")
    parser.add_argument("--context", type=str, default="all")
    # Method-specific args
    parser.add_argument("--n-select-sample", type=int, default=3)
    parser.add_argument("--n-generate-sample", type=int, default=2)
    parser.add_argument("--reasoning-bank-k", type=int, default=2)
    parser.add_argument("--ace-reflector-model", type=str, default="deepseek-v3.2")
    parser.add_argument("--ace-curator-model", type=str, default="deepseek-v3.2")
    parser.add_argument("--reflect-model-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--textgrad-engine-name", type=str, default="deepseek-v3.2")
    parser.add_argument("--a-mem-llm-model", type=str, default="deepseek-v3.2", dest="a_mem_sys_llm_model")
    parser.add_argument("--genome-iters", type=int, default=50)
    parser.add_argument("--genome-population-size", type=int, default=10)
    parser.add_argument("--ragen-n-rollouts", type=int, default=8)
    parser.add_argument("--ragen-ppo-epochs", type=int, default=2)
    parser.add_argument("--soar-generations", type=int, default=2)
    parser.add_argument("--soar-k-candidates", type=int, default=4)
    parser.add_argument("--discover-num-epochs", type=int, default=50)
    parser.add_argument("--discover-group-size", type=int, default=8)
    parser.add_argument("--discover-groups-per-batch", type=int, default=64)
    parser.add_argument("--discover-learning-rate", type=float, default=4e-5)
    parser.add_argument("--discover-adv-estimator", type=str, default="entropic")
    parser.add_argument("--discover-adv-estimator-beta", type=float, default=2.0)
    parser.add_argument("--discover-loss-fn", type=str, default="importance_sampling")
    parser.add_argument("--discover-lora-rank", type=int, default=32)
    parser.add_argument("--discover-max-tokens", type=int, default=65536)
    parser.add_argument("--discover-temperature", type=float, default=1.0)
    parser.add_argument("--discover-num-substeps", type=int, default=1)
    parser.add_argument("--discover-max-expansion-rounds", type=int, default=2)
    parser.add_argument("--theta-evolve-num-rollout", type=int, default=3000)
    parser.add_argument("--theta-evolve-rollout-batch-size", type=int, default=32)
    parser.add_argument("--expel-max-rounds", type=int, default=8)
    parser.add_argument("--expel-max-num-rules", type=int, default=20)
    
    args = parser.parse_args()

    task_list = resolve_task_list(args.task)
    if not task_list:
        print(f"❌ No tasks found for: {args.task}")
        return 1

    work_items = collect_work_items(
        task_list, args.model_type, args.model_name, args.method, args.context
    )

    if not work_items:
        print("✅ All runs complete. Nothing to do.")
        return 0

    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    evaluate_script = os.path.join("evaluation", "evaluate.py")

    base_argv = [
        sys.executable, evaluate_script,
        "--model-type", args.model_type,
        "--model-name", args.model_name,
        "--max-iterations", str(args.max_iterations),
        "--max-steps", str(args.max_steps),
        "--method", args.method,
        "--context", args.context,
    ]
    if args.model_path: base_argv += ["--model-path", args.model_path]
    if args.api_key: base_argv += ["--api-key", args.api_key]

    if args.model_type == "openai":
        print(f"📋 Work items (missing pairs): {len(work_items)}")
        results = run_api_parallel(work_items, args, scripts_dir)
        success = sum(1 for r in results if r[-1] == 0)
        total = len(results)
        print(f"📊 API summary: {success}/{total} succeeded")
        return 0 if success == total else 1

    # Local
    gpu_ids = [int(x.strip()) for x in args.gpus.split(",")] if args.gpus else list(range(args.num_workers))
    num_workers = len(gpu_ids)
    gpu_specs = list(gpu_ids)
    work_chunks = [[] for _ in range(num_workers)]
    for i, item in enumerate(work_items):
        work_chunks[i % num_workers].append(item)

    print(f"📋 Work items (missing pairs): {len(work_items)}")
    for i, (spec, chunk) in enumerate(zip(gpu_specs, work_chunks)):
        preview = [f"{t}:{s}->{tg}" if s else t for (t, s, tg) in chunk[:3]]
        print(f"   Worker {i} (GPU {spec}): {len(chunk)} item(s) — {preview}...")

    results = run_local_workers(gpu_specs, work_chunks, scripts_dir, base_argv)
    success = sum(1 for _, ok, _ in results if ok)
    print(f"📊 Summary: {success}/{len(results)} workers succeeded")
    return 0 if success == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
