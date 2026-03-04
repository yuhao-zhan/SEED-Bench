#!/usr/bin/env python3
"""Evaluation result statistics.

Computes aggregated metrics across task pairs, models, and methods,
and outputs LaTeX tables (default) or markdown tables.
"""

import os
import sys
import re
import io
import json
import math
import token
import tokenize
import argparse
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from evaluation.utils import get_evaluation_results_dir

RESULTS_DIR = get_evaluation_results_dir()

# discovery@T: k values
DISCOVERY_K_VALUES = (3, 5, 10, 15, 20)

# Token types to skip
_SKIP_TOKEN_TYPES = {
    token.NEWLINE, token.NL, token.INDENT, token.DEDENT,
    token.ENCODING, token.ENDMARKER, token.COMMENT,
}


def count_code_tokens(code_str):
    if not code_str or not code_str.strip():
        return 0
    try:
        tokens = tokenize.generate_tokens(io.StringIO(code_str).readline)
        return sum(1 for t in tokens if t.type not in _SKIP_TOKEN_TYPES)
    except (tokenize.TokenError, IndentationError):
        lines = [l for l in code_str.splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        return len(lines)


def get_best_code(data):
    if data.get('best_score', 0.0) > 0 and data.get('best_code'):
        return data['best_code']
    history = data.get('history', [])
    if history:
        for entry in reversed(history):
            if entry.get('code'):
                return entry['code']
    return data.get('best_code', '')


def get_code_usage(data):
    return count_code_tokens(get_best_code(data))


def compute_efficiency(data):
    tokens = get_code_usage(data)
    if tokens == 0:
        return 0.0
    return data.get('best_score', 0.0) / tokens


def load_results(results_dir, task_filter='all'):
    results = defaultdict(lambda: defaultdict(dict))
    all_file_ids = set()

    # The new structure is results_dir/{category}/{task}/{model}/{method}/*.json
    # The old structure was results_dir/{task_name}/{model}/{method}/*.json
    
    # We'll use os.walk to handle both structures or any nesting
    for root, dirs, files in os.walk(results_dir):
        # We are looking for files in a 'method' directory which is inside a 'model' directory
        # path structure: .../{model}/{method}/{file}.json
        path_parts = root.split(os.sep)
        if len(path_parts) < 2:
            continue
            
        method = path_parts[-1]
        model = path_parts[-2]
        
        # Basic validation that we are in a results leaf directory
        if method in _IGNORED_METHODS or _should_ignore_model(model):
            continue

        # Check if the task matches the filter
        # root is like '.../evaluation_results/Category1_Statics_Equilibrium/S_01/Qwen3-8B/baseline'
        # or '.../evaluation_results/category_1_01/Qwen3-8B/baseline'
        task_match = False
        if task_filter == 'all':
            task_match = True
        else:
            # Check if any part of the path matches task_filter
            # (e.g. 'category_1' or 'S_01' or 'category_1_01')
            for part in path_parts:
                if task_filter.startswith('category_') and part.startswith(task_filter):
                    task_match = True
                    break
                if part == task_filter:
                    task_match = True
                    break
        
        if not task_match:
            continue

        for fn in files:
            if not fn.endswith('.json'):
                continue
            
            # User requirement: ONLY consider json files with filename like all_{source_stage}_to_{target_stage}*.json
            # And EXCLUDE those like all_1st_pass_20260301_pseudo.json
            if not fn.startswith('all_'):
                continue
            
            # Match pattern: all_{source}_to_{target}*.json
            # regex: all_.+_to_.+.*\.json
            if not re.match(r'^all_.+_to_.+.*\.json$', fn):
                continue
            
            # Exclude pseudo files
            if '_pseudo' in fn:
                continue

            file_path = os.path.join(root, fn)
            # Create a unique file_id that includes task and filename
            # For new structure, root might be .../Category1/S_01/Model/Method
            # Let's try to extract task name from path
            try:
                # Assuming standard structure, task_name is 3 levels up from file
                task_name = path_parts[-3] 
                file_id = f"{task_name}/{fn}"
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results[model][method][file_id] = data
                all_file_ids.add(file_id)
            except Exception as e:
                # Skip files that don't fit the structure or fail to load
                pass

    return results, sorted(list(all_file_ids))


def compute_metrics(model_method_results, all_file_ids):
    n_total = len(all_file_ids)
    if n_total == 0:
        return {}

    success_cnt = 0
    scores = []
    iters = []
    efficiencies = []
    code_usages = []
    discovery = {k: 0 for k in DISCOVERY_K_VALUES}
    
    _MAX_ITER = 20

    for fid in all_file_ids:
        data = model_method_results.get(fid)
        if not data:
            scores.append(0.0)
            iters.append(_MAX_ITER)
            efficiencies.append(0.0)
            code_usages.append(0.0)
            continue

        best_score = data.get('best_score', 0.0)
        is_success = data.get('success', False)
        total_iters = data.get('iterations', _MAX_ITER)
        
        if is_success:
            success_cnt += 1
            
        scores.append(best_score)
        iters.append(total_iters)
        efficiencies.append(compute_efficiency(data))
        code_usages.append(get_code_usage(data))
        
        for k in DISCOVERY_K_VALUES:
            if is_success and total_iters <= k:
                discovery[k] += 1

    return {
        'Pass@1': (success_cnt / n_total) * 100,
        'Score-Avg': sum(scores) / n_total,
        'Iteration-Avg': sum(iters) / n_total,
        'Efficiency-Avg': sum(efficiencies) / n_total,
        'CodeUsage-Avg': sum(code_usages) / n_total,
        **{f'Discovery@{k}': (discovery[k] / n_total) * 100 for k in DISCOVERY_K_VALUES}
    }


def _should_ignore_model(full_name):
    name = full_name
    for prefix in _MODEL_NAME_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name in _IGNORED_MODELS


def short_model_name(name):
    for prefix in _MODEL_NAME_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return _MODEL_NAME_ABBREV.get(name, name)


_MODEL_NAME_PREFIXES = ('openai_', 'anthropic_', 'huggingface_', 'local_')
_MODEL_NAME_ABBREV = {
    'gemini-3-flash-preview': 'gemini-3-flash',
    'gemini-3-flash-preview-thinking': 'gemini-3-think',
    'gemini-3-pro-preview': 'gemini-3-pro'
}
_IGNORED_MODELS = {'gpt-4o', 'gpt-oss-20b', 'gemini-3-flash-preview-thinking', 'o3-mini', 'Qwen3-1.7B', 'Qwen3-4B'}
_IGNORED_METHODS = {'absolute_zero', 'self_refine_inner_only', 'baseline_backup', 'sys_feedback_backup', 'a_mem_sys'}

MODEL_COLUMN_ORDER = [
    'Qwen3-8B', 'Qwen3-14B', 'Qwen3-32B',
    'claude-opus-4-6', 'deepseek-v3.2', 'deepseek-v3.2-think', 'gemini-3-flash', 'gemini-3-pro',
]

METHOD_DISPLAY_NAMES = {
    'baseline': 'vanilla',
    'sys_feedback': 'sys_feedback',
    'textgrad': 'textgrad',
    'reflexion': 'reflexion',
    'self_refine': 'self_refine',
    'ace': 'ace',
    'rememberer': 'rememberer',
    'expel': 'expel',
    'memento_nonparametric': 'memento',
    'reasoning_bank': 'reasoningbank',
    'tree_of_thought': 'ToT',
    'science_codeevolve': 'CodeEvolve',
    'alpha_evolve': 'AlphaEvolve',
    'seal': 'seal',
    'ragen': 'ragen',
    'genome': 'genome',
    'soar': 'soar',
    'theta_evolve': 'ThetaEvolve',
    'discover': 'TTT-Discover',
    'absolute_zero_iter': 'Absolute-Zero',
}

METHOD_CATEGORIES = {
    'Context Evolution': ['baseline', 'sys_feedback', 'textgrad', 'reflexion', 'self_refine'],
    'Memory Evolution': ['ace', 'rememberer', 'expel', 'memento_nonparametric', 'reasoning_bank'],
    'Inference-time Search': ['tree_of_thought', 'science_codeevolve', 'alpha_evolve'],
    'Parameter Evolution': ['seal', 'ragen', 'genome', 'soar', 'theta_evolve', 'discover', 'absolute_zero_iter'],
}


def method_display_name(internal_name):
    return METHOD_DISPLAY_NAMES.get(internal_name, internal_name)


def _get_ordered_models(models):
    order_map = {s: i for i, s in enumerate(MODEL_COLUMN_ORDER)}
    def sort_key(m):
        short = short_model_name(m)
        idx = order_map.get(short, len(MODEL_COLUMN_ORDER))
        return (idx, short)
    return sorted(models, key=sort_key)


def _get_ordered_methods(methods):
    ordered = []
    for cat in METHOD_CATEGORIES.values():
        for m in cat:
            if m in methods:
                ordered.append(m)
    for m in methods:
        if m not in ordered:
            ordered.append(m)
    return ordered


def print_latex_table(metric_name, models, methods, data, bold_best=True):
    n_cols = 1 + len(models)
    ordered_methods = _get_ordered_methods(methods)
    
    col_max = {}
    for model in models:
        vals = []
        for method in ordered_methods:
            v = data.get((model, method))
            if v is not None and not math.isnan(v):
                vals.append(float(v))
        col_max[model] = max(vals) if vals else None

    model_headers = [short_model_name(m) for m in models]
    col_spec = 'l' + 'c' * len(models)

    print(r'\begin{table*}[t]')
    print(r'    \centering')
    print(f'    \\caption{{Performance comparison: {metric_name}}}')
    print(r'    \resizebox{\textwidth}{!}{')
    print(f'    \\begin{{tabular}}{{{col_spec}}}')
    print(r'        \toprule')
    print('        \\textbf{Method} & ' + ' & '.join(f'\\textbf{{{h}}}' for h in model_headers) + r' \\')
    print(r'        \midrule')

    for cat_name, cat_methods in METHOD_CATEGORIES.items():
        present_methods = [m for m in cat_methods if m in methods]
        if not present_methods: continue
        print(f'        \\multicolumn{{{n_cols}}}{{l}}{{\\textit{{{cat_name}}}}} \\\\')
        print(r'        \midrule')
        for method in present_methods:
            cells = []
            for model in models:
                v = data.get((model, method))
                if v is None or math.isnan(v):
                    cells.append('N/A')
                else:
                    s = f'{v:.2f}'
                    if bold_best and col_max.get(model) is not None and abs(v - col_max[model]) < 1e-6:
                        s = f'\\textbf{{{s}}}'
                    cells.append(s)
            print(f'        {method_display_name(method)} & ' + ' & '.join(cells) + r' \\')
        print(r'        \midrule')

    print(r'        \bottomrule')
    print(r'    \end{tabular}}')
    print(r'\end{table*}')
    print()


def print_markdown_table(name, models, methods, data):
    print(f'\n### {name}\n')
    model_headers = [short_model_name(m) for m in models]
    print('| Method | ' + ' | '.join(model_headers) + ' |')
    print('| --- | ' + ' | '.join(['---'] * len(models)) + ' |')
    for method in _get_ordered_methods(methods):
        cells = []
        for model in models:
            v = data.get((model, method))
            cells.append(f'{v:.2f}' if v is not None and not math.isnan(v) else 'N/A')
        print(f'| {method_display_name(method)} | ' + ' | '.join(cells) + ' |')


def plot_results(tables, models, methods, output_dir):
    if not HAS_MATPLOTLIB: return
    
    os.makedirs(output_dir, exist_ok=True)
    plt.rcParams.update({'font.size': 12, 'figure.dpi': 200})
    
    ordered_methods = _get_ordered_methods(methods)
    method_labels = [method_display_name(m) for m in ordered_methods]
    model_labels = [short_model_name(m) for m in models]
    
    # --- 1. Primary Metrics Heatmaps ---
    for metric, label, filename in [
        ('Pass@1', 'Pass Rate (%)', 'pass_rate_heatmap'),
        ('Score-Avg', 'Average Score', 'score_avg_heatmap'),
        ('Iteration-Avg', 'Avg Iterations', 'iteration_avg_heatmap'),
        ('Efficiency-Avg', 'Efficiency (Score/Token)', 'efficiency_avg_heatmap'),
        ('CodeUsage-Avg', 'Code Usage (Tokens)', 'code_usage_avg_heatmap'),
    ]:
        if not tables.get(metric) or not ordered_methods or not models:
            continue
            
        fig, ax = plt.subplots(figsize=(len(ordered_methods)*0.8 + 2, len(models)*0.6 + 2))
        data = []
        for model in models:
            row = []
            for method in ordered_methods:
                v = tables[metric].get((model, method), float('nan'))
                row.append(v)
            data.append(row)
        
        # Manually mask NaNs for imshow
        v_min = 0
        v_max = 100 if 'Pass' in metric else None
        if v_max is None:
            finite_vals = [v for row in data for v in row if not math.isnan(v)]
            v_max = max(finite_vals) if finite_vals else 1.0
            
        masked_data = [[(v if not math.isnan(v) else 0) for v in row] for row in data]
        
        im = ax.imshow(masked_data, cmap='Blues', vmin=v_min, vmax=v_max)
        ax.set_xticks(range(len(ordered_methods)))
        ax.set_yticks(range(len(models)))
        ax.set_xticklabels(method_labels, rotation=45, ha='right')
        ax.set_yticklabels(model_labels)
        
        for i in range(len(models)):
            for j in range(len(ordered_methods)):
                val = data[i][j]
                if not math.isnan(val):
                    txt = f'{val:.1f}' if 'Efficiency' in metric or 'Score' in metric else f'{val:.0f}'
                    ax.text(j, i, txt, ha='center', va='center', color='white' if val > v_max/2 else 'black', fontsize=9)
        
        plt.title(f'{label} Across Task Pairs')
        plt.colorbar(im, label=label)
        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, f'{filename}.png'))
        plt.close(fig)

    # --- 2. Qwen Model Comparison ---
    qwen_models = [m for m in models if short_model_name(m) in ('Qwen3-8B', 'Qwen3-14B')]
    if qwen_models and ordered_methods:
        fig, ax = plt.subplots(figsize=(max(12, len(ordered_methods)*0.6), 6))
        x = list(range(len(ordered_methods)))
        width = 0.35
        
        for i, model in enumerate(qwen_models):
            vals = [tables['Score-Avg'].get((model, m), 0) for m in ordered_methods]
            vals = [v if not math.isnan(v) else 0 for v in vals]
            ax.bar([pos + (i-0.5)*width for pos in x], vals, width, label=short_model_name(model))
            
        ax.set_ylabel('Average Score')
        ax.set_title('Qwen3-8B vs Qwen3-14B Score Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(method_labels, rotation=45, ha='right')
        ax.legend()
        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, 'qwen_score_comparison.png'))
        plt.close(fig)

    # --- 3. Discovery Rate Line Plot ---
    if models:
        fig, ax = plt.subplots(figsize=(8, 6))
        k_vals = list(DISCOVERY_K_VALUES)
        for model in models:
            y = []
            for k in k_vals:
                vals = [tables[f'Discovery@{k}'].get((model, m)) for m in methods if (model, m) in tables[f'Discovery@{k}']]
                vals = [v for v in vals if v is not None and not math.isnan(v)]
                avg = sum(vals) / len(vals) if vals else 0
                y.append(avg)
            ax.plot(k_vals, y, 'o-', label=short_model_name(model), linewidth=2)
        
        ax.set_xlabel('Max Iterations (T)')
        ax.set_ylabel('Discovery Rate (%)')
        ax.set_title('Average Discovery Rate@T')
        ax.set_xticks(k_vals)
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.tight_layout()
        fig.savefig(os.path.join(output_dir, 'discovery_rate_agg.png'))
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=str, default='all')
    parser.add_argument('--format', choices=('latex', 'markdown'), default='markdown')
    parser.add_argument('--no-per-task', action='store_true', help='Disable per-task statistics output')
    args = parser.parse_args()

    results, all_file_ids = load_results(RESULTS_DIR, args.task)
    if not all_file_ids:
        print(f"No results found for filter: {args.task}")
        return

    models = _get_ordered_models(list(results.keys()))
    methods = _get_ordered_methods({m for model in results for m in results[model]})

    metric_names = ['Pass@1', 'Score-Avg', 'Iteration-Avg', 'Efficiency-Avg', 'CodeUsage-Avg']
    metric_names += [f'Discovery@{k}' for k in DISCOVERY_K_VALUES]

    # --- 1. Aggregated Statistics (Current logic) ---
    tables = {mn: {} for mn in metric_names}
    for model in models:
        for method in methods:
            if method not in results[model]: continue
            metrics = compute_metrics(results[model][method], all_file_ids)
            for mn in metric_names:
                tables[mn][(model, method)] = metrics.get(mn, float('nan'))

    # Efficiency Normalization (Global)
    eff_key = 'Efficiency-Avg'
    all_eff = [v for v in tables[eff_key].values() if not math.isnan(v)]
    if all_eff:
        max_eff = max(all_eff)
        if max_eff > 0:
            for k in tables[eff_key]:
                if not math.isnan(tables[eff_key][k]):
                    tables[eff_key][k] /= max_eff

    print(f"\n# Evaluation Results for {args.task}\n")
    print(f"Filter: {args.task} | Unique transitions: {len(all_file_ids)}")

    print(f"\n## Aggregated Statistics (All Tasks Combined)\n")
    for mn in metric_names:
        if args.format == 'latex':
            print_latex_table(mn, models, methods, tables[mn])
        else:
            print_markdown_table(mn, models, methods, tables[mn])

    # --- 2. Per-Task Statistics (New logic) ---
    if not args.no_per_task:
        # Group file_ids by task
        task_groups = defaultdict(list)
        for fid in all_file_ids:
            task_name = fid.split('/')[0]
            task_groups[task_name].append(fid)
        
        # Sort task names
        sorted_tasks = sorted(task_groups.keys())
        
        if len(sorted_tasks) > 1: # Only output per-task if there is more than 1 task or if specifically requested
            print(f"\n## Per-Task Statistics\n")
            for task_name in sorted_tasks:
                task_fids = task_groups[task_name]
                print(f"\n### Task: {task_name} ({len(task_fids)} transitions)\n")
                
                # Compute metrics for this specific task
                task_tables = {mn: {} for mn in metric_names}
                for model in models:
                    for method in methods:
                        if method not in results[model]: continue
                        task_metrics = compute_metrics(results[model][method], task_fids)
                        for mn in metric_names:
                            task_tables[mn][(model, method)] = task_metrics.get(mn, float('nan'))
                
                # Output tables for each metric
                for mn in metric_names:
                    # Skip efficiency normalization here or keep it consistent? 
                    # For simplicity, we skip per-task efficiency normalization or keep it absolute
                    if args.format == 'latex':
                        print_latex_table(mn, models, methods, task_tables[mn])
                    else:
                        print_markdown_table(mn, models, methods, task_tables[mn])

    # --- 3. Plots ---
    plot_dir = os.path.join(RESULTS_DIR, 'plots', args.task)
    plot_results(tables, models, methods, plot_dir)
    print(f"\nPlots saved to: {plot_dir}")

if __name__ == '__main__':
    main()
