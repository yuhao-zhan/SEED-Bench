#!/usr/bin/env python3
"""
Discover evaluation result JSONs where the base task succeeded but mutation_sequence
is missing or incomplete (fewer than total_mutations results), then run
run_mutation_for_log for each to fill in the missing mutations.

For local/huggingface models:
- 32B/30B: 2-GPU tensor parallel (TP2), same as initial task. --device cuda:1,2 => GPUs 1,2 together.
- Other models: data-parallel (split logs across GPUs). --device cuda:4,5,6,7 => 4 workers.

Usage:
  # Scan default evaluation_results (under scripts/), exclude 'basic', run all incomplete
  python run_all_missing_mutations.py

  # 32B: 2 GPUs together (TP2)
  python run_all_missing_mutations.py --local-model-path /path/to/models --device cuda:1,2

  # Data-parallel (split logs across GPUs 4,5,6,7)
  python run_all_missing_mutations.py --local-model-path /path/to/models --device cuda:4,5,6,7

  # Custom root and dry-run
  python run_all_missing_mutations.py --results-dir /path/to/evaluation_results --dry-run
"""
import os
import sys
import json
import argparse
import subprocess
import threading

# Point to scripts directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.run_mutation_from_log import run_mutation_for_log

# Default base path for local/huggingface models (e.g. /home/test/testdata/models/Qwen3-14B)
DEFAULT_LOCAL_MODEL_BASE_PATH = "/home/test/testdata/models"


def parse_model_from_path(results_root: str, log_path: str) -> tuple[str | None, str | None, str | None]:
    """
    Infer model_type, model_name, method from path under results_root.
    Path is like: results_root/category_1_02/openai_deepseek-v3.2/baseline/all_1st_pass_20260209.json
    or results_root/category_1_02/Qwen3-8B/baseline/all_1st_pass_20260209.json

    Returns:
        (model_type, model_name, method) or (None, None, None) if path structure doesn't match.
    """
    results_root = os.path.normpath(results_root)
    log_path = os.path.normpath(log_path)
    if not log_path.startswith(results_root):
        return None, None, None
    rel = log_path[len(results_root) :].lstrip(os.sep)
    parts = rel.split(os.sep)
    # expect: category_xx, model_folder, method, filename.json
    if len(parts) < 3:
        return None, None, None
    model_folder = parts[1]
    method = parts[2]
    if model_folder.startswith("openai_"):
        model_type = "openai"
        model_name = model_folder[7:]
    elif model_folder.startswith("anthropic_"):
        # Legacy: anthropic_xxx treated as openai (Claude via OpenAI-compatible API)
        model_type = "openai"
        model_name = model_folder[10:]
    else:
        # local model, e.g. Qwen3-8B, gpt-oss-20b
        model_type = "local"
        model_name = model_folder
    return model_type, model_name, method


def is_incomplete_mutations(log_path: str) -> bool:
    """
    Return True if this log has base task success but mutation results are missing or incomplete.
    """
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    if not data.get("success"):
        return False
    ms = data.get("mutation_sequence")
    if ms is None:
        # No mutation_sequence at all -> need to run all
        return True
    total = ms.get("total_mutations", 4)
    results = ms.get("sequence_results", [])
    return len(results) < total


# Only consider JSON files whose filename starts with one of these (e.g. all_raw_*, all_1st_pass_*, etc.)
ALLOWED_FILENAME_PREFIXES = ("all_", "previous_")


def parse_gpu_ids_from_device(device: str) -> list[int] | None:
    """
    Parse device string to extract GPU IDs for multi-GPU parallel execution.
    E.g. "cuda:4,5,6,7" -> [4, 5, 6, 7], "cuda:0" -> [0].
    Returns None if device does not specify multiple GPUs (use sequential).
    """
    if not device or device in ("auto", "cpu"):
        return None
    if device == "cuda":
        return [0]  # Single default GPU
    if device.startswith("cuda:"):
        rest = device[5:].strip()  # after "cuda:"
        if "," in rest:
            try:
                return [int(x.strip()) for x in rest.split(",") if x.strip()]
            except ValueError:
                return None
        try:
            return [int(rest)]
        except ValueError:
            return None
    return None


def model_needs_tp2(model_name: str) -> bool:
    """True if model is 32B/30B and should use 2-GPU tensor parallel (same as run_evaluate_parallel)."""
    if not model_name:
        return False
    return "32b" in model_name.lower() or "30b" in model_name.lower()


def build_mutation_argv(
    log_path: str,
    model_type: str,
    model_name: str,
    method: str,
    model_path: str | None,
    output_dir: str,
    args,
    device_override: str | None = None,
) -> list[str]:
    """Build argv for run_mutation_from_log.py (subprocess).
    When CUDA_VISIBLE_DEVICES is set, use device_override if given (e.g. cuda:0,1 for TP2), else cuda:0."""
    device = device_override if device_override is not None else "cuda:0"
    argv = [
        sys.executable,
        os.path.join("evaluation", "run_mutation_from_log.py"),
        "--log", log_path,
        "--model-type", model_type,
        "--model-name", model_name,
        "--method", method,
        "--device", device,
        "--output-dir", output_dir,
    ]
    if model_path:
        argv += ["--model-path", model_path]
    if getattr(args, "reflect_model_name", None):
        argv += ["--reflect-model-name", args.reflect_model_name]
    if getattr(args, "textgrad_engine_name", None):
        argv += ["--textgrad-engine-name", args.textgrad_engine_name]
    if getattr(args, "a_mem_sys_llm_model", None):
        argv += ["--a-mem-llm-model", args.a_mem_sys_llm_model]
    if getattr(args, "ace_reflector_model", None):
        argv += ["--ace-reflector-model", args.ace_reflector_model]
    if getattr(args, "ace_curator_model", None):
        argv += ["--ace-curator-model", args.ace_curator_model]
    return argv


def run_local_workers_parallel(
    work_chunks: list[tuple[int, list[tuple[str, str, str, str, str | None]]]],
    scripts_dir: str,
    results_root: str,
    output_dir: str,
    args,
) -> list[tuple[int, bool, int]]:
    """
    Run mutation sequences in parallel: one subprocess per log per GPU.
    work_chunks: list of (gpu_id, [(log_path, model_type, model_name, method, model_path), ...])
    Returns: list of (gpu_id, all_ok, last_exit_code)
    """
    results: list[tuple[int, bool, int]] = []
    print_lock = threading.Lock()

    def build_argv(
        log_path: str, model_type: str, model_name: str, method: str, model_path: str | None
    ) -> list[str]:
        return build_mutation_argv(log_path, model_type, model_name, method, model_path, output_dir, args)

    def worker(gpu_id: int, chunk: list[tuple[str, str, str, str, str | None]]) -> None:
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        env["PYTHONUNBUFFERED"] = "1"
        all_ok = True
        last_code = 0
        for log_path, model_type, model_name, method, model_path in chunk:
            cmd = build_argv(log_path, model_type, model_name, method, model_path)
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=scripts_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                for line in iter(proc.stdout.readline, ""):
                    if "Loading weights" in line or "Materializing param" in line:
                        continue
                    with print_lock:
                        print(f"[GPU {gpu_id}] {line}", end="", flush=True)
                proc.wait()
                last_code = proc.returncode
                if last_code != 0:
                    all_ok = False
            except Exception as e:
                all_ok = False
                last_code = -1
                with print_lock:
                    print(f"[GPU {gpu_id}] Exception: {e}", flush=True)
        results.append((gpu_id, all_ok, last_code))

    threads = []
    for gpu_id, chunk in work_chunks:
        if not chunk:
            continue
        t = threading.Thread(target=worker, args=(gpu_id, chunk))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    return results


def run_tp2_workers_parallel(
    work_chunks: list[tuple[tuple[int, int], list[tuple[str, str, str, str, str | None]]]],
    scripts_dir: str,
    results_root: str,
    output_dir: str,
    args,
) -> list[tuple[str, bool, int]]:
    """
    Run mutation sequences with 2-GPU tensor parallel per worker (for 32B/30B).
    work_chunks: list of ((gpu_a, gpu_b), [(log_path, model_type, model_name, method, model_path), ...])
    Each subprocess gets CUDA_VISIBLE_DEVICES='a,b' and --device cuda:0,1 so vLLM loads model across 2 GPUs.
    Returns: list of (gpu_label, all_ok, last_exit_code).
    """
    results: list[tuple[str, bool, int]] = []
    print_lock = threading.Lock()
    tp2_device = "cuda:0,1"

    def build_argv(
        log_path: str, model_type: str, model_name: str, method: str, model_path: str | None
    ) -> list[str]:
        return build_mutation_argv(
            log_path, model_type, model_name, method, model_path, output_dir, args,
            device_override=tp2_device,
        )

    def worker(gpu_pair: tuple[int, int], chunk: list[tuple[str, str, str, str, str | None]]) -> None:
        gpu_a, gpu_b = gpu_pair
        gpu_label = f"{gpu_a},{gpu_b}"
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = f"{gpu_a},{gpu_b}"
        env["PYTHONUNBUFFERED"] = "1"
        all_ok = True
        last_code = 0
        for log_path, model_type, model_name, method, model_path in chunk:
            cmd = build_argv(log_path, model_type, model_name, method, model_path)
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=scripts_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
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
                with print_lock:
                    print(f"[GPU {gpu_label}] Exception: {e}", flush=True)
        results.append((gpu_label, all_ok, last_code))

    threads = []
    for gpu_pair, chunk in work_chunks:
        if not chunk:
            continue
        t = threading.Thread(target=worker, args=(gpu_pair, chunk))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    return results


def collect_incomplete_logs(results_root: str, exclude_dirs: set[str] | None = None) -> list[str]:
    """Find all JSON files under results_root (excluding exclude_dirs) that need mutation run.
    Only includes files whose basename starts with all_1st, all_2nd, or all_3rd."""
    if exclude_dirs is None:
        exclude_dirs = {"basic"}
    results_root = os.path.abspath(results_root)
    out = []
    for root, dirs, _ in os.walk(results_root, topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in os.listdir(root):
            if not name.endswith(".json"):
                continue
            if not name.startswith(ALLOWED_FILENAME_PREFIXES):
                continue
            path = os.path.join(root, name)
            if not os.path.isfile(path):
                continue
            if is_incomplete_mutations(path):
                out.append(path)
    return sorted(out)


def main():
    parser = argparse.ArgumentParser(
        description="Find result JSONs with successful base task but incomplete mutation_sequence, then run mutations for each."
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="/home/test/test1709/THUNLP/DaVinciBench/2D_exploration/scripts/evaluation_results",
        help="Root directory of evaluation_results (default: scripts/evaluation_results)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        default=["basic", "category_1_03_org", "category_1_05_org"],
        help="Subfolder names to exclude from scan (default: basic)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list incomplete logs, do not run run_mutation_for_log",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output_dir passed to run_mutation_for_log (default: same as results-dir)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full config for each run (verbose=True in run_mutation_for_log)",
    )
    parser.add_argument(
        "--local-model-path",
        type=str,
        default=DEFAULT_LOCAL_MODEL_BASE_PATH,
        help=f"Base directory for local/huggingface models (default: {DEFAULT_LOCAL_MODEL_BASE_PATH}); model_path = <this>/<model_name>",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device type: auto (automatic), cuda (use default GPU), cpu, cuda:1 (single GPU), or cuda:1,2,3 (multiple GPUs)",
    )
    parser.add_argument(
        "--reflect-model-name",
        type=str,
        default="deepseek-v3.2",
        help="Model for reflexion LLM (used when method directory is 'reflexion'). Default: deepseek-v3.2",
    )
    parser.add_argument(
        "--textgrad-engine-name",
        type=str,
        default="deepseek-v3.2",
        help="Engine for TextGrad backward/optimizer (used when method directory is 'textgrad'). Default: deepseek-v3.2",
    )
    parser.add_argument(
        "--a-mem-llm-model",
        type=str,
        default="deepseek-v3.2",
        dest="a_mem_sys_llm_model",
        help="LLM for memory module (used when method directory is 'a_mem_sys'). Default: deepseek-v3.2",
    )
    parser.add_argument(
        "--ace-reflector-model",
        type=str,
        default="deepseek-v3.2",
        dest="ace_reflector_model",
        help="Model for ACE Reflector (used when method directory is 'ace'). Default: deepseek-v3.2",
    )
    parser.add_argument(
        "--ace-curator-model",
        type=str,
        default="deepseek-v3.2",
        dest="ace_curator_model",
        help="Model for ACE Curator (used when method directory is 'ace'). Default: deepseek-v3.2",
    )
    args = parser.parse_args()

    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_root = args.results_dir or os.path.join(scripts_dir, "evaluation_results")
    results_root = os.path.abspath(results_root)
    output_dir = args.output_dir or results_root
    exclude_dirs = set(args.exclude)

    if not os.path.isdir(results_root):
        print(f"❌ Results root is not a directory: {results_root}")
        return 1

    incomplete = collect_incomplete_logs(results_root, exclude_dirs)
    print(f"📂 Scanned {results_root} (excluding {exclude_dirs})")
    print(f"📋 Found {len(incomplete)} log(s) with successful base task but incomplete mutation_sequence:\n")
    for p in incomplete:
        print(f"   {p}")
    if not incomplete:
        print("Nothing to run.")
        return 0
    if args.dry_run:
        print("\n🔍 Dry-run: not running mutations.")
        return 0

    print(f"\n{'='*80}")
    print(f"🚀 Running mutation sequence for {len(incomplete)} log(s)")
    print(f"{'='*80}\n")

    # Parse device early so we know whether to include 32B/30B (they need >=2 GPUs in pairs for TP2)
    gpu_ids = parse_gpu_ids_from_device(args.device)
    can_tp2 = gpu_ids is not None and len(gpu_ids) >= 2 and len(gpu_ids) % 2 == 0

    # Build work items: (log_path, model_type, model_name, method, model_path)
    work_items: list[tuple[str, str, str, str, str | None]] = []
    parse_failed: list[tuple[str, str]] = []
    for log_path in incomplete:
        model_type, model_name, method = parse_model_from_path(results_root, log_path)
        if model_type is None:
            print(f"⚠️  Skip (cannot parse path): {log_path}")
            parse_failed.append((log_path, "path parse failed"))
            continue
        # Skip 32B/30B only when we cannot use 2-GPU tensor parallel (need --device cuda:1,2 or similar with even count)
        if model_name and model_needs_tp2(model_name):
            if not can_tp2:
                print(f"⏭️  Skip 32B/30B model (need >=2 GPUs in pairs, e.g. --device cuda:1,2): {log_path}")
                continue
        model_path = None
        if model_type == "local":
            model_path = os.path.normpath(os.path.join(args.local_model_path, model_name))
        work_items.append((log_path, model_type, model_name, method, model_path))

    # Split work: 32B/30B use 2-GPU tensor parallel (TP2); others use data-parallel or sequential
    tp2_items = [w for w in work_items if w[1] == "local" and model_needs_tp2(w[2])]
    data_parallel_items = [w for w in work_items if w not in tp2_items]
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failed = list(parse_failed)

    # 1) Run 32B/30B with TP2 when we have >=2 GPUs in pairs (same as initial task: 1,2 together load model)
    if tp2_items and can_tp2 and gpu_ids is not None:
        gpu_pairs = [(gpu_ids[2 * i], gpu_ids[2 * i + 1]) for i in range(len(gpu_ids) // 2)]
        tp2_chunks: list[tuple[tuple[int, int], list[tuple[str, str, str, str, str | None]]]] = [
            (pair, []) for pair in gpu_pairs
        ]
        for i, item in enumerate(tp2_items):
            idx = i % len(gpu_pairs)
            tp2_chunks[idx][1].append(item)
        tp2_chunks = [(pair, chunk) for pair, chunk in tp2_chunks if chunk]
        if tp2_chunks:
            print(f"🔀 32B/30B TP2: {len(gpu_pairs)} worker(s), GPUs per worker: {[f'{a},{b}' for (a, b) in gpu_pairs]}")
            for (gpu_a, gpu_b), chunk in tp2_chunks:
                preview = [os.path.basename(os.path.dirname(p[0])) for p in chunk[:3]]
                extra = f" ... +{len(chunk)-3}" if len(chunk) > 3 else ""
                print(f"   GPUs {gpu_a},{gpu_b}: {len(chunk)} log(s) — {preview}{extra}")
            print()
            tp2_results = run_tp2_workers_parallel(
                tp2_chunks, scripts_dir, results_root, output_dir, args
            )
            for gpu_label, ok, code in tp2_results:
                if not ok:
                    chunk = next((c for (p, c) in tp2_chunks if f"{p[0]},{p[1]}" == gpu_label), [])
                    for item in chunk:
                        failed.append((item[0], f"exit_code={code}"))

    # 2) Run non-32B with data-parallel (one GPU per worker) when multiple GPUs and all local
    use_data_parallel = (
        data_parallel_items
        and all(w[1] == "local" for w in data_parallel_items)
        and gpu_ids is not None
        and len(gpu_ids) > 1
    )
    if use_data_parallel:
        work_chunks_dp: list[tuple[int, list[tuple[str, str, str, str, str | None]]]] = [
            (gpu_id, []) for gpu_id in gpu_ids
        ]
        for i, item in enumerate(data_parallel_items):
            idx = i % len(gpu_ids)
            work_chunks_dp[idx][1].append(item)
        work_chunks_dp = [(gid, chunk) for gid, chunk in work_chunks_dp if chunk]
        if work_chunks_dp:
            print(f"🔀 Multi-GPU data-parallel: {len(gpu_ids)} workers (GPUs: {gpu_ids})")
            for gpu_id, chunk in work_chunks_dp:
                preview = [os.path.basename(os.path.dirname(p[0])) for p in chunk[:3]]
                extra = f" ... +{len(chunk)-3}" if len(chunk) > 3 else ""
                print(f"   GPU {gpu_id}: {len(chunk)} log(s) — {preview}{extra}")
            print()
            worker_results = run_local_workers_parallel(
                work_chunks_dp, scripts_dir, results_root, output_dir, args
            )
            for gpu_id, ok, code in worker_results:
                if not ok:
                    chunk = next((c for gid, c in work_chunks_dp if gid == gpu_id), [])
                    for item in chunk:
                        failed.append((item[0], f"exit_code={code}"))

    # 3) Sequential: API model, single GPU, or remaining items (e.g. only 32B with 1 GPU already skipped)
    sequential_items = data_parallel_items if not use_data_parallel else []
    if sequential_items:
        # Sequential: single GPU or API model (each log in subprocess to free GPU memory after each run)
        single_gpu_id = int(gpu_ids[0]) if gpu_ids else 0
        for i, (log_path, model_type, model_name, method, model_path) in enumerate(sequential_items, 1):
            print(f"[{i}/{len(sequential_items)}] {log_path}")
            print(f"     model_type={model_type}, model_name={model_name}, method={method}")
            if model_path:
                print(f"     model_path={model_path}")
            try:
                if model_type == "local":
                    env = os.environ.copy()
                    env["CUDA_VISIBLE_DEVICES"] = str(single_gpu_id)
                    env["PYTHONUNBUFFERED"] = "1"
                    cmd = build_mutation_argv(
                        log_path, model_type, model_name, method, model_path, output_dir, args
                    )
                    proc = subprocess.run(
                        cmd,
                        cwd=scripts_dir,
                        env=env,
                    )
                    exit_code = proc.returncode
                else:
                    exit_code, _ = run_mutation_for_log(
                        log_path,
                        model_type=model_type,
                        model_name=model_name,
                        method=method,
                        output_dir=output_dir,
                        device=args.device,
                        verbose=args.verbose,
                        model_path=model_path,
                        reflect_model_name=getattr(args, "reflect_model_name", None),
                        textgrad_engine_name=getattr(args, "textgrad_engine_name", None),
                        a_mem_sys_llm_model=getattr(args, "a_mem_sys_llm_model", None),
                        ace_reflector_model=getattr(args, "ace_reflector_model", None),
                        ace_curator_model=getattr(args, "ace_curator_model", None),
                    )
                if exit_code != 0:
                    failed.append((log_path, f"exit_code={exit_code}"))
                    print(f"     ❌ Exit code {exit_code}")
                else:
                    print(f"     ✅ Done")
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                return 130
            except Exception as e:
                failed.append((log_path, str(e)))
                print(f"     ❌ Error: {e}")

    print(f"\n{'='*80}")
    print("📊 Summary")
    print(f"{'='*80}")
    print(f"Total: {len(incomplete)}, Failed: {len(failed)}")
    if failed:
        for path, reason in failed:
            print(f"  - {path}: {reason}")
    print(f"{'='*80}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
