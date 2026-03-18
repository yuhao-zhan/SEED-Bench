# Methods Checklist: Where Each Method Is Wired

One-by-one check of all methods under `methods/` and their use in evaluation paths.

**Paths:**
- **evaluate.py**: from-scratch / single-task (no pair). TaskEvaluator.__init__ loads method state; evaluate() runs the main loop.
- **evaluate_mutated.py**: sequence-based mutation (run_mutation_from_log). mutated_evaluate() replaces the evaluate() loop.
- **evaluate_cross_mutated.py**: pair-based cross-mutation (run_evaluate_parallel). run_single_pair() runs one (source_env → target_env) pair.

---

## 1. baseline

| Location | Status |
|----------|--------|
| evaluate.py | ✅ Main loop: format_initial_prompt / format_revision_prompt, generate, verify. No special state. |
| evaluate_mutated.py | ✅ Same loop (revision with mutated prompts). |
| evaluate_cross_mutated.py | ✅ Generic revision loop (format_mutated_prompt / format_mutated_revision_prompt). |

**Verdict:** Fully wired everywhere.

---

## 2. sys_feedback

| Location | Status |
|----------|--------|
| evaluate.py | ✅ Same as baseline; enable_feedback controls include_suggestions in format_feedback. |
| evaluate_mutated.py | ✅ include_suggestions=evaluator.enable_feedback in format_feedback. |
| evaluate_cross_mutated.py | ✅ format_feedback(..., include_suggestions=getattr(evaluator, "enable_feedback", False)). |

**Verdict:** Fully wired everywhere.

---

## 3. reflexion

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: reflect_solver, reflections. Loop: prepend reflections_str to prompt; after fail call _generate_reflection, update reflections_str. |
| evaluate_mutated.py | ✅ Prepends reflections to prompt; after fail generates reflection, updates reflections_str. |
| evaluate_cross_mutated.py | ✅ Prepends reflections_str to prompt; after fail calls _generate_reflection, updates reflections_str. |

**Verdict:** Fully wired in cross_mutation.

---

## 4. textgrad

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: tg_code_var, tg_optimizer, tg_engine. (Main loop uses normal generate in from-scratch; textgrad step is used in other flows.) |
| evaluate_mutated.py | ✅ iteration > 1: textgrad_optimize_step, verify, append; tg_code_var set from previous code at start. |
| evaluate_cross_mutated.py | ✅ iteration > 1 and tg_code_var: textgrad_optimize_step, verify, append. After generic revision: tg_code_var.set_value(current_code). |

**Verdict:** Fully wired in cross_mutation.

---

## 5. self_refine

| Location | Status |
|----------|--------|
| evaluate.py | ✅ max_iterations capped 20. Loop: iteration > 1 uses self_verify inner loop + format_revision_prompt_self_refine_inner (in evaluate.py flow). |
| evaluate_mutated.py | ✅ iteration > 1: self_verify loop, then one verifier run; phase/self_refine_inner_steps saved. |
| evaluate_cross_mutated.py | ✅ iteration > 1: self_verify inner loop, format_revision_prompt_self_refine_inner, one verifier; self_refine_inner_steps in history. |

**Verdict:** Fully wired in cross_mutation.

---

## 6. self_refine_inner_only

| Location | Status |
|----------|--------|
| evaluate.py | ✅ max_iterations = 1. Otherwise same as self_refine (one round with inner loop). |
| evaluate_mutated.py | ✅ Not explicitly branched; would run as self_refine with max_iterations=1. |
| evaluate_cross_mutated.py | ⚠️ No explicit branch. Runs as generic revision (max_iterations set in evaluator). If evaluator.max_iterations is 1, only one revision; but no self_verify inner loop for that single round. |

**Fixed:** In cross_mutation, self_refine_inner_only now runs the same self_verify inner loop on iteration 1 (condition: self_refine_inner_only and iteration == 1); first prompt uses format_mutated_prompt when history has only iter 0.

---

## 7. rememberer

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: load_rememberer_memory_for_task → _rememberer_items, _rememberer_candidates. Loop: retrieve_for_prompt, inject memory_block into prompt. |
| evaluate_mutated.py | ✅ Memory loaded from base log / restore; in revision loop memory would need to be injected (evaluate_mutated “else” branch does not inject rememberer in prompt; it only has reflexion prepend). So mutated path may not inject rememberer. |
| evaluate_cross_mutated.py | ✅ memory_block = rememberer_retrieve(...); prompt += memory section. |

**Note:** evaluate_mutated’s generic “else” branch does not add memory_block for rememberer/expel/etc.; only reflexion is prepended. So rememberer is wired in cross_mutated but may be missing in the mutated “else” branch (run_mutation_from_log). Cross_mutation: OK.

---

## 8. expel

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: load_expel_memory_for_task → _expel_items, _expel_rules, _expel_embedder. Loop: expel_retrieve, inject memory_block. |
| evaluate_mutated.py | ⚠️ Same as rememberer: no memory_block injection in the “else” revision branch. |
| evaluate_cross_mutated.py | ✅ expel_retrieve, prompt += memory section. |

**Verdict:** Cross_mutation wired. evaluate_mutated generic branch does not inject expel memory (same gap as rememberer).

---

## 9. reasoning_bank

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: _reasoning_bank_path, _reasoning_bank_items. Loop: (1) retrieve_for_prompt → memory_block; (2) if reasoning_bank_k > 1: MaTTS (K parallel trajectories, contrast_and_distill, pick best); (3) after iter: store_after_iteration. |
| evaluate_mutated.py | ⚠️ No MaTTS, no explicit memory inject in “else” branch. |
| evaluate_cross_mutated.py | ✅ retrieve_for_prompt → memory_block, prompt += memory. ❌ No reasoning_bank_k > 1 (MaTTS). ❌ No store_after_iteration. |

**Fixed:** Cross_mutation now has (1) MaTTS when reasoning_bank_k > 1 (K parallel trajectories, contrast_and_distill, store, pick best); (2) store_after_iteration for single trajectory (extract_memory_items_llm, judge_success_llm).

---

## 10. memento_nonparametric

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: _memento_memory_path, _memento_items, _memento_pairs. Loop: memento_retrieve → memory_block; after iter: memento_store, reload. |
| evaluate_mutated.py | ⚠️ No memory inject in “else” branch; restore from base log. |
| evaluate_cross_mutated.py | ✅ memento_retrieve, prompt += memory. ❌ No store_after_iteration. |

**Fixed:** Cross_mutation now calls memento store_after_iteration after each revision and reloads _memento_items, _memento_pairs.

---

## 11. a_mem_sys

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_memory_system → _a_mem_sys_memory. Loop: a_mem_sys_retrieve → memory_block; after iter: a_mem_sys_store. |
| evaluate_mutated.py | ⚠️ No memory inject in “else” branch. |
| evaluate_cross_mutated.py | ✅ a_mem_sys_retrieve, prompt += memory. ❌ No store_after_iteration. |

**Gap in cross_mutation:** No store_after_iteration.

---

## 12. ace

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_initial_playbook, build_ace_reflector_curator → _ace_playbook, _ace_reflector, _ace_curator. Loop: playbook in prompt; ACE output format (bullet_ids); after iter: reflect_on_iteration, update_playbook_after_iteration. |
| evaluate_mutated.py | ⚠️ restore_playbook_from_base_log; no reflector/curator update in loop. |
| evaluate_cross_mutated.py | ✅ memory_block = playbook text, prompt += memory. ❌ No “Output format (ACE): bullet_ids” in prompt. ❌ No reflector/curator after iteration (playbook never updated). |

**Fixed:** Cross_mutation now (1) appends ACE output format (bullet_ids) to prompt; (2) after each revision runs reflect_on_iteration and update_playbook_after_iteration, updates _ace_playbook and _ace_next_global_id.

---

## 13. tree_of_thought

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: n_select_sample, n_generate_sample. Loop: ToT beam search (generate n per beam, verify, keep top b). |
| evaluate_mutated.py | ✅ iteration > 1 and tot_states: format_mutated_prompt per state, n samples, verify, tot_states = top b. |
| evaluate_cross_mutated.py | ✅ iteration > 1 and tot_states: same (mutated prompt per state, parallel gen, verify, tot_states = top b). Bootstrap: tot_states = [last_entry] after generic revision. |

**Verdict:** Fully wired in cross_mutation.

---

## 14. theta_evolve

| Location | Status |
|----------|--------|
| evaluate.py | ✅ Early return: run_single_task (theta_evolve train.py), return report. |
| evaluate_mutated.py | ✅ Handled in run_single_task-style branch (not in run_single_pair). |
| evaluate_cross_mutated.py | ✅ Early return: theta_evolve run_single_task for the pair, save report, return. |

**Verdict:** Fully wired in cross_mutation.

---

## 15. soar

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_soar_solver. Early branch: run_pretrain (get_initial_prompt, get_revision_prompt), merge history, return. No fallback to normal loop. |
| evaluate_mutated.py | ✅ Not in run_single_pair (sequence path). |
| evaluate_cross_mutated.py | ✅ Early return: get_initial_prompt = format_mutated_prompt, get_revision_prompt = format_mutated_revision_*, solver.run_pretrain, return. |

**Verdict:** Fully wired in cross_mutation.

---

## 16. ragen

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_ragen_solver. run_pretrain (rollout + GRPO + PPO), then fall through to normal loop with tuned solver. |
| evaluate_mutated.py | ✅ Pretrain then loop. |
| evaluate_cross_mutated.py | ✅ run_pretrain first, then fall through to revision loop (same solver). |

**Verdict:** Fully wired in cross_mutation.

---

## 17. discover

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_discover_solver. run_pretrain (TTT), then fall through to normal loop. |
| evaluate_mutated.py | ✅ Pretrain then loop. |
| evaluate_cross_mutated.py | ✅ run_pretrain first, then revision loop. |

**Verdict:** Fully wired in cross_mutation.

---

## 18. seal

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_seal_solver. Loop: after each iter _seal_ttt_step(). |
| evaluate_mutated.py | ✅ After revision: evaluator._seal_ttt_step(). |
| evaluate_cross_mutated.py | ✅ After revision: evaluator._seal_ttt_step(). |

**Verdict:** Fully wired in cross_mutation.

---

## 19. genome

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_genome_solver (or phase1). Main: genome uses special solver; report can include genome_best_lora_path. |
| evaluate_mutated.py | ✅ run_single_task / sequence; genome_best_lora_path from base log. |
| evaluate_cross_mutated.py | ⚠️ No dedicated branch. Uses generic revision loop; evaluator.solver may be genome solver if method=genome (set in __init__). So “solver” is genome-aware but run_single_pair does not run phase1 or pass pair-specific LoRA; it just runs revision with whatever solver was created. |

**Gap:** Cross_mutation uses the same evaluator (with genome solver if method=genome) but does not run genome phase1 per pair or handle genome_best_lora_path per pair. So genome in cross_mutation is “revision with genome solver” only.

---

## 20. absolute_zero_iter

| Location | Status |
|----------|--------|
| evaluate.py | ✅ __init__: get_azr_solver (Absolute-Zero solver). Loop: normal generate/verify with that solver. |
| evaluate_mutated.py | ✅ Same solver in loop. |
| evaluate_cross_mutated.py | ⚠️ No explicit branch. Evaluator created with method=absolute_zero_iter gets AZR solver in __init__; run_single_pair uses evaluator.solver.generate_code. So it uses AZR solver in the generic loop. |

**Verdict:** Effectively wired (solver is AZR; no extra per-iteration logic needed in cross_mutated).

---

## 21. science_codeevolve

| Location | Status |
|----------|--------|
| evaluate.py | ❌ Not in evaluate.py main path (no science_codeevolve branch). |
| evaluate_mutated.py | ✅ At top level: if method == 'science_codeevolve' run_single_task (CodeEvolve) and return; never calls run_single_pair. So used only in sequence/mutation-from-log. |
| evaluate_cross_mutated.py | ❌ No branch. run_evaluate_parallel never invokes science_codeevolve run_single_task for a pair. |

**Gap:** Cross_mutation (run_evaluate_parallel) has no science_codeevolve; it would run as baseline (generic revision). To support: add a branch in run_single_pair that calls science_codeevolve run_single_task for the pair (with env_overrides for target env).

---

## 22. alpha_evolve

| Location | Status |
|----------|--------|
| evaluate.py | ❌ No alpha_evolve branch in evaluate(). |
| evaluate_mutated.py | ✅ At top level: if method == 'alpha_evolve' run_single_task (alpha_evolve) and return. |
| evaluate_cross_mutated.py | ❌ No branch. Would run as baseline. |

**Gap:** Same as science_codeevolve; no alpha_evolve in cross_mutation path.

---

## Summary Table (evaluate_cross_mutated.run_single_pair)

| Method | Wired | Gaps |
|--------|-------|------|
| baseline | ✅ | — |
| sys_feedback | ✅ | — |
| reflexion | ✅ | — |
| textgrad | ✅ | — |
| self_refine | ✅ | — |
| self_refine_inner_only | ✅ | Fixed: self_verify loop on iteration 1. |
| rememberer | ✅ | — |
| expel | ✅ | — |
| reasoning_bank | ✅ | MaTTS (k>1) + store_after_iteration (single and MaTTS). |
| memento_nonparametric | ✅ | store_after_iteration + reload memory. |
| a_mem_sys | — | Not implemented (per user). |
| ace | ✅ | bullet_ids in prompt + reflector/curator update. |
| tree_of_thought | ✅ | — |
| theta_evolve | ✅ | — |
| soar | ✅ | — |
| ragen | ✅ | — |
| discover | ✅ | — |
| seal | ✅ | — |
| genome | ⚠️ | Uses genome solver but no phase1 per pair. |
| absolute_zero_iter | ✅ | Uses AZR solver in generic loop. |
| science_codeevolve | — | Not implemented (per user). |
| alpha_evolve | — | Not implemented (per user). |
