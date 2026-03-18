# Methods Implementation Audit

One-by-one verification that each method under `methods/` is **actually used** in the evaluation pipeline (evaluate.py, evaluate_cross_mutated.py). Gaps that were found and fixed are noted.

**Evaluation paths:**
- **evaluate.py** TaskEvaluator: single-task or single pair (when `--source-env`/`--target-env`). __init__ sets method-specific state; evaluate() or run_single_pair() uses it.
- **evaluate_cross_mutated.py** run_single_pair(): pair-based evaluation (used by run_evaluate_parallel.py). Uses the same TaskEvaluator from evaluate.py; must init and use each method’s logic.

---

## 1. baseline ✅

| Where | Status |
|-------|--------|
| evaluate.py | Default solver; format_initial_prompt / format_revision_prompt; no extra state. |
| evaluate_cross_mutated.py | Generic revision loop (format_mutated_prompt / format_mutated_revision_prompt). |

**Verdict:** Implemented.

---

## 2. sys_feedback ✅

| Where | Status |
|-------|--------|
| evaluate.py | enable_feedback=True; format_feedback(..., include_suggestions=True). |
| evaluate_cross_mutated.py | format_feedback(..., include_suggestions=getattr(evaluator, "enable_feedback", False)). |

**Verdict:** Implemented.

---

## 3. reflexion ✅ (fixed earlier)

| Where | Status |
|-------|--------|
| evaluate.py | __init__: reflections, reflections_str, reflect_solver (SolverInterface openai), REFLEXION_SYSTEM_PROMPT. _generate_reflection(). |
| evaluate_cross_mutated.py | Prepends reflections_str to prompt; after fail calls _generate_reflection, appends to reflections, format_reflections_str. |

**Verdict:** Implemented (after adding reflexion init and _generate_reflection in evaluate.py and passing reflect_model_name).

---

## 4. textgrad ✅ (fixed in this audit)

| Where | Status |
|-------|--------|
| evaluate.py | **Was missing:** tg_engine, tg_code_var, tg_optimizer. **Fixed:** __init__ sets tg_engine = create_textgrad_engine(), tg_code_var/tg_optimizer = None. |
| evaluate_cross_mutated.py | iteration > 1: textgrad_optimize_step when tg_code_var is not None. **Fixed:** after first revision, if tg_code_var is None and tg_engine exists, call init_textgrad_components(current_code, tg_engine) and set tg_code_var, tg_optimizer. Then set_value(current_code) for later iters. |

**Verdict:** Implemented after adding TextGrad init in evaluate.py and init_textgrad_components after iter 1 in cross_mutated.

---

## 5. self_refine ✅

| Where | Status |
|-------|--------|
| evaluate.py | max_iterations capped at 20. (Single-task loop does not have self_verify inner branch; that path is less used.) |
| evaluate_cross_mutated.py | iteration > 1: self_verify inner loop, format_revision_prompt_self_refine_inner, one verifier run; self_refine_inner_steps in history. |

**Verdict:** Implemented in cross_mutation path.

---

## 6. self_refine_inner_only ✅

| Where | Status |
|-------|--------|
| evaluate.py | max_iterations = 1. |
| evaluate_cross_mutated.py | Same self_verify branch when (self_refine_inner_only and iteration == 1) or (self_refine and iteration > 1). |

**Verdict:** Implemented.

---

## 7. rememberer ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: load_rememberer_memory_for_task → _rememberer_items, _rememberer_candidates. Loop: retrieve_for_prompt, inject memory_block. |
| evaluate_cross_mutated.py | rememberer_retrieve, prompt += memory_block. run_evaluate_parallel: ensure_rememberer_data_from_scratch for each pair’s source env. |

**Verdict:** Implemented.

---

## 8. expel ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: load_expel_memory_for_task → _expel_items, _expel_rules, _expel_embedder. Loop: expel_retrieve, inject. |
| evaluate_cross_mutated.py | expel_retrieve, prompt += memory_block. ensure_expel_data_from_scratch in run_evaluate_parallel. |

**Verdict:** Implemented.

---

## 9. reasoning_bank ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: _reasoning_bank_path, _reasoning_bank_items. Loop: retrieve; if k>1 MaTTS (K trajectories, contrast_and_distill, store, pick best); after iter store_after_iteration (single traj). |
| evaluate_cross_mutated.py | retrieve; MaTTS when reasoning_bank_k > 1; store_after_iteration (single and MaTTS). |

**Verdict:** Implemented.

---

## 10. memento_nonparametric ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: _memento_memory_path, _memento_items, _memento_pairs. Loop: memento_retrieve, inject; after iter memento_store, load_memory. |
| evaluate_cross_mutated.py | memento_retrieve, inject; after iter memento_store, load_memory. |

**Verdict:** Implemented.

---

## 11. a_mem_sys ✅ (fixed in this audit)

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_memory_system → _a_mem_sys_memory. Loop: a_mem_sys_retrieve, inject; after iter a_mem_sys_store. |
| evaluate_cross_mutated.py | a_mem_sys_retrieve, inject. **Was missing:** store_after_iteration. **Fixed:** after each revision call a_mem_sys_store(task_name, iteration, score, feedback, current_code, _a_mem_sys_memory). |

**Verdict:** Implemented after adding store_after_iteration in evaluate_cross_mutated.

---

## 12. ace ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_initial_playbook, build_ace_reflector_curator → _ace_playbook, _ace_reflector, _ace_curator. Loop: playbook in prompt; ACE output (bullet_ids); after iter reflect_on_iteration, update_playbook_after_iteration. |
| evaluate_cross_mutated.py | Playbook in prompt; ACE output format (bullet_ids); after iter reflect_on_iteration, update_playbook_after_iteration. |

**Verdict:** Implemented.

---

## 13. tree_of_thought ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: n_select_sample, n_generate_sample. (Single-task evaluate() loop does not implement ToT beam search; use cross_mutation path for ToT.) |
| evaluate_cross_mutated.py | iteration > 1 and tot_states: b beams × n samples, verify, keep top b; tot_states = [last_entry] after generic revision. |

**Verdict:** Implemented in cross_mutation path.

---

## 14. theta_evolve ✅

| Where | Status |
|-------|--------|
| evaluate.py | Early exit: theta_evolve run_single_task, return report. |
| evaluate_cross_mutated.py | Early exit: theta_evolve run_single_task for the pair, save report, return. |

**Verdict:** Implemented.

---

## 15. soar ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_soar_solver. evaluate() has early branch: run_pretrain, return. |
| evaluate_cross_mutated.py | Early return: get_revision_prompt = format_mutated_revision_*, solver.run_pretrain, return. |

**Verdict:** Implemented.

---

## 16. ragen ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_ragen_solver. evaluate(): run_pretrain then normal loop with same solver. |
| evaluate_cross_mutated.py | run_pretrain first, then revision loop. |

**Verdict:** Implemented.

---

## 17. discover ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_discover_solver. evaluate(): run_pretrain then normal loop. |
| evaluate_cross_mutated.py | run_pretrain first, then revision loop. |

**Verdict:** Implemented.

---

## 18. seal ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_seal_solver. Loop: after each iter _seal_ttt_step(). |
| evaluate_cross_mutated.py | After revision: evaluator._seal_ttt_step(). |

**Verdict:** Implemented.

---

## 19. genome ⚠️

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_genome_solver (or phase1). Uses genome solver in loop. |
| evaluate_cross_mutated.py | Uses same evaluator (genome solver); no per-pair phase1 or genome_best_lora_path handling. Effectively “revision with genome solver” only. |

**Verdict:** Wired for revision with genome solver; no phase1 per pair in cross_mutation.

---

## 20. absolute_zero_iter ✅

| Where | Status |
|-------|--------|
| evaluate.py | __init__: get_azr_solver. Normal generate/verify with that solver. |
| evaluate_cross_mutated.py | No explicit branch; evaluator.solver is AZR, generic loop uses it. |

**Verdict:** Implemented.

---

## 21. science_codeevolve ❌ (not in cross_mutation)

| Where | Status |
|-------|--------|
| evaluate.py | No branch. |
| evaluate_mutated.py | Top-level: if method == 'science_codeevolve' run_single_task (CodeEvolve) and return. |
| evaluate_cross_mutated.py | No branch; would run as baseline if selected. |

**Verdict:** Only in sequence/mutation-from-log path; not in run_evaluate_parallel pair path.

---

## 22. alpha_evolve ❌ (not in cross_mutation)

| Where | Status |
|-------|--------|
| evaluate.py | No branch. |
| evaluate_mutated.py | Top-level: if method == 'alpha_evolve' run_single_task and return. |
| evaluate_cross_mutated.py | No branch; would run as baseline. |

**Verdict:** Only in sequence path; not in run_evaluate_parallel pair path.

---

## Summary

| Method | evaluate.py | evaluate_cross_mutated.py | Notes |
|--------|-------------|---------------------------|-------|
| baseline | ✅ | ✅ | |
| sys_feedback | ✅ | ✅ | |
| reflexion | ✅ | ✅ | Fixed: init + _generate_reflection + reflect_model_name |
| textgrad | ✅ | ✅ | Fixed: tg_engine init + init_textgrad_components after iter 1 |
| self_refine | ✅ | ✅ | |
| self_refine_inner_only | ✅ | ✅ | |
| rememberer | ✅ | ✅ | |
| expel | ✅ | ✅ | |
| reasoning_bank | ✅ | ✅ | |
| memento_nonparametric | ✅ | ✅ | |
| a_mem_sys | ✅ | ✅ | Fixed: store_after_iteration in cross_mutated |
| ace | ✅ | ✅ | |
| tree_of_thought | ✅ (init only) | ✅ | ToT beam in cross_mutated only |
| theta_evolve | ✅ | ✅ | |
| soar | ✅ | ✅ | |
| ragen | ✅ | ✅ | |
| discover | ✅ | ✅ | |
| seal | ✅ | ✅ | |
| genome | ✅ | ⚠️ | No phase1 per pair in cross_mutation |
| absolute_zero_iter | ✅ | ✅ | |
| science_codeevolve | ❌ | ❌ | Sequence path only |
| alpha_evolve | ❌ | ❌ | Sequence path only |
