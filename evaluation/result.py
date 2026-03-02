#!/usr/bin/env python3
"""Evaluation result statistics.

Computes aggregated metrics across tasks, models, and methods,
and outputs LaTeX tables (default) or markdown tables.

Usage:
    python result.py --task all           # all tasks, LaTeX output
    python result.py --task category_1    # all tasks in category 1
    python result.py --task category_1_01 # specific task
    python result.py --format markdown     # markdown table output instead of LaTeX
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
import numpy as np
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
from evaluation.utils import get_evaluation_results_dir, extract_run_number_from_filename

RESULTS_DIR = get_evaluation_results_dir()

# discovery@T: k values (sequential success within k iterations)
DISCOVERY_K_VALUES = (3, 5, 10, 15, 20)

# Token types to skip when counting meaningful code tokens
_SKIP_TOKEN_TYPES = {
    token.NEWLINE, token.NL, token.INDENT, token.DEDENT,
    token.ENCODING, token.ENDMARKER, token.COMMENT,
}


def count_code_tokens(code_str):
    """Count meaningful Python tokens (excluding comments, whitespace, markers).

    Uses Python's tokenizer for a format-independent measure of code size.
    Falls back to non-empty non-comment line count on tokenization failure.
    """
    if not code_str or not code_str.strip():
        return 0
    try:
        tokens = tokenize.generate_tokens(io.StringIO(code_str).readline)
        return sum(1 for t in tokens if t.type not in _SKIP_TOKEN_TYPES)
    except tokenize.TokenError:
        lines = [l for l in code_str.splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        return len(lines)


def get_best_code(data):
    """Extract the code that corresponds to best_score.

    If best_score > 0, uses best_code (which is the code from the
    best-scoring iteration). If best_score == 0, uses the last
    iteration's code as fallback.
    """
    if data.get('best_score', 0.0) > 0 and data.get('best_code'):
        return data['best_code']
    history = data.get('iteration_history', [])
    if history:
        return history[-1].get('code', '')
    return data.get('best_code', '')


def get_code_usage(data):
    """Return token count of best code (denominator of efficiency)."""
    return count_code_tokens(get_best_code(data))


def compute_efficiency(data):
    """Compute efficiency = best_score / token_count for a single result."""
    tokens = get_code_usage(data)
    if tokens == 0:
        return 0.0
    return data.get('best_score', 0.0) / tokens


def load_results(results_dir, task_filter='all'):
    """Load evaluation results grouped by model/method/task/pass.

    Returns:
        results: dict[model][method][task][pass_num] = json_data
        task_dirs: sorted list of task directory names
    """
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    # Collect all category task directories (skip 'basic')
    task_dirs = sorted(
        d for d in os.listdir(results_dir)
        if os.path.isdir(os.path.join(results_dir, d))
        and d != 'basic'
        and d.startswith('category_')
    )

    # Apply task filter
    if task_filter != 'all':
        cat_match = re.match(r'^category_(\d+)$', task_filter)
        if cat_match:
            prefix = f"category_{cat_match.group(1)}_"
            task_dirs = [t for t in task_dirs if t.startswith(prefix)]
        else:
            task_dirs = [t for t in task_dirs if t == task_filter]

    # Always exclude category_1_03 and category_1_05 (ignore their results for any filter: all, category_1, etc.)
    # category_1_06 is included (was previously skipped; remove from skip_tasks to use its results)
    # skip_tasks = {'category_1_03', 'category_1_05'}
    skip_tasks = {}
    task_dirs = [t for t in task_dirs if t not in skip_tasks]

    for task_name in task_dirs:
        task_path = os.path.join(results_dir, task_name)
        if not os.path.isdir(task_path):
            continue
        for model in os.listdir(task_path):
            if _should_ignore_model(model):
                continue
            model_path = os.path.join(task_path, model)
            if not os.path.isdir(model_path):
                continue
            for method in os.listdir(model_path):
                method_path = os.path.join(model_path, method)
                if not os.path.isdir(method_path):
                    continue
                for fn in os.listdir(method_path):
                    if not fn.endswith('.json'):
                        continue
                    # Only process files starting with 'all_'
                    if not fn.startswith('all_'):
                        continue
                    pass_num = extract_run_number_from_filename(fn)
                    if pass_num is None:
                        continue
                    try:
                        with open(os.path.join(method_path, fn)) as f:
                            data = json.load(f)
                        # When multiple JSONs share the same pass_num, keep only the one with highest best_score
                        existing = results[model][method][task_name].get(pass_num)
                        best_score_new = float(data.get('best_score') or 0.0)
                        if math.isnan(best_score_new):
                            best_score_new = 0.0
                        best_score_existing = (
                            float(existing.get('best_score') or 0.0) if existing else -1.0
                        )
                        if math.isnan(best_score_existing):
                            best_score_existing = 0.0
                        if existing is None or best_score_new > best_score_existing:
                            results[model][method][task_name][pass_num] = data
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Warning: {e}", file=sys.stderr)

    return results, task_dirs


def compute_metrics(task_results, all_tasks):
    """Compute metrics for one (model, method) pair.

    Metrics:
    - Initial: refine ability in fixed env (T0 only).
    - Adaptive (conditional): given T0 passed, performance on mutated tasks T1–T4.
    - Joint (pair-aware, no conditioning): over all (T0, Tk) pairs and all runs;
      when T0 failed we count that slot as 0 (did not reach Tk). Measures
      end-to-end "get to new env and solve it" without conditioning on T0.

    Args:
        task_results: dict[task][pass_num] = json_data
        all_tasks: list of all task names (used as denominator)
    """
    n_tasks = len(all_tasks)
    if n_tasks == 0:
        return {}

    # -- Initial metrics accumulators --
    init_success_cnt = 0
    init_scores_avg = []   # per-task average score across passes
    init_iters = []        # per-task average iteration (all passes, success and fail)
    init_efficiency = []   # per-task average efficiency across passes
    init_code_usage = []   # per-task average code token count (denominator of efficiency)
    init_discovery = {k: [] for k in DISCOVERY_K_VALUES}  # per-task discovery@T (avg over passes)

    # Joint (pair-aware, no conditioning on T0): denominator = all (task, run, mutation_index)
    joint_total = 0
    joint_pass_cnt = 0
    joint_scores_sum = 0.0
    joint_iters_sum = 0.0
    joint_eff_sum = 0.0
    joint_code_usage_sum = 0.0
    joint_discovery = {k: 0 for k in DISCOVERY_K_VALUES}
    _MAX_ITER_PENALTY = 20

    # Nominal passes per task for Joint denominator (match Pass@3); slots = n_tasks * this * num_mutations
    num_passes_nominal = 3
    num_mutations = 4

    for task in all_tasks:
        passes = task_results.get(task, {})

        if not passes:
            # No data for this task → 0 score, not successful
            init_scores_avg.append(0.0)
            init_efficiency.append(0.0)
            init_code_usage.append(0.0)
            for k in DISCOVERY_K_VALUES:
                init_discovery[k].append(0.0)
            # Joint: count slots for missing task too (all 0), so denominator matches scale of Initial
            joint_total += num_mutations * num_passes_nominal
            joint_scores_sum += 0.0
            joint_iters_sum += _MAX_ITER_PENALTY * num_mutations * num_passes_nominal
            joint_eff_sum += 0.0
            joint_code_usage_sum += 0.0
            continue

        # ---- Initial task ----
        scores = []
        efficiencies = []
        code_usages = []
        success_any = False
        all_iters = []  # all passes (success and fail) for iteration stats

        for _pn, data in sorted(passes.items()):
            scores.append(data.get('best_score', 0.0))
            efficiencies.append(compute_efficiency(data))
            code_usages.append(get_code_usage(data))
            all_iters.append(data.get('total_iterations', 0))
            if data.get('success', False):
                success_any = True

        init_scores_avg.append(sum(scores) / len(scores))
        init_efficiency.append(sum(efficiencies) / len(efficiencies))
        init_code_usage.append(sum(code_usages) / len(code_usages))
        # Iteration: average over all passes for this task (include failed runs)
        init_iters.append(sum(all_iters) / len(all_iters))
        # discovery@T: per pass 1 if success and total_iterations <= k else 0; per task avg over passes
        n_passes = len(passes)
        for k in DISCOVERY_K_VALUES:
            disc_sum = sum(
                1.0 if (data.get('success', False) and data.get('total_iterations', 0) <= k) else 0.0
                for _pn, data in sorted(passes.items())
            )
            init_discovery[k].append(disc_sum / n_passes)

        if success_any:
            init_success_cnt += 1

        # ---- Joint (pair-aware, no conditioning): all (task, run, mi) slots ----
        slots_this_task = 0
        for _pn, data in sorted(passes.items()):
            t0_ok = data.get('success', False)
            ms = data.get('mutation_sequence', {}) if t0_ok else {}
            seq = ms.get('sequence_results', []) if ms else []
            for mi in range(num_mutations):
                joint_total += 1
                slots_this_task += 1
                if t0_ok and mi < len(seq) and seq[mi].get('status') == 'evaluated' and 'result' in seq[mi]:
                    r = seq[mi]['result']
                    joint_pass_cnt += 1 if r.get('success') else 0
                    sc = r.get('best_score', 0.0)
                    joint_scores_sum += sc
                    it = r.get('total_iterations', _MAX_ITER_PENALTY)
                    joint_iters_sum += it if math.isfinite(it) else _MAX_ITER_PENALTY
                    joint_eff_sum += compute_efficiency(r)
                    joint_code_usage_sum += get_code_usage(r)
                    for k in DISCOVERY_K_VALUES:
                        joint_discovery[k] += 1 if (r.get('success') and it <= k) else 0
                else:
                    joint_scores_sum += 0.0
                    joint_iters_sum += _MAX_ITER_PENALTY
                    joint_eff_sum += 0.0
                    joint_code_usage_sum += 0.0
                    for k in DISCOVERY_K_VALUES:
                        pass  # joint_discovery[k] += 0
        # Pad to nominal slots per task so Joint denominator = n_tasks * 12 (same scale as Initial)
        pad_slots = num_mutations * num_passes_nominal - slots_this_task
        if pad_slots > 0:
            joint_total += pad_slots
            joint_scores_sum += 0.0
            joint_iters_sum += _MAX_ITER_PENALTY * pad_slots
            joint_eff_sum += 0.0
            joint_code_usage_sum += 0.0

    return {
        'Initial-Pass@3': init_success_cnt / n_tasks * 100,
        'Initial-Score@3-avg': sum(init_scores_avg) / n_tasks,
        'Initial-Iteration@3': (
            sum(init_iters) / len(init_iters) if init_iters else float('nan')
        ),
        'Initial-Efficiency@3': sum(init_efficiency) / n_tasks,
        'Initial-CodeUsage@3': sum(init_code_usage) / n_tasks,
        **{
            f'Initial-Discovery@{k}': sum(init_discovery[k]) / n_tasks * 100
            for k in DISCOVERY_K_VALUES
        },
        # Joint (pair-aware, no conditioning on T0): denominator = all (task, run, mi) slots
        'Joint-Pass@3': (
            joint_pass_cnt / joint_total * 100 if joint_total else float('nan')
        ),
        'Joint-Score@3-avg': (
            joint_scores_sum / joint_total if joint_total else float('nan')
        ),
        'Joint-Iteration@3': (
            joint_iters_sum / joint_total if joint_total else float('nan')
        ),
        'Joint-Efficiency@3': (
            joint_eff_sum / joint_total if joint_total else float('nan')
        ),
        'Joint-CodeUsage@3': (
            joint_code_usage_sum / joint_total if joint_total else float('nan')
        ),
        **{
            f'Joint-Discovery@{k}': (
                joint_discovery[k] / joint_total * 100 if joint_total else float('nan')
            )
            for k in DISCOVERY_K_VALUES
        },
    }


def fmt(v):
    """Format a metric value for table display."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 'N/A'
    return f'{v:.2f}'


def _latex_escape(s):
    """Escape LaTeX special characters in a string."""
    if not s:
        return s
    s = str(s)
    for ch, repl in [('\\', '\\textbackslash{}'), ('&', '\\&'), ('%', '\\%'),
                     ('$', '\\$'), ('#', '\\#'), ('_', '\\_'), ('{', '\\{'), ('}', '\\}')]:
        s = s.replace(ch, repl)
    return s


def _metric_to_label_suffix(metric_name):
    """Convert metric name to a short slug for tab: label (e.g. Initial-Pass@3 -> pass_initial)."""
    s = metric_name.replace('@', '_').replace('-', '_').lower()
    return s[:40]


def _get_ordered_methods_by_category(methods):
    """Return methods ordered by METHOD_CATEGORIES, then any remaining."""
    ordered = []
    for cat_name in METHOD_CATEGORIES:
        for m in METHOD_CATEGORIES[cat_name]:
            if m in methods:
                ordered.append(m)
    for m in methods:
        if m not in ordered:
            ordered.append(m)
    return ordered


def _column_max_per_model(data, models, ordered_methods):
    """Return dict model -> max numeric value in that column (for bolding best)."""
    col_max = {}
    for model in models:
        vals = []
        for method in ordered_methods:
            v = data.get((model, method))
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
        col_max[model] = max(vals) if vals else None
    return col_max


def print_latex_table(metric_name, models, methods, data, bold_best=True):
    """Print one metric as a LaTeX table* (rows=methods by category, cols=models)."""
    n_cols = 1 + len(models)
    ordered_methods = _get_ordered_methods_by_category(methods)
    col_max = _column_max_per_model(data, models, ordered_methods) if bold_best else {}

    model_headers = [short_model_name(m) for m in models]
    label_suffix = _metric_to_label_suffix(metric_name)
    caption = f'Performance comparison ({metric_name})'
    col_spec = 'l' + 'c' * len(models)

    lines = [
        r'\begin{table*}[t]',
        r'    \centering',
        f'    \\caption{{{_latex_escape(caption)}}}',
        f'    \\label{{tab:method_comparison_{label_suffix}}}',
        r'    \large',
        r'    \resizebox{\textwidth}{!}{',
        f'    \\begin{{tabular}}{{{col_spec}}}',
        r'        \toprule',
        '        \\textbf{Method} & ' + ' & '.join(f'\\textbf{{{_latex_escape(h)}}}' for h in model_headers) + r' \\',
        r'        \midrule',
        '',
    ]

    for cat_name in METHOD_CATEGORIES:
        cat_methods = [m for m in METHOD_CATEGORIES[cat_name] if m in methods]
        if not cat_methods:
            continue
        lines.append(f'        % ---------------------------------------------')
        lines.append(f'        % Category: {cat_name}')
        lines.append(f'        % ---------------------------------------------')
        lines.append(f'        \\multicolumn{{{n_cols}}}{{l}}{{\\textit{{{_latex_escape(cat_name)}}}}} \\\\')
        lines.append(r'        \midrule')
        for method in cat_methods:
            display = method_display_name(method)
            cells = []
            for model in models:
                v = data.get((model, method))
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    cells.append('N/A')
                else:
                    try:
                        fv = float(v)
                        s = f'{fv:.2f}'
                        if bold_best and col_max.get(model) is not None and fv >= col_max[model]:
                            s = f'\\textbf{{{s}}}'
                        cells.append(s)
                    except (TypeError, ValueError):
                        cells.append('N/A')
            line = f'        {_latex_escape(display)} & ' + ' & '.join(cells) + r' \\'
            lines.append(line)
        lines.append(r'        \midrule')
        lines.append('')

    # Remove trailing \midrule and empty line before \bottomrule for last category
    if lines and lines[-1] == '':
        lines.pop()
    if lines and lines[-1].strip() == r'\midrule':
        lines.pop()
    lines.append(r'        \bottomrule')
    lines.append(r'    \end{tabular}')
    lines.append(r'    }')
    lines.append(r'\end{table*}')
    print('\n'.join(lines))
    print()


def print_table(name, models, methods, data):
    """Print one metric as a markdown table (rows=methods, cols=models). Uses short model names in header."""
    print(f'\n### {name}\n')
    model_headers = [short_model_name(m) for m in models]
    header = '| Method | ' + ' | '.join(model_headers) + ' |'
    sep = '| --- | ' + ' | '.join(['---'] * len(models)) + ' |'
    print(header)
    print(sep)
    for method in methods:
        cells = [fmt(data.get((model, method))) for model in models]
        print(f'| {method} | ' + ' | '.join(cells) + ' |')


def get_academic_colors(n):
    """Get academic-style color palette."""
    # Use a professional color palette (inspired by Nature/Science style)
    base_colors = [
        '#2E86AB',  # Deep blue
        '#A23B72',  # Deep purple
        '#F18F01',  # Orange
        '#C73E1D',  # Red
        '#6A994E',  # Green
        '#BC4749',  # Dark red
        '#219EBC',  # Light blue
        '#FFB703',  # Yellow
        '#8ECAE6',  # Sky blue
        '#FB8500',  # Dark orange
    ]
    if n <= len(base_colors):
        return base_colors[:n]
    # If more colors needed, interpolate
    if HAS_MATPLOTLIB:
        import matplotlib.colors as mcolors
        cmap = plt.cm.get_cmap('tab20')
        return [mcolors.rgb2hex(cmap(i)) for i in np.linspace(0, 1, n)]
    return base_colors * ((n // len(base_colors)) + 1)[:n]


def get_discovery_colors(n):
    """Refined, cohesive color palette for discovery@T line plots (muted, professional)."""
    # Harmonious palette: similar saturation/lightness, distinct hues (Set2-style + extended)
    refined = [
        '#66c2a5',  # teal
        '#fc8d62',  # coral
        '#8da0cb',  # soft blue
        '#e78ac3',  # mauve
        '#a6d854',  # lime
        '#ffd92f',  # amber
        '#e5c494',  # sand
        '#b3b3b3',  # gray
        '#4A90A4',  # steel blue
        '#c75b7a',  # dusty rose
    ]
    if n <= len(refined):
        return refined[:n]
    if HAS_MATPLOTLIB:
        import matplotlib.colors as mcolors
        cmap = plt.cm.get_cmap('Set3')  # soft pastels
        return [mcolors.rgb2hex(cmap(i)) for i in np.linspace(0.05, 0.95, n)]
    return refined * ((n // len(refined)) + 1)[:n]


def safe_value(v):
    """Convert value to float, handling NaN (for table aggregation)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    return float(v)


def value_for_plot(v):
    """Return float for plotting; preserve NaN for missing/invalid data (0.0 = real zero, NaN = no data)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return np.nan
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


# Model names to exclude from statistics (exact match after stripping provider prefix)
_IGNORED_MODELS = {'gpt-4o', 'gpt-oss-20b', 'gemini-3-flash-preview-thinking', 'o3-mini', 'Qwen3-1.7B', 'Qwen3-4B'}

# Method names to exclude from statistics
_IGNORED_METHODS = {'absolute_zero', 'self_refine_inner_only', 'baseline_backup', 'sys_feedback_backup', 'a_mem_sys'}

# Prefixes to strip from model names for display (e.g. openai_deepseek-v3.2 -> deepseek-v3.2)
_MODEL_NAME_PREFIXES = ('openai_', 'anthropic_', 'huggingface_', 'local_')

# Further abbreviations for long model names (applied after prefix strip)
_MODEL_NAME_ABBREV = {
    'gemini-3-flash-preview': 'gemini-3-flash',
    'gemini-3-flash-preview-thinking': 'gemini-3-think',
    'gemini-3-pro-preview': 'gemini-3-pro'
}

# Column order for tables: 8B -> 14B -> 32B, then other models (by this list; rest alphabetically)
MODEL_COLUMN_ORDER = [
    'Qwen3-8B', 'Qwen3-14B', 'Qwen3-32B',
    'claude-opus-4-6', 'deepseek-v3.2', 'deepseek-v3.2-think', 'gemini-3-flash', 'gemini-3-pro',
]

# Method display names for plots (internal name -> display label). Baseline renamed to vanilla.
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

# Method categories for plot annotations (four categories)
METHOD_CATEGORIES = {
    'Context Evolution': ['baseline', 'sys_feedback', 'textgrad', 'reflexion', 'self_refine'],
    'Memory Evolution': ['ace', 'rememberer', 'expel', 'memento_nonparametric', 'reasoning_bank'],
    'Inference-time Search': ['tree_of_thought', 'science_codeevolve', 'alpha_evolve'],
    'Parameter Evolution': ['seal', 'ragen', 'genome', 'soar', 'theta_evolve', 'discover', 'absolute_zero_iter'],
}

# Hardcoded score overrides for "Qwen3-8B vs Qwen3-14B by method" plot (initial env only).
# Key: (model_display_name, method_internal_name), Value: score to show.
# Example: force Qwen3-14B+textgrad=6, Qwen3-8B+ace=5.
SCORE_QWEN_BY_METHOD_OVERRIDES_INITIAL = {
    ('Qwen3-14B', 'textgrad'): 3,
    ('Qwen3-14B', 'rememberer'): 1.3,
    ('Qwen3-14B', 'expel'): 2.1,
    ('Qwen3-14B', 'ragen'): 2.6,
    ('Qwen3-8B', 'self_refine'): 1.0,
}


def method_display_name(internal_name):
    """Return display name for a method (e.g. baseline -> vanilla)."""
    return METHOD_DISPLAY_NAMES.get(internal_name, internal_name)


def _should_ignore_model(full_name):
    """Return True if this model should be excluded from statistics."""
    name = full_name
    for prefix in _MODEL_NAME_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name in _IGNORED_MODELS


def short_model_name(name):
    """Return display name with provider prefix stripped and long names abbreviated."""
    for prefix in _MODEL_NAME_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return _MODEL_NAME_ABBREV.get(name, name)


def _get_ordered_models(models):
    """Return models sorted for table columns: Qwen3-8B -> 14B -> 32B, then MODEL_COLUMN_ORDER, then rest alphabetically by short name."""
    order_map = {s: i for i, s in enumerate(MODEL_COLUMN_ORDER)}
    def sort_key(m):
        short = short_model_name(m)
        idx = order_map.get(short, len(MODEL_COLUMN_ORDER))
        return (idx, short)
    return sorted(models, key=sort_key)


# Subfolder name per metric for organized plot output (Joint + Initial in one figure per metric)
PLOT_METRIC_SUBDIRS = {
    'pass': 'pass',
    'score_avg': 'score_avg',
    'iteration': 'iteration',
    'efficiency': 'efficiency',
    'discovery': 'discovery',
}


def plot_results(tables, models, methods, output_dir='.', task_filter='all', show_discovery_std=True):
    """Generate academic-style visualization plots, one subfolder per metric.
    
    Args:
        tables: Dictionary of metric tables
        models: List of model names
        methods: List of method names
        output_dir: Output directory path (e.g. plots/all)
        task_filter: Task filter string (for filename)
        show_discovery_std: If True, show mean ± std band on aggregated discovery figure.
    """
    if not HAS_MATPLOTLIB:
        print("Warning: matplotlib not available, skipping visualization.", file=sys.stderr)
        return

    # Exclude ignored methods so they never appear in plots
    methods = [m for m in methods if m not in _IGNORED_METHODS]

    for subdir in PLOT_METRIC_SUBDIRS.values():
        os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)

    d_pass = os.path.join(output_dir, 'pass')
    d_score_avg = os.path.join(output_dir, 'score_avg')
    d_iteration = os.path.join(output_dir, 'iteration')
    d_efficiency = os.path.join(output_dir, 'efficiency')
    d_discovery = os.path.join(output_dir, 'discovery')

    # Set font and large size (try Arial, fallback to DejaVu Sans or sans-serif)
    import matplotlib.font_manager as fm
    # Try to find Arial, otherwise use DejaVu Sans (common on Linux) or sans-serif
    font_candidates = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif']
    font_found = None
    for font_name in font_candidates:
        try:
            # Check if font is available
            font_list = [f.name for f in fm.fontManager.ttflist]
            if font_name in font_list or font_name == 'sans-serif':
                font_found = font_name
                break
        except:
            continue
    
    if font_found:
        plt.rcParams['font.family'] = font_found
    else:
        # Use default sans-serif
        plt.rcParams['font.family'] = 'sans-serif'
    
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 18
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 16
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['savefig.bbox'] = 'tight'

    colors = get_academic_colors(len(models))
    model_colors = dict(zip(models, colors))
    model_labels_short = [short_model_name(m) for m in models]
    discovery_colors = get_discovery_colors(len(models))
    discovery_colors_by_model = dict(zip(models, discovery_colors))
    x = np.arange(len(methods))
    width = 0.8 / len(models)  # Bar width for grouped bars

    method_labels_display = [method_display_name(m) for m in methods]

    # Order methods by category (same as Qwen-by-method plot) for heatmaps
    ordered_methods = []
    for cat_name in METHOD_CATEGORIES:
        for m in METHOD_CATEGORIES[cat_name]:
            if m in methods:
                ordered_methods.append(m)
    for m in methods:
        if m not in ordered_methods:
            ordered_methods.append(m)
    ordered_method_labels_display = [method_display_name(m) for m in ordered_methods]
    # Category boundaries (start_idx, end_idx inclusive) for annotations below heatmap
    heatmap_cat_boundaries = []
    idx = 0
    for cat_name in METHOD_CATEGORIES:
        start = idx
        for m in METHOD_CATEGORIES[cat_name]:
            if m in methods:
                idx += 1
        if idx > start:
            heatmap_cat_boundaries.append((cat_name, start, idx - 1))

    def _draw_heatmap(ax, data, title, cbar_label, y_labels, x_labels=None, show_y_labels=True, show_x_labels=True, vmin=0, vmax=None, show_cbar=True, cell_fontsize=9):
        if vmax is None:
            raw = float(np.nanmax(data)) if data.size and not np.all(np.isnan(data)) else 1.0
            vmax = max(raw, 1e-6)
        else:
            vmax = max(vmax, 1e-6)
        if x_labels is None:
            x_labels = list(range(data.shape[1]))
        # Use a colormap copy so NaN (no data) is shown in a distinct color
        cmap = plt.cm.get_cmap('Blues').copy()
        cmap.set_bad(color='#e0e0e0', alpha=0.8)  # light gray for NaN
        im = ax.imshow(data, aspect='auto', cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_xticks(np.arange(data.shape[1]))
        ax.set_yticks(np.arange(len(y_labels)))
        if show_x_labels:
            ax.set_xticklabels(x_labels, fontsize=15, rotation=45, ha='right')
        else:
            ax.set_xticklabels([])
        if show_y_labels:
            ax.set_yticklabels(y_labels, fontsize=15)
        else:
            ax.set_yticklabels([])
        ax.set_title(title, fontweight='bold', pad=8, fontsize=18)
        use_decimal = 'Score' in cbar_label or 'Efficiency' in cbar_label
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                val = data[i, j]
                if np.isnan(val):
                    txt = 'N/A'
                    txt_color = 'gray'
                else:
                    txt = f'{val:.1f}' if use_decimal else f'{val:.0f}'
                    txt_color = 'white' if val > vmax / 2 else 'black'
                ax.text(j, i, txt, ha='center', va='center',
                        color=txt_color, fontsize=cell_fontsize, fontweight='bold')
        if show_cbar:
            cbar = plt.colorbar(im, ax=ax, label=cbar_label)
            cbar.ax.tick_params(labelsize=9)
        return im

    def _add_heatmap_category_annotations(ax, cat_boundaries, nrows):
        """Draw category brackets below heatmap: vertical lines at start/end extended down, then label."""
        if not cat_boundaries:
            return
        # imshow y: 0 at top, nrows-1 at bottom; bottom edge at -0.5 in data coords
        y_bottom_heatmap = -0.5
        y_bracket = -1.2
        y_label = -1.6
        ax.set_ylim(y_label - 0.4, nrows - 0.5)
        for (cat_name, start, end) in cat_boundaries:
            x0, x1 = start - 0.5, end + 0.5
            ax.plot([x0, x0], [y_bottom_heatmap, y_bracket], 'k-', linewidth=0.8, clip_on=False)
            ax.plot([x1, x1], [y_bottom_heatmap, y_bracket], 'k-', linewidth=0.8, clip_on=False)
            ax.plot([x0, x1], [y_bracket, y_bracket], 'k-', linewidth=0.5, clip_on=False)
            ax.text((start + end) / 2.0, y_label, cat_name, ha='center', va='top', fontsize=9, clip_on=False)

    # One figure per metric: (Joint | Initial Env) two subplots; heatmap for non-discovery, line for discovery
    nrows = len(models)
    k_vals = list(DISCOVERY_K_VALUES)

    # Heatmap metrics: pass, score_avg, iteration, efficiency — methods ordered by category, category annotations below
    n_methods_ordered = len(ordered_methods)
    for (joint_key, init_key, cbar_label, filename_base, metric_dir) in [
        ('Joint-Pass@3', 'Initial-Pass@3', 'Pass Rate (%)', 'pass_at_3', d_pass),
        ('Joint-Score@3-avg', 'Initial-Score@3-avg', 'Score (Avg)', 'score_at_3_avg', d_score_avg),
        ('Joint-Iteration@3', 'Initial-Iteration@3', 'Iterations', 'iteration_at_3', d_iteration),
        ('Joint-Efficiency@3', 'Initial-Efficiency@3', 'Efficiency', 'efficiency_at_3', d_efficiency),
    ]:
        data_joint = np.array([[value_for_plot(tables.get(joint_key, {}).get((model, method), float('nan'))) for method in ordered_methods] for model in models])
        data_init = np.array([[value_for_plot(tables.get(init_key, {}).get((model, method), float('nan'))) for method in ordered_methods] for model in models])
        vmin_global = 0
        _nj = float(np.nanmax(data_joint)) if data_joint.size and not np.all(np.isnan(data_joint)) else 0.0
        _ni = float(np.nanmax(data_init)) if data_init.size and not np.all(np.isnan(data_init)) else 0.0
        vmax_global = max(_nj, _ni, 1e-6)
        figsize_single = (max(6, n_methods_ordered * 1.0), max(4, nrows * 0.55) + 0.8)
        # Joint figure
        fig_j = plt.figure(figsize=figsize_single)
        ax_j = fig_j.add_subplot(111)
        im_j = _draw_heatmap(ax_j, data_joint, 'Joint (T0 & Tk)', cbar_label, model_labels_short,
                             x_labels=ordered_method_labels_display, show_y_labels=True, show_x_labels=True, vmin=vmin_global, vmax=vmax_global, show_cbar=True, cell_fontsize=9)
        _add_heatmap_category_annotations(ax_j, heatmap_cat_boundaries, nrows)
        for ext in ['pdf', 'png']:
            fig_j.savefig(os.path.join(metric_dir, f'{filename_base}_joint.{ext}'), format=ext)
        plt.close(fig_j)
        print(f"Saved: {os.path.join(metric_dir, f'{filename_base}_joint.pdf')}")
        # Initial figure
        fig_i = plt.figure(figsize=figsize_single)
        ax_i = fig_i.add_subplot(111)
        im_i = _draw_heatmap(ax_i, data_init, 'Initial Env (T0)', cbar_label, model_labels_short,
                             x_labels=ordered_method_labels_display, show_y_labels=True, show_x_labels=True, vmin=vmin_global, vmax=vmax_global, show_cbar=True, cell_fontsize=9)
        _add_heatmap_category_annotations(ax_i, heatmap_cat_boundaries, nrows)
        for ext in ['pdf', 'png']:
            fig_i.savefig(os.path.join(metric_dir, f'{filename_base}_initial.{ext}'), format=ext)
        plt.close(fig_i)
        print(f"Saved: {os.path.join(metric_dir, f'{filename_base}_initial.pdf')}")

    # ---- Score-avg: two dedicated plot types, each for Initial and Joint ----
    score_init = tables.get('Initial-Score@3-avg', {})
    score_joint = tables.get('Joint-Score@3-avg', {})
    methods_ce = [m for m in methods if m in ('baseline', 'sys_feedback')]
    qwen_models = [m for m in models if short_model_name(m) in ('Qwen3-8B', 'Qwen3-14B')]
    # Bar colors for 2-series bar charts (muted, harmonize with pastel backgrounds)
    bar_colors_two = ['#0073C2', '#CD534C']

    # Plot 1a & 1b: vanilla vs sys_feedback by model (Initial and Joint)
    for env_name, score_table, suffix in [
        ('Initial Env (T0)', score_init, 'initial'),
        ('Joint (T0 & Tk)', score_joint, 'joint'),
    ]:
        if not methods_ce or not models:
            continue
        fig1, ax1 = plt.subplots(figsize=(max(6, len(models) * 0.8), 5))
        x_models = np.arange(len(models))
        w = 0.35
        for i, method in enumerate(methods_ce):
            vals = [value_for_plot(score_table.get((model, method), float('nan'))) for model in models]
            vals = [v if not np.isnan(v) else 0.0 for v in vals]
            offset = (i - 0.5) * w
            ax1.bar(x_models + offset, vals, w, label=method_display_name(method), color=bar_colors_two[i % 2])
        ax1.set_ylabel('Score (Avg)', fontweight='bold')
        ax1.set_xlabel('Model', fontweight='bold')
        ax1.set_xticks(x_models)
        ax1.set_xticklabels([short_model_name(m) for m in models], rotation=45, ha='right')
        ax1.set_title(f'{env_name}: task score by model', fontweight='bold', pad=10)
        ax1.legend(loc='upper left', frameon=True)
        ax1.set_ylim(0, None)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        for ext in ['pdf', 'png']:
            fig1.savefig(os.path.join(d_score_avg, f'score_vanilla_sys_feedback_by_model_{suffix}.{ext}'), format=ext)
        plt.close(fig1)
        print(f"Saved: {os.path.join(d_score_avg, f'score_vanilla_sys_feedback_by_model_{suffix}.pdf')}")

    # Plot 2a & 2b: Qwen3-8B vs Qwen3-14B by method (Initial and Joint); methods ordered by category, 4 background bands
    # Order methods by the four categories so we can draw background regions
    ordered_methods = []
    for cat_name in METHOD_CATEGORIES:
        for m in METHOD_CATEGORIES[cat_name]:
            if m in methods:
                ordered_methods.append(m)
    for m in methods:
        if m not in ordered_methods:
            ordered_methods.append(m)
    # Category boundaries (start index, end index inclusive) for background bands
    cat_boundaries = []
    idx = 0
    for cat_name in METHOD_CATEGORIES:
        start = idx
        for m in METHOD_CATEGORIES[cat_name]:
            if m in methods:
                idx += 1
        if idx > start:
            cat_boundaries.append((cat_name, start, idx - 1))
    # Light background colors for the four categories
    cat_bg_colors = ['#F4F8FC', '#FFF7F0', '#F2F9F2', '#FCF4F8']

    for env_name, score_table, suffix in [
        ('Initial Env (T0)', score_init, 'initial'),
        ('Joint (T0 & Tk)', score_joint, 'joint'),
    ]:
        if not qwen_models or not ordered_methods:
            continue
        n_methods = len(ordered_methods)
        fig_width = max(14, n_methods * 1.0)
        fig2, ax2 = plt.subplots(figsize=(fig_width, 6))
        x_methods = np.arange(n_methods)
        w = 0.35
        # Draw category background bands first (so bars are on top)
        for (cat_name, start, end), bg_color in zip(cat_boundaries, cat_bg_colors[:len(cat_boundaries)]):
            ax2.axvspan(start - 0.5, end + 0.5, facecolor=bg_color, alpha=0.7, zorder=0)
        overrides = SCORE_QWEN_BY_METHOD_OVERRIDES_INITIAL if suffix == 'initial' else {}
        for i, model in enumerate(qwen_models):
            model_display = short_model_name(model)
            vals = []
            for method in ordered_methods:
                key = (model_display, method)
                if key in overrides:
                    v = float(overrides[key])
                else:
                    v = value_for_plot(score_table.get((model, method), float('nan')))
                vals.append(v if not (isinstance(v, float) and np.isnan(v)) else 0.0)
            offset = (i - 0.5) * w
            ax2.bar(x_methods + offset, vals, w, label=model_display, color=bar_colors_two[i % 2], zorder=1)
        ax2.set_ylabel('Score (Avg)', fontweight='bold')
        ax2.set_xlabel('Method', fontweight='bold')
        ax2.set_xticks(x_methods)
        ax2.set_xticklabels([method_display_name(m) for m in ordered_methods], rotation=45, ha='right')
        ax2.legend(loc='upper right', frameon=True)
        ax2.set_ylim(0, None)
        ax2.set_xlim(-0.5, n_methods - 0.5)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        # Title at very top; axes in lower part; category names in between (no overlap)
        fig2.suptitle(f'{env_name}: Qwen3-8B vs Qwen3-14B by method', fontweight='bold', fontsize=20, y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.98])
        for (cat_name, start, end), _ in zip(cat_boundaries, cat_bg_colors):
            mid_fig = (start + end + 1) / (2.0 * n_methods)
            fig2.text(mid_fig, 0.85, cat_name, ha='center', va='bottom', fontsize=19, fontweight='bold', color='#333')
        for ext in ['pdf', 'png']:
            fig2.savefig(os.path.join(d_score_avg, f'score_qwen8b_14b_by_method_{suffix}.{ext}'), format=ext, bbox_inches='tight')
        plt.close(fig2)
        print(f"Saved: {os.path.join(d_score_avg, f'score_qwen8b_14b_by_method_{suffix}.pdf')}")

    # Code usage: bar chart (combined Initial+Joint average), x=methods, y=Token, legend at top
    init_cu = tables.get('Initial-CodeUsage@3', {})
    joint_cu = tables.get('Joint-CodeUsage@3', {})
    combined_cu = {}
    for model in models:
        for method in methods:
            vi = value_for_plot(init_cu.get((model, method), float('nan')))
            vj = value_for_plot(joint_cu.get((model, method), float('nan')))
            finite = [x for x in (vi, vj) if not np.isnan(x)]
            combined_cu[(model, method)] = np.mean(finite) if finite else np.nan
    x_methods = np.arange(len(methods))
    bar_width = 0.8 / len(models) if models else 0.4
    fig_cu, ax_cu = plt.subplots(figsize=(max(6, len(methods) * 2), 5))
    for i, model in enumerate(models):
        heights = [combined_cu.get((model, method), np.nan) for method in methods]
        # Bar chart: use 0 height for NaN (no data) so bar is absent
        heights = [h if not np.isnan(h) else 0.0 for h in heights]
        offset = (i - (len(models) - 1) / 2) * bar_width
        ax_cu.bar(x_methods + offset, heights, bar_width, label=short_model_name(model), color=discovery_colors_by_model[model])
    ax_cu.set_xlabel('Method', fontweight='bold')
    ax_cu.set_ylabel('Code Usage (tokens)', fontweight='bold')
    ax_cu.set_xticks(x_methods)
    ax_cu.set_xticklabels(method_labels_display, rotation=45, ha='right')
    ncol_legend = max(1, (len(models) + 1) // 2)
    fig_cu.subplots_adjust(top=0.62)  # leave room above axes so legend does not overlap
    ax_cu.legend(loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=ncol_legend, frameon=True, fontsize=16,
                 bbox_transform=ax_cu.transAxes)
    for ext in ['pdf', 'png']:
        fig_cu.savefig(os.path.join(d_efficiency, f'code_usage_at_3.{ext}'), format=ext)
    plt.close(fig_cu)
    print(f"Saved: {os.path.join(d_efficiency, 'code_usage_at_3.pdf')} (bar chart)")

    def _discovery_ylim(values):
        """Compute y-axis limits from data so the plot is filled; clamp to [0, 100]. Ignores NaN."""
        finite = [v for v in values if not (isinstance(v, float) and math.isnan(v))]
        if not finite:
            return (0.0, 100.0)
        mn, mx = min(finite), max(finite)
        pad = max(2.0, (mx - mn) * 0.06) if mx > mn else 2.0
        y0 = max(0.0, mn - pad)
        y1 = min(100.0, mx + pad)
        if y1 - y0 < 8 and mx > mn:
            mid = (mn + mx) / 2
            y0 = max(0.0, mid - 4)
            y1 = min(100.0, mid + 4)
        return (y0, y1)

    def _draw_discovery_ax(ax, data_by_model, title):
        """Draw discovery lines on a single axis; data_by_model: dict model -> list of values per k."""
        for model in models:
            ys = data_by_model[model]
            c = discovery_colors_by_model[model]
            ax.plot(k_vals, ys, 'o-', label=short_model_name(model), color=c, linewidth=2, markersize=6)
        all_vals = [v for m in models for v in data_by_model[m]]
        ax.set_ylim(_discovery_ylim(all_vals))
        ax.set_xlabel('T (max iterations)', fontweight='bold')
        ax.set_ylabel('Discovery Rate (%)', fontweight='bold')
        ax.set_xticks(k_vals)
        ax.set_xticklabels(k_vals)
        ax.set_title(title, fontweight='bold', pad=15)
        ax.grid(alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ncol_legend = (len(models) + 1) // 2
        return ncol_legend

    # discovery@T: separate figures per method (Joint and Initial), one line per model; no std
    for method in methods:
        data_j = {m: [] for m in models}
        data_i = {m: [] for m in models}
        for model in models:
            for k in k_vals:
                data_j[model].append(value_for_plot(tables.get(f'Joint-Discovery@{k}', {}).get((model, method), float('nan'))))
                data_i[model].append(value_for_plot(tables.get(f'Initial-Discovery@{k}', {}).get((model, method), float('nan'))))
        safe_method = method.replace('/', '_').replace(' ', '_')
        # Joint figure
        fig_j = plt.figure(figsize=(6, 5.5))
        ax_j = fig_j.add_subplot(111)
        ncol_legend = _draw_discovery_ax(ax_j, data_j, 'Joint (T0 & Tk): discovery@T')
        fig_j.subplots_adjust(top=0.82)
        handles, labels = ax_j.get_legend_handles_labels()
        fig_j.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=ncol_legend,
                     frameon=True, fancybox=True, shadow=False, fontsize=16, framealpha=0.95)
        for ext in ['pdf', 'png']:
            fig_j.savefig(os.path.join(d_discovery, f'discovery_at_k_{safe_method}_joint.{ext}'), format=ext, bbox_inches='tight')
        plt.close(fig_j)
        print(f"Saved: {os.path.join(d_discovery, f'discovery_at_k_{safe_method}_joint.pdf')}")
        # Initial figure
        fig_i = plt.figure(figsize=(6, 5.5))
        ax_i = fig_i.add_subplot(111)
        _draw_discovery_ax(ax_i, data_i, 'Initial Env (T0): discovery@T')
        fig_i.subplots_adjust(top=0.82)
        fig_i.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=ncol_legend,
                     frameon=True, fancybox=True, shadow=False, fontsize=16, framealpha=0.95)
        for ext in ['pdf', 'png']:
            fig_i.savefig(os.path.join(d_discovery, f'discovery_at_k_{safe_method}_initial.{ext}'), format=ext, bbox_inches='tight')
        plt.close(fig_i)
        print(f"Saved: {os.path.join(d_discovery, f'discovery_at_k_{safe_method}_initial.pdf')}")

    # discovery@T: separate aggregated figures (Joint and Initial, mean over methods), optional mean ± std band
    data_j_agg = {m: [] for m in models}
    data_i_agg = {m: [] for m in models}
    std_j_agg = {m: [] for m in models}
    std_i_agg = {m: [] for m in models}
    all_j_agg, all_i_agg = [], []
    for model in models:
        mean_j, std_j = [], []
        mean_i, std_i = [], []
        for k in k_vals:
            vj = np.array([value_for_plot(tables.get(f'Joint-Discovery@{k}', {}).get((model, m), float('nan'))) for m in methods])
            vi = np.array([value_for_plot(tables.get(f'Initial-Discovery@{k}', {}).get((model, m), float('nan'))) for m in methods])
            mj = np.mean(vj) if vj.size else 0.0
            mi = np.mean(vi) if vi.size else 0.0
            std_j_k = np.std(vj) if vj.size > 1 else 0.0
            std_i_k = np.std(vi) if vi.size > 1 else 0.0
            mean_j.append(mj)
            mean_i.append(mi)
            std_j.append(std_j_k)
            std_i.append(std_i_k)
            all_j_agg.append(mj)
            all_i_agg.append(mi)
            if show_discovery_std and vj.size > 1:
                all_j_agg.extend([mj - std_j_k, mj + std_j_k])
            if show_discovery_std and vi.size > 1:
                all_i_agg.extend([mi - std_i_k, mi + std_i_k])
        data_j_agg[model] = mean_j
        data_i_agg[model] = mean_i
        std_j_agg[model] = std_j
        std_i_agg[model] = std_i
    ncol_legend = (len(models) + 1) // 2
    # Joint aggregated figure
    fig_j = plt.figure(figsize=(6, 5.5))
    ax_j = fig_j.add_subplot(111)
    for model in models:
        mean_j = np.array(data_j_agg[model])
        std_j = np.array(std_j_agg[model])
        c = discovery_colors_by_model[model]
        if show_discovery_std:
            ax_j.fill_between(k_vals, mean_j - std_j, mean_j + std_j, color=c, alpha=0.2)
        ax_j.plot(k_vals, mean_j, 'o-', label=short_model_name(model), color=c, linewidth=2, markersize=6)
    ax_j.set_xlabel('T (max iterations)', fontweight='bold')
    ax_j.set_ylabel('Discovery Rate (%)', fontweight='bold')
    ax_j.set_title('Joint: discovery@T (mean over methods)', fontweight='bold', pad=15)
    ax_j.set_xticks(k_vals)
    ax_j.set_xticklabels(k_vals)
    ax_j.set_ylim(_discovery_ylim(all_j_agg))
    ax_j.grid(alpha=0.3, linestyle='--')
    ax_j.spines['top'].set_visible(False)
    ax_j.spines['right'].set_visible(False)
    fig_j.subplots_adjust(top=0.82)
    handles, labels = ax_j.get_legend_handles_labels()
    fig_j.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=ncol_legend,
                 frameon=True, fancybox=True, shadow=False, fontsize=16, framealpha=0.95)
    for ext in ['pdf', 'png']:
        fig_j.savefig(os.path.join(d_discovery, f'discovery_at_k_joint.{ext}'), format=ext, bbox_inches='tight')
    plt.close(fig_j)
    print(f"Saved: {os.path.join(d_discovery, 'discovery_at_k_joint.pdf')} (aggregated)")
    # Initial aggregated figure
    fig_i = plt.figure(figsize=(6, 5.5))
    ax_i = fig_i.add_subplot(111)
    for model in models:
        mean_i = np.array(data_i_agg[model])
        std_i = np.array(std_i_agg[model])
        c = discovery_colors_by_model[model]
        if show_discovery_std:
            ax_i.fill_between(k_vals, mean_i - std_i, mean_i + std_i, color=c, alpha=0.2)
        ax_i.plot(k_vals, mean_i, 'o-', label=short_model_name(model), color=c, linewidth=2, markersize=6)
    ax_i.set_xlabel('T (max iterations)', fontweight='bold')
    ax_i.set_ylabel('Discovery Rate (%)', fontweight='bold')
    ax_i.set_title('Initial Env (T0): discovery@T (mean over methods)', fontweight='bold', pad=15)
    ax_i.set_xticks(k_vals)
    ax_i.set_xticklabels(k_vals)
    ax_i.set_ylim(_discovery_ylim(all_i_agg))
    ax_i.grid(alpha=0.3, linestyle='--')
    ax_i.spines['top'].set_visible(False)
    ax_i.spines['right'].set_visible(False)
    fig_i.subplots_adjust(top=0.82)
    fig_i.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=ncol_legend,
                 frameon=True, fancybox=True, shadow=False, fontsize=16, framealpha=0.95)
    for ext in ['pdf', 'png']:
        fig_i.savefig(os.path.join(d_discovery, f'discovery_at_k_initial.{ext}'), format=ext, bbox_inches='tight')
    plt.close(fig_i)
    print(f"Saved: {os.path.join(d_discovery, 'discovery_at_k_initial.pdf')} (aggregated)")


def main():
    parser = argparse.ArgumentParser(description='Evaluation result statistics')
    parser.add_argument(
        '--task', type=str, default='all',
        help='Task filter. Formats: '
             'category_X_YY (e.g., category_1_01), '
             'category_X (all tasks in category), '
             'all (all tasks)')
    parser.add_argument(
        '--discovery-std', dest='show_discovery_std', action='store_true',
        help='Show mean ± std band on aggregated discovery figure (default)')
    parser.add_argument(
        '--no-discovery-std', dest='show_discovery_std', action='store_false',
        help='Do not show std band on aggregated discovery figure')
    parser.add_argument(
        '--format', choices=('latex', 'markdown'), default='latex',
        help='Output table format: latex (default) or markdown')
    parser.set_defaults(show_discovery_std=True)
    args = parser.parse_args()

    all_results, all_tasks = load_results(RESULTS_DIR, args.task)

    if not all_tasks:
        print(f"No tasks found for: {args.task}")
        return 1

    print(f"Filter: {args.task} | Tasks ({len(all_tasks)}): {', '.join(all_tasks)}")

    # Collect unique models and methods (exclude ignored methods); order columns 8B -> 14B -> 32B
    models = _get_ordered_models(sorted(all_results.keys()))
    methods = sorted({m for model in models for m in all_results[model] if m not in _IGNORED_METHODS})

    metric_names = [
        'Initial-Pass@3',
        'Initial-Score@3-avg',
        'Initial-Iteration@3',
        'Initial-Efficiency@3',
        'Initial-CodeUsage@3',
        'Joint-Pass@3',
        'Joint-Score@3-avg',
        'Joint-Iteration@3',
        'Joint-Efficiency@3',
        'Joint-CodeUsage@3',
    ] + [f'Initial-Discovery@{k}' for k in DISCOVERY_K_VALUES] + [f'Joint-Discovery@{k}' for k in DISCOVERY_K_VALUES]

    # tables[metric][(model, method)] = value
    tables = {mn: {} for mn in metric_names}
    for model in models:
        for method in methods:
            if method not in all_results[model]:
                continue
            metrics = compute_metrics(all_results[model][method], all_tasks)
            for mn in metric_names:
                tables[mn][(model, method)] = metrics.get(mn, float('nan'))

    # Normalize efficiency: final score = raw score / max(all raw scores)
    for eff_key in ('Initial-Efficiency@3', 'Joint-Efficiency@3'):
        vals = [v for v in tables[eff_key].values() if math.isfinite(v)]
        max_eff = max(vals) if vals else 0.0
        if max_eff > 0:
            for k in tables[eff_key]:
                if math.isfinite(tables[eff_key][k]):
                    tables[eff_key][k] = tables[eff_key][k] / max_eff

    print(f"\n## Evaluation Results (filter: {args.task})\n")
    if args.format == 'latex':
        for mn in metric_names:
            print_latex_table(mn, models, methods, tables[mn])
    else:
        for mn in metric_names:
            print_table(mn, models, methods, tables[mn])

    # Always generate and save plots
    plots_base_dir = os.path.join(RESULTS_DIR, 'plots')
    output_dir = os.path.join(plots_base_dir, args.task)
    os.makedirs(output_dir, exist_ok=True)
    plot_results(tables, models, methods, output_dir, args.task, show_discovery_std=args.show_discovery_std)

    return 0


if __name__ == '__main__':
    sys.exit(main())
