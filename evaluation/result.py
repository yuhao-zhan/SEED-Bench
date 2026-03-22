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

# Okabe–Ito–style accents (colorblind-friendly) for bars/lines
_ACCENT_A = '#0072B2'  # blue
_ACCENT_B = '#D55E00'  # vermillion
_ACCENT_GRID = '#B0B0B0'
_ACCENT_TEXT = '#2C2C2C'
_BASELINE_LINE = '#444444'


def _configure_matplotlib_academic():
    """Plot defaults: Arial (with fallbacks), large type, high-res save."""
    if not HAS_MATPLOTLIB:
        return
    plt.rcParams.update({
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.12,
        'font.family': 'sans-serif',
        'font.sans-serif': [
            'Arial', 'Helvetica', 'Liberation Sans', 'Nimbus Sans', 'DejaVu Sans',
            'sans-serif',
        ],
        'mathtext.fontset': 'dejavusans',
        'font.size': 20,
        'axes.labelsize': 20,
        'axes.titlesize': 20,
        'axes.titleweight': 'normal',
        'axes.labelweight': 'normal',
        'axes.linewidth': 0.9,
        'axes.edgecolor': _ACCENT_TEXT,
        'axes.labelcolor': _ACCENT_TEXT,
        'axes.titlepad': 8,
        'xtick.labelsize': 18,
        'ytick.labelsize': 18,
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,
        'legend.frameon': True,
        'legend.framealpha': 0.95,
        'legend.edgecolor': '#CCCCCC',
        'legend.fontsize': 18,
        'grid.color': _ACCENT_GRID,
        'grid.linestyle': '-',
        'grid.linewidth': 0.5,
        'grid.alpha': 0.55,
    })


def _style_axes_minimal_spines(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(_ACCENT_TEXT)
    ax.spines['bottom'].set_color(_ACCENT_TEXT)


# (left, bottom, right, top): axes live inside this box → margins outside (esp. top breathing room).
_FIG_RECT_DEFAULT = (0.07, 0.10, 0.96, 0.88)
# Qwen bars: room below for tilted x-labels; top matches fig.legend anchor (tight gap, no huge void).
_QWEN_AXES_TOP_FIG = 0.95
_FIG_RECT_QWEN = (0.08, 0.16, 0.96, _QWEN_AXES_TOP_FIG)

# Base methods for which we omit the +CE bar in qwen_score_comparison (e.g. incomplete / unwanted CE runs).
#   _QWEN_SKIP_CE_METHODS = frozenset({'tree_of_thought'})
_QWEN_SKIP_CE_METHODS = frozenset()

# discovery_rate_agg: distinct line colors (user palette; #3480o8 → #3480b8).
_DISCOVERY_LINE_PALETTE = (
    '#f79059', '#c2bdde', '#8dcec8', '#add3e2',
    '#3480b8', '#ffbe7a', '#fa8878', '#c82423',
)


def _tight_layout_margins(fig, rect=_FIG_RECT_DEFAULT):
    fig.tight_layout(rect=rect)


def _score_agg_success_within_budget(results, model, method, all_file_ids, k):
    """Score@k for one model/method on all files (unqualified samples contribute 0)."""
    if method not in results.get(model, {}):
        return None
    n_total = len(all_file_ids)
    if n_total == 0:
        return 0.0
    s = 0.0
    for fid in all_file_ids:
        data = results[model][method].get(fid)
        if not data:
            # Missing result for this file contributes 0 to match discovery-style denominator.
            continue
        it = data.get('iterations', _MAX_DISCOVERY_K + 1)
        if data.get('success') and it <= k:
            s += float(data.get('best_score', 0.0))
    return s / n_total


def _y_lists_score_vs_iteration(results, models, methods, all_file_ids, k_vals):
    """Per model: y[k] = mean over available methods of method-wise Score@k."""
    y_lists = []
    for model in models:
        y = []
        for k in k_vals:
            method_avgs = []
            for m in methods:
                v = _score_agg_success_within_budget(results, model, m, all_file_ids, k)
                if v is not None:
                    method_avgs.append(v)
            y.append(sum(method_avgs) / len(method_avgs) if method_avgs else 0.0)
        y_lists.append(y)
    return y_lists


def _plot_iteration_budget_lines(
    models, k_vals, y_lists, ylabel, output_path, ymax_cap=None,
):
    """Shared layout for discovery_rate_agg and score_vs_iteration (no title)."""
    if not HAS_MATPLOTLIB or not models:
        return
    _xt = list(range(1, _MAX_DISCOVERY_K + 1, 2))
    if _MAX_DISCOVERY_K not in _xt:
        _xt.append(_MAX_DISCOVERY_K)
    fig, ax = plt.subplots(figsize=(10.0, 8.0), facecolor='white')
    ax.set_facecolor('white')
    for mi, model in enumerate(models):
        c = _DISCOVERY_LINE_PALETTE[mi % len(_DISCOVERY_LINE_PALETTE)]
        y = y_lists[mi]
        ax.plot(
            k_vals, y,
            'o-',
            label=short_model_name(model),
            linewidth=2.8,
            markersize=3.4,
            color=c,
            markerfacecolor=c,
            markeredgecolor='none',
            markeredgewidth=0,
            zorder=3,
        )
    ax.set_xlabel('Max iterations (T)')
    ax.set_ylabel(ylabel, labelpad=14)
    ax.set_xticks(_xt)
    ax.set_xlim(0.5, _MAX_DISCOVERY_K + 0.5)
    _style_axes_minimal_spines(ax)
    ax.grid(True, axis='y', linestyle='-', linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)
    finite = [v for row in y_lists for v in row if not math.isnan(v)]
    if finite:
        ymax = max(finite) * 1.08
        if ymax_cap is not None:
            ymax = min(float(ymax_cap), ymax)
        ax.set_ylim(0, ymax + 1e-6)
    leg_handles, leg_labels = ax.get_legend_handles_labels()
    nleg = len(leg_handles)
    if not leg_handles:
        axes_top_fig = 0.90
        ncol_disc = 1
    else:
        ncol_disc = nleg if nleg <= 3 else 3
        n_leg_rows = math.ceil(nleg / ncol_disc)
        row_frac = 0.048
        axes_top_fig = max(0.72, 0.94 - row_frac * n_leg_rows)
    _tight_layout_margins(fig, (0.14, 0.12, 0.96, axes_top_fig))
    if leg_handles:
        fig.legend(
            leg_handles, leg_labels,
            loc='lower center',
            bbox_to_anchor=(0.5, axes_top_fig),
            bbox_transform=fig.transFigure,
            ncol=ncol_disc,
            columnspacing=1.2,
            handletextpad=0.45,
            handlelength=2.0,
            frameon=True,
        )
    fig.savefig(
        output_path,
        facecolor='white',
        bbox_inches='tight',
        pad_inches=0.14,
    )
    plt.close(fig)


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from evaluation.utils import get_evaluation_results_dir, get_evaluation_results_scratch_dir

RESULTS_DIR = get_evaluation_results_dir()
SCRATCH_DIR = get_evaluation_results_scratch_dir()

# discovery@T: k = 1.._MAX_DISCOVERY_K (inclusive); used in metrics + discovery_rate_agg plot.
_MAX_DISCOVERY_K = 20
DISCOVERY_K_VALUES = tuple(range(1, _MAX_DISCOVERY_K + 1))

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
            
            # Only T0=Initial → mutated env: all_Initial_to_Stage-1.json (ignore Stage-3_to_Stage-2, etc.)
            if not fn.startswith('all_Initial_to_'):
                continue
            if '_pseudo' in fn or fn.count('_to_') != 1:
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


def load_results_scratch(results_dir, task_filter='all'):
    """Load results from evaluation_results_scratch (single-env JSONs: all_Initial.json, all_Stage-1.json, etc.)."""
    results = defaultdict(lambda: defaultdict(dict))
    all_file_ids = set()

    for root, dirs, files in os.walk(results_dir):
        path_parts = root.split(os.sep)
        if len(path_parts) < 2:
            continue

        method = path_parts[-1]
        model = path_parts[-2]

        if method in _IGNORED_METHODS or _should_ignore_model(model):
            continue

        task_match = False
        if task_filter == 'all':
            task_match = True
        else:
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
            if not fn.endswith('.json') or not fn.startswith('all_') or '_pseudo' in fn:
                continue
            # Scratch: only single-env files (exclude pair files all_*_to_*.json)
            if re.match(r'^all_.+_to_.+.*\.json$', fn):
                continue

            file_path = os.path.join(root, fn)
            try:
                task_name = path_parts[-3]
                file_id = f"{task_name}/{fn}"
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results[model][method][file_id] = data
                all_file_ids.add(file_id)
            except Exception:
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

    _MAX_ITER = _MAX_DISCOVERY_K

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
    'gemini-3-pro-preview': 'gemini-3-pro',
    'gemini-3.1-flash-lite-preview': 'gemini-3.1-flash',
}
_IGNORED_MODELS = {'gpt-4o', 'gpt-oss-20b', 'gemini-3-flash-preview-thinking', 'o3-mini', 'Qwen3-1.7B', 'Qwen3-4B'}
_IGNORED_METHODS = {
    'self_refine_inner_only', 'baseline_backup', 'sys_feedback_backup', 'a_mem_sys',
    'sys_feedback', 'sys_feedback_CE',
    'memento_nonparametric', 'memento_nonparametric_CE',
}

MODEL_COLUMN_ORDER = [
    'Qwen3-8B', 'Qwen3-14B', 'Qwen3-32B',
    'claude-opus-4-6', 'deepseek-v3.2', 'deepseek-v3.2-think', 'gemini-3-flash', 'gemini-3-pro',
]

METHOD_DISPLAY_NAMES = {
    'baseline': 'vanilla',
    'baseline_CE': 'vanilla_CE',
    'textgrad': 'textgrad',
    'reflexion': 'reflexion',
    'self_refine': 'self_refine',
    'ace': 'ace',
    'rememberer': 'rememberer',
    'expel': 'expel',
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
    'Context Evolution': ['baseline', 'textgrad', 'reflexion', 'self_refine'],
    'Memory Evolution': ['ace', 'rememberer', 'expel', 'reasoning_bank'],
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


def _base_methods_for_ce_grouping(ordered_methods):
    """Ordered list of methods that are not *_CE (for paired base vs CE bars)."""
    bases = []
    seen = set()
    for m in ordered_methods:
        if m.endswith('_CE'):
            continue
        if m not in seen:
            bases.append(m)
            seen.add(m)
    return bases


def plot_results(
    tables, models, methods, output_dir, score_by_model_method='baseline',
    results=None, all_file_ids=None,
):
    if not HAS_MATPLOTLIB: return
    
    os.makedirs(output_dir, exist_ok=True)
    _configure_matplotlib_academic()
    method_set = set(methods)
    
    ordered_methods = _get_ordered_methods(methods)
    method_labels = [method_display_name(m) for m in ordered_methods]
    model_labels = [short_model_name(m) for m in models]
    
    # --- 1. Primary Metrics Heatmaps ---
    for metric, label, filename in [
        ('Pass@1', 'Pass Rate (%)', 'pass_rate_heatmap'),
        ('Score-Avg', 'Average Score', 'score_avg_heatmap'),
        ('Iteration-Avg', 'Avg Iterations', 'iteration_avg_heatmap'),
        ('Efficiency-Avg', 'Efficiency (score / token)', 'efficiency_avg_heatmap'),
        ('CodeUsage-Avg', 'Code usage (tokens)', 'code_usage_avg_heatmap'),
    ]:
        if not tables.get(metric) or not ordered_methods or not models:
            continue
            
        fig, ax = plt.subplots(
            figsize=(len(ordered_methods) * 1.05 + 3.0, len(models) * 0.85 + 2.8),
            facecolor='white',
        )
        ax.set_facecolor('#FAFAFA')
        data = []
        for model in models:
            row = []
            for method in ordered_methods:
                v = tables[metric].get((model, method), float('nan'))
                row.append(v)
            data.append(row)
        
        v_min = 0
        v_max = 100 if 'Pass' in metric else None
        if v_max is None:
            finite_vals = [v for row in data for v in row if not math.isnan(v)]
            v_max = max(finite_vals) if finite_vals else 1.0
            
        masked_data = [[(v if not math.isnan(v) else 0) for v in row] for row in data]
        
        im = ax.imshow(
            masked_data,
            cmap='Blues',
            vmin=v_min,
            vmax=v_max,
            aspect='auto',
            interpolation='nearest',
        )
        ax.set_xticks(range(len(ordered_methods)))
        ax.set_yticks(range(len(models)))
        ax.set_xticklabels(method_labels, rotation=40, ha='right')
        ax.set_yticklabels(model_labels)
        for s in ax.spines.values():
            s.set_linewidth(0.9)
            s.set_edgecolor(_ACCENT_TEXT)
        ax.tick_params(axis='both', length=4, width=0.8)
        ax.set_xlabel('Method')
        ax.set_ylabel('Model')
        
        # Light cell boundaries (readable grid)
        for i in range(len(models) + 1):
            ax.axhline(i - 0.5, color='white', linewidth=0.9, zorder=5)
        for j in range(len(ordered_methods) + 1):
            ax.axvline(j - 0.5, color='white', linewidth=0.9, zorder=5)
        
        for i in range(len(models)):
            for j in range(len(ordered_methods)):
                val = data[i][j]
                if not math.isnan(val):
                    txt = f'{val:.1f}' if 'Efficiency' in metric or 'Score' in metric else f'{val:.0f}'
                    tc = 'white' if val > v_min + 0.55 * (v_max - v_min) else _ACCENT_TEXT
                    ax.text(j, i, txt, ha='center', va='center', color=tc, fontsize=17)
        
        cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.02, aspect=22)
        cbar.ax.tick_params(labelsize=18, width=0.7, length=3)
        cbar.set_label(label, fontsize=18)
        _tight_layout_margins(fig, _FIG_RECT_DEFAULT)
        fig.savefig(os.path.join(output_dir, f'{filename}.png'), facecolor='white')
        plt.close(fig)

    # --- 2. Qwen Model Comparison (grouped: each method vs its *_CE variant) ---
    qwen_models = [m for m in models if short_model_name(m) in ('Qwen3-8B',)]
    method_bases = _base_methods_for_ce_grouping(ordered_methods)
    if qwen_models and method_bases:
        model = qwen_models[0]
        n = len(method_bases)
        fig, ax = plt.subplots(figsize=(max(12.5, n * 0.92), 6.5), facecolor='white')
        ax.set_facecolor('white')
        x = list(range(n))
        width = 0.34
        vals_base = []
        vals_ce = []
        for m in method_bases:
            vb = tables['Score-Avg'].get((model, m), float('nan'))
            vals_base.append(vb if not math.isnan(vb) else 0.0)
            m_ce = f'{m}_CE'
            if m_ce in method_set:
                vc = tables['Score-Avg'].get((model, m_ce), float('nan'))
                vals_ce.append(vc if not math.isnan(vc) else 0.0)
            else:
                vals_ce.append(0.0)
        xb = [i - width / 2 for i in x]
        xc = [i + width / 2 for i in x]
        h_wo = h_ce = None
        ce_heights_for_ylim = []
        for i, m in enumerate(method_bases):
            lb = 'w/o CE' if h_wo is None else '_nolegend_'
            b0 = ax.bar(
                xb[i], vals_base[i], width,
                label=lb, color=_ACCENT_A, edgecolor='#003D5C', linewidth=0.45, zorder=2,
            )
            if h_wo is None:
                h_wo = b0[0]
            if m in _QWEN_SKIP_CE_METHODS:
                continue
            m_ce = f'{m}_CE'
            if m_ce not in method_set:
                continue
            lc = '+ CE' if h_ce is None else '_nolegend_'
            b1 = ax.bar(
                xc[i], vals_ce[i], width,
                label=lc, color=_ACCENT_B, edgecolor='#6B2F00', linewidth=0.45, zorder=2,
            )
            if h_ce is None:
                h_ce = b1[0]
            ce_heights_for_ylim.append(vals_ce[i])
        vanilla_y = tables['Score-Avg'].get((model, 'baseline'), float('nan'))
        h_line = None
        if not math.isnan(vanilla_y):
            h_line = ax.axhline(
                vanilla_y,
                linestyle=':',
                color=_BASELINE_LINE,
                linewidth=1.25,
                zorder=1,
            )
        ax.set_ylabel('Average score')
        # ax.set_xlabel('Method')
        ax.set_xticks(x)
        ax.set_xticklabels([method_display_name(m) for m in method_bases], rotation=38, ha='right')
        _style_axes_minimal_spines(ax)
        ax.yaxis.grid(True, linestyle='-', linewidth=0.5, alpha=0.85)
        ax.set_axisbelow(True)
        y_candidates = list(vals_base) + ce_heights_for_ylim
        if not math.isnan(vanilla_y):
            y_candidates.append(vanilla_y)
        ymax = max(y_candidates) if y_candidates else 1.0
        ax.set_ylim(0, ymax * 1.12 if ymax > 0 else 1.0)
        _tight_layout_margins(fig, _FIG_RECT_QWEN)
        leg_handles = []
        leg_labels = []
        if h_wo is not None:
            leg_handles.append(h_wo)
            leg_labels.append('w/o CE')
        if h_ce is not None:
            leg_handles.append(h_ce)
            leg_labels.append('+ CE')
        if h_line is not None:
            leg_handles.append(h_line)
            leg_labels.append('Vanilla baseline')
        if leg_handles:
            # Legend sits immediately above axes (lower edge = axes top) — avoids a tall empty band.
            fig.legend(
                leg_handles, leg_labels,
                loc='lower center',
                bbox_to_anchor=(0.5, _QWEN_AXES_TOP_FIG),
                bbox_transform=fig.transFigure,
                ncol=len(leg_handles),
                handlelength=2.2,
                columnspacing=1.4,
                handletextpad=0.55,
                frameon=True,
            )
        fig.savefig(
            os.path.join(output_dir, 'qwen_score_comparison.png'),
            facecolor='white',
            bbox_inches='tight',
            pad_inches=0.14,
        )
        plt.close(fig)

    # --- 2b. Score by model for a fixed method (default: baseline / vanilla) ---
    if models and score_by_model_method in method_set:
        fig, ax = plt.subplots(figsize=(max(9.0, len(models) * 0.72), 6.0), facecolor='white')
        ax.set_facecolor('white')
        x = list(range(len(models)))
        vals = []
        for model in models:
            v = tables['Score-Avg'].get((model, score_by_model_method), float('nan'))
            vals.append(v if not math.isnan(v) else 0.0)
        ax.bar(
            x, vals,
            color='#117733',
            edgecolor='#0A4D22',
            linewidth=0.5,
            zorder=2,
        )
        ax.set_ylabel('Average score')
        # ax.set_xlabel('Model')
        ax.set_xticks(x)
        ax.set_xticklabels([short_model_name(m) for m in models], rotation=28, ha='right')
        _style_axes_minimal_spines(ax)
        ax.yaxis.grid(True, linestyle='-', linewidth=0.5, alpha=0.55)
        ax.set_axisbelow(True)
        ymax = max(vals) if vals else 1.0
        ax.set_ylim(0, ymax * 1.1 if ymax > 0 else 1.0)
        _tight_layout_margins(fig, _FIG_RECT_DEFAULT)
        fig.savefig(os.path.join(output_dir, 'score_by_model.png'), facecolor='white')
        plt.close(fig)

    # --- 2c. Pass rate by model (same layout as score_by_model; uses Pass@1) ---
    if models and score_by_model_method in method_set:
        fig, ax = plt.subplots(figsize=(max(9.0, len(models) * 0.72), 6.0), facecolor='white')
        ax.set_facecolor('white')
        x = list(range(len(models)))
        vals = []
        for model in models:
            v = tables['Pass@1'].get((model, score_by_model_method), float('nan'))
            vals.append(v if not math.isnan(v) else 0.0)
        ax.bar(
            x, vals,
            color='#117733',
            edgecolor='#0A4D22',
            linewidth=0.5,
            zorder=2,
        )
        ax.set_ylabel('Pass rate (%)')
        # ax.set_xlabel('Model')
        ax.set_xticks(x)
        ax.set_xticklabels([short_model_name(m) for m in models], rotation=28, ha='right')
        _style_axes_minimal_spines(ax)
        ax.yaxis.grid(True, linestyle='-', linewidth=0.5, alpha=0.55)
        ax.set_axisbelow(True)
        ymax = max(vals) if vals else 1.0
        ax.set_ylim(0, min(100.0, ymax * 1.12 + 2) if ymax > 0 else 1.0)
        _tight_layout_margins(fig, _FIG_RECT_DEFAULT)
        fig.savefig(os.path.join(output_dir, 'pass_rate_by_model.png'), facecolor='white')
        plt.close(fig)

    # --- 3. Discovery rate vs. T + score vs. T (same layout; markers match line, no white halo) ---
    if models:
        k_vals = list(DISCOVERY_K_VALUES)
        y_disc = []
        for model in models:
            row = []
            for k in k_vals:
                vals = [
                    tables[f'Discovery@{k}'].get((model, m))
                    for m in methods
                    if (model, m) in tables[f'Discovery@{k}']
                ]
                vals = [v for v in vals if v is not None and not math.isnan(v)]
                row.append(sum(vals) / len(vals) if vals else 0)
            y_disc.append(row)
        _plot_iteration_budget_lines(
            models, k_vals, y_disc,
            'Discovery rate (%)',
            os.path.join(output_dir, 'discovery_rate_agg.png'),
            ymax_cap=100.0,
        )
        if results is not None and all_file_ids is not None:
            y_score = _y_lists_score_vs_iteration(
                results, models, methods, all_file_ids, k_vals,
            )
            _plot_iteration_budget_lines(
                models, k_vals, y_score,
                'Average score',
                os.path.join(output_dir, 'score_vs_iteration.png'),
            )


def plot_task_env_heatmaps(results, models, methods, base_output_dir, scratch_mode=False):
    """Draws heatmaps for score_avg and pass rate on each task intersecting its env.
    scratch_mode: if True, fn is single-env (all_Initial.json, all_Stage-1.json); pair = env name."""
    if not HAS_MATPLOTLIB:
        return
    
    output_dir = os.path.join(base_output_dir, 'task_env_heatmaps')
    os.makedirs(output_dir, exist_ok=True)
    
    _configure_matplotlib_academic()

    for model in models:
        for method in methods:
            if method not in results[model]:
                continue
            
            # task_env_data[task][pair] = {'scores': [], 'successes': []}
            task_env_data = defaultdict(lambda: defaultdict(lambda: {'scores': [], 'successes': []}))
            
            for fid, data in results[model][method].items():
                # fid is task_name/fn
                if '/' not in fid:
                    continue
                task_name, fn = fid.split('/', 1)
                
                if scratch_mode:
                    # Scratch: all_Initial.json -> Initial, all_Stage-1.json -> Stage-1
                    if not fn.startswith('all_') or not fn.endswith('.json'):
                        continue
                    pair = fn[4:-5]  # strip "all_" and ".json"
                else:
                    # Pair files: all_{source}_to_{target}.json
                    match = re.match(r'all_(.+)_to_([^.]+)', fn)
                    if not match:
                        continue
                    source = match.group(1).lower()
                    target = match.group(2).lower()
                    if '_' in source and not source.startswith('stage-'): source = source.split('_')[0]
                    if '_' in target and not target.startswith('stage-'): target = target.split('_')[0]
                    pair = f"{source}_to_{target}"
                
                task_env_data[task_name][pair]['scores'].append(data.get('best_score', 0.0))
                task_env_data[task_name][pair]['successes'].append(1.0 if data.get('success', False) else 0.0)

            if not task_env_data:
                continue

            all_tasks = sorted(task_env_data.keys())
            
            all_pairs_set = set()
            for t in task_env_data:
                all_pairs_set.update(task_env_data[t].keys())
            
            if scratch_mode:
                def env_sort_key(p):
                    if p == 'Initial': return (0, 0)
                    m = re.search(r'Stage-(\d+)', p, re.I)
                    if m: return (1, int(m.group(1)))
                    return (2, p)
                sorted_pairs = sorted(list(all_pairs_set), key=env_sort_key)
            else:
                def pair_sort_key(p):
                    def stage_to_val(s):
                        if s == 'initial': return (0, 0)
                        m = re.search(r'stage-(\d+)', s)
                        if m: return (1, int(m.group(1)))
                        return (2, s)
                    if '_to_' not in p: return (3, p)
                    parts = p.split('_to_', 1)
                    return stage_to_val(parts[0]) + stage_to_val(parts[1])
                sorted_pairs = sorted(list(all_pairs_set), key=pair_sort_key)
            
            model_short = short_model_name(model)
            method_disp = method_display_name(method)
            
            for metric_type in ['score_avg', 'pass_rate']:
                fig, ax = plt.subplots(
                    figsize=(max(9.5, len(all_tasks) * 1.0), max(7.5, len(sorted_pairs) * 0.88)),
                    facecolor='white',
                )
                ax.set_facecolor('#FAFAFA')
                
                grid = []
                for pair in sorted_pairs:
                    row = []
                    for task in all_tasks:
                        vals_dict = task_env_data[task].get(pair)
                        if vals_dict:
                            vals = vals_dict['scores'] if metric_type == 'score_avg' else vals_dict['successes']
                            avg_val = sum(vals) / len(vals)
                            if metric_type == 'pass_rate':
                                avg_val *= 100
                            row.append(avg_val)
                        else:
                            row.append(float('nan'))
                    grid.append(row)
                
                plot_data = [[(v if not math.isnan(v) else 0) for v in row] for row in grid]
                v_max = 100.0
                
                im = ax.imshow(
                    plot_data,
                    cmap='YlGnBu',
                    vmin=0,
                    vmax=v_max,
                    aspect='auto',
                    interpolation='nearest',
                )
                
                ax.set_xticks(range(len(all_tasks)))
                ax.set_yticks(range(len(sorted_pairs)))
                ax.set_xticklabels(all_tasks, rotation=40, ha='right')
                ax.set_yticklabels(sorted_pairs)
                for s in ax.spines.values():
                    s.set_linewidth(0.9)
                    s.set_edgecolor(_ACCENT_TEXT)
                ax.tick_params(axis='both', length=4, width=0.8)
                ax.set_xlabel('Task')
                ax.set_ylabel('Environment pair')
                for i in range(len(sorted_pairs) + 1):
                    ax.axhline(i - 0.5, color='white', linewidth=0.85, zorder=5)
                for j in range(len(all_tasks) + 1):
                    ax.axvline(j - 0.5, color='white', linewidth=0.85, zorder=5)
                
                for i in range(len(sorted_pairs)):
                    for j in range(len(all_tasks)):
                        val = grid[i][j]
                        if not math.isnan(val):
                            txt = f'{val:.1f}' if metric_type == 'score_avg' else f'{val:.0f}'
                            tc = 'white' if val > v_max * 0.58 else _ACCENT_TEXT
                            ax.text(j, i, txt, ha='center', va='center', color=tc, fontsize=16)

                metric_label = 'Average score' if metric_type == 'score_avg' else 'Pass rate (%)'
                cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.02, aspect=22)
                cbar.ax.tick_params(labelsize=18, width=0.7, length=3)
                cbar.set_label(metric_label, fontsize=18)
                _tight_layout_margins(fig, _FIG_RECT_DEFAULT)
                
                safe_model = model_short.replace('/', '_').replace(' ', '_')
                safe_method = method_disp.replace('/', '_').replace(' ', '_')
                filename = f"{safe_model}_{safe_method}_{metric_type}.png"
                fig.savefig(os.path.join(output_dir, filename), facecolor='white')
                plt.close(fig)


def _run_evaluation(results, all_file_ids, plot_base_dir, scratch_mode, label, task_filter, args):
    """Compute metrics, print tables, and save plots for one results set."""
    models = _get_ordered_models(list(results.keys()))
    methods = _get_ordered_methods({m for model in results for m in results[model]})

    metric_names = ['Pass@1', 'Score-Avg', 'Iteration-Avg', 'Efficiency-Avg', 'CodeUsage-Avg']
    metric_names += [f'Discovery@{k}' for k in DISCOVERY_K_VALUES]

    tables = {mn: {} for mn in metric_names}
    for model in models:
        for method in methods:
            if method not in results[model]:
                continue
            metrics = compute_metrics(results[model][method], all_file_ids)
            for mn in metric_names:
                tables[mn][(model, method)] = metrics.get(mn, float('nan'))

    eff_key = 'Efficiency-Avg'
    all_eff = [v for v in tables[eff_key].values() if not math.isnan(v)]
    if all_eff:
        max_eff = max(all_eff)
        if max_eff > 0:
            for k in tables[eff_key]:
                if not math.isnan(tables[eff_key][k]):
                    tables[eff_key][k] /= max_eff

    print(f"\n# {label} Results for {task_filter}\n")
    print(f"Filter: {task_filter} | Unique files: {len(all_file_ids)}")

    print(f"\n## Aggregated Statistics (All Tasks Combined)\n")
    for mn in metric_names:
        if args.format == 'latex':
            print_latex_table(mn, models, methods, tables[mn])
        else:
            print_markdown_table(mn, models, methods, tables[mn])

    if not args.no_per_task:
        task_groups = defaultdict(list)
        for fid in all_file_ids:
            task_name = fid.split('/')[0]
            task_groups[task_name].append(fid)
        sorted_tasks = sorted(task_groups.keys())
        if len(sorted_tasks) > 1:
            print(f"\n## Per-Task Statistics\n")
            for task_name in sorted_tasks:
                task_fids = task_groups[task_name]
                print(f"\n### Task: {task_name} ({len(task_fids)} transitions)\n")
                task_tables = {mn: {} for mn in metric_names}
                for model in models:
                    for method in methods:
                        if method not in results[model]:
                            continue
                        task_metrics = compute_metrics(results[model][method], task_fids)
                        for mn in metric_names:
                            task_tables[mn][(model, method)] = task_metrics.get(mn, float('nan'))
                for mn in metric_names:
                    if args.format == 'latex':
                        print_latex_table(mn, models, methods, task_tables[mn])
                    else:
                        print_markdown_table(mn, models, methods, task_tables[mn])

    plot_dir = os.path.join(plot_base_dir, "plots", task_filter)
    plot_results(
        tables, models, methods, plot_dir,
        score_by_model_method=args.score_by_model_method,
        results=results,
        all_file_ids=all_file_ids,
    )
    plot_task_env_heatmaps(results, models, methods, plot_dir, scratch_mode=scratch_mode)
    print(f"\nPlots saved to: {plot_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=str, default='all')
    parser.add_argument('--format', choices=('latex', 'markdown'), default='markdown')
    parser.add_argument('--no-per-task', action='store_true', help='Disable per-task statistics output')
    parser.add_argument(
        '--score-by-model-method',
        type=str,
        default='baseline',
        metavar='METHOD',
        help='Internal method name for score_by_model.png and pass_rate_by_model.png (default: baseline)',
    )
    args = parser.parse_args()

    # 1. evaluation_results (pair transitions: all_*_to_*.json)
    results, all_file_ids = load_results(RESULTS_DIR, args.task)
    if all_file_ids:
        _run_evaluation(results, all_file_ids, RESULTS_DIR, scratch_mode=False,
                        label="Evaluation", task_filter=args.task, args=args)
    else:
        print(f"No results found in evaluation_results for filter: {args.task}")

    # 2. evaluation_results_scratch (single-env: all_Initial.json, all_Stage-1.json, ...)
    results_scratch, all_file_ids_scratch = load_results_scratch(SCRATCH_DIR, args.task)
    if all_file_ids_scratch:
        _run_evaluation(results_scratch, all_file_ids_scratch, SCRATCH_DIR, scratch_mode=True,
                        label="Scratch", task_filter=args.task, args=args)
    else:
        print(f"No results found in evaluation_results_scratch for filter: {args.task}")


if __name__ == '__main__':
    main()
