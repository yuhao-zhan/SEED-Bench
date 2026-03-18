# Parameter_Policy Verification Prompt

Use the following prompt when asking an LLM to verify your reimplementation against the official baseline. **Process one method at a time.**

---

## Prompt (copy below)

You are helping verify that a reimplementation of Parameter_Policy methods matches the **official GitHub repo implementation** as closely as possible, while remaining compatible with the existing evaluation pipeline.

### Scope and constraints

- **Only modify** code under:  
  `DaVinciBench/2D_exploration/scripts/methods/Parameter_Policy/<method_name>/`  
  (e.g. `genome/`, `theta_evolve/`, `absolute_zero/`, `ragen/`, `seal/`, `soar/`, `discover/`).
- **Do not change** the official repo under `DaVinciBench/baseline/Parameter_Policy/` or other scripts (e.g. under `evaluation/`). If a change outside `Parameter_Policy` is necessary, **stop and ask for explicit permission** before making it.
- **Process one method per run.** Do not mix multiple methods in one verification pass.

### Reference paths

- **Official implementations:**  
  `DaVinciBench/baseline/Parameter_Policy/`  
  (e.g. `GENOME/`, `ThetaEvolve/`, `Absolute-Zero-Reasoner/`, `RAGEN/`, `SEAL/`, `SOAR/`, `discover/`).
- **Your reimplementation:**  
  `DaVinciBench/2D_exploration/scripts/methods/Parameter_Policy/`  
  (e.g. `genome/`, `theta_evolve/`, `absolute_zero/`, `ragen/`, `seal/`, `soar/`, `discover/`).
- **Evaluation pipeline (read-only for context):**  
  `DaVinciBench/2D_exploration/scripts/evaluation/`  
  (e.g. `run_evaluate_parallel.py`, `run_evaluate_parallel_from_scratch.py`, `evaluate.py`, `evaluate_from_scratch.py`, `evaluate_mutated.py`).

---

### Verification steps (follow in order)

#### 1. Algorithm, logic, and reuse from official repo

- **1.1** Read the **official** implementation for the current method in `DaVinciBench/baseline/Parameter_Policy/<OfficialMethodName>/`. Understand the end-to-end flow: entry points, training/eval loops, selection/crossover/mutation (if any), reward/loss, and how results are produced.
- **1.2** Identify all **reusable** pieces in the official repo that can be used as-is:
  - Functions (e.g. merge weights, selection, crossover).
  - Classes (e.g. config, individual, trainer).
  - Prompts, templates, or config strings.
  - Constants and hyperparameters.
- **1.3** In the reimplementation under `DaVinciBench/2D_exploration/scripts/methods/Parameter_Policy/<method>/`:
  - Anything that **can be imported directly** from the official repo **must** be imported from there (e.g. `from src.genome import Genome, GenomeConfig` or equivalent from the baseline path). Do not reimplement those parts.
  - Anything that **must** be adapted (e.g. task-specific fitness, 2D env interface) should be the **minimal** wrapper around official logic; document why the adapter exists.
- **1.4** Confirm there are **no logical conflicts**: control flow, selection criteria, and termination conditions in the reimplementation match the official design, except where explicitly adapted for the 2D evaluation task.

#### 2. Training parameters and implementation details

- **2.1** Extract from the official repo all **training (and related) parameters**: learning rate, batch size, epochs/iterations, population size, rollout count, PPO/GRPO options, LoRA rank, temperature, etc.
- **2.2** Compare them **one-by-one** with the reimplementation. List any mismatch (name or value).
- **2.3** Align the reimplementation so that **every such parameter** matches the official default or the value used in the official scripts, unless an explicit reason (e.g. 2D task interface) requires a different value—in which case document it.
- **2.4** Ensure there are **no conflicting defaults** (e.g. one place using 50 iters and another 100 for the same concept).

#### 3. Compatibility with the current evaluation task

- **3.1** Read how the evaluation pipeline uses this method:
  - How `run_evaluate_parallel.py` / `run_evaluate_parallel_from_scratch.py` invoke evaluation (e.g. per task, per task–env pair).
  - How `evaluate.py` / `evaluate_from_scratch.py` / `evaluate_mutated.py` create the evaluator, pass `method`, and call into the method (e.g. custom solver, Phase 1 + Phase 2, or training script).
- **3.2** Ensure the reimplementation:
  - Exposes the **entry points and signatures** expected by these scripts (e.g. `run_single_task(...)`, `get_*_solver(...)`, or whatever the pipeline calls).
  - Uses the **task/environment interface** used by the benchmark (e.g. task name, stage_id, env_overrides, `CodeVerifier`, `load_task_prompt`, etc.) without changing the evaluation scripts.
- **3.3** Do **not** change the evaluation scripts to fit the method; only adapt the method code under `Parameter_Policy/<method>/` so it fits the existing pipeline.

#### 4. GPU usage and OOM prevention

- **4.1** From the official repo, determine:
  - How many GPUs the method expects (e.g. single-GPU training, multi-GPU data parallel, or tensor parallel for large models).
  - Any official scripts or configs that set `CUDA_VISIBLE_DEVICES`, `accelerate` config, or similar.
- **4.2** From the evaluation side, note:
  - `run_evaluate_parallel.py`: currently assigns one task pair per worker; 8B/14B typically one GPU per pair, 32B often two GPUs per pair for inference.
  - `run_evaluate_parallel_from_scratch.py`: can use TP2 (two GPUs per worker) for e.g. `theta_evolve` or 32B.
  - Training (e.g. PPO, LoRA, rollout) may need **more** memory than inference; a single GPU may be enough for 8B but not for 14B/32B with training.
- **4.3** For the method you are verifying:
  - Document how many GPUs the **official** implementation assumes and for what (inference vs training).
  - Ensure the reimplementation either (a) uses the same GPU assumption when run via the existing scripts, or (b) clearly documents the required GPU setup (e.g. “this method needs 2 GPUs for 32B training”) and, if possible, add a small **demo/check** (e.g. a minimal run or a comment) so that OOM can be detected.
- **4.4** If you have the ability to run a **short demo** (e.g. one task, one env, few steps), run it and report:
  - Whether it completes without OOM.
  - If OOM occurs, suggest a concrete GPU allocation (e.g. “use 2 GPUs per worker for this method when model is 14B or larger”) and implement only the changes allowed under “Scope and constraints” (e.g. inside `Parameter_Policy/<method>/` or env/device handling within that module). Do not modify the main evaluation scripts unless the user has agreed.

#### 5. Output format

For the single method you verified, produce:

1. **Summary:** Method name; one paragraph on alignment with official repo and any intentional adaptations.
2. **Imports from official repo:** List of symbols and files that are now imported from the baseline instead of reimplemented.
3. **Parameter table:** Official parameter name, official default/value, value in reimplementation, match (yes/no), and note if different by design.
4. **Entry points:** How the evaluation pipeline calls this method and confirmation that signatures/contracts match.
5. **GPU:** Official GPU assumption; reimplementation GPU usage; result of any demo run (success / OOM); recommended GPU allocation if needed.
6. **Changes made:** Only under `Parameter_Policy/<method>/`; bullet list of files and what was changed.
7. **Conflicts or follow-ups:** Any remaining mismatch, open point, or change that would require modifying the official repo or evaluation scripts (and therefore need your approval).

---

### Chain-of-thought (CoT) style

While working, reason step by step:

- First, state what you are verifying (e.g. “Step 1.1: Reading official GENOME run_genome.py and genome.py”).
- Then state what you found (e.g. “Official uses population_size=10, max_iter=50; reimplementation has population_size=10, genome_iters=50”).
- Then state the conclusion or action (e.g. “Match” or “Align reimplementation to use max_iter name for consistency” or “Document that genome_iters is the same as max_iter”).

Apply this for algorithm logic, parameters, pipeline compatibility, and GPU behavior so the verification is auditable and reproducible.
