# TTT-Discover: Alignment with Official Repo

## Reference

- **Official:** `DaVinciBench/baseline/Parameter_Policy/discover/`
  - Entry: `tinker_cookbook/recipes/ttt/train.py` (CLIConfig → Config → `tinker_cookbook.rl.train.main`)
  - Advantage logic: `tinker_cookbook/rl/train.py` (`compute_advantages`, `do_group_rollout_and_filter_constant_reward`)
- **Reimplementation:** `DaVinciBench/2D_exploration/scripts/methods/Parameter_Policy/discover/`

## Algorithm alignment

- **Flow:** Rollout → (optional feedback-based expansion when all rewards equal) → compute advantages (entropic / mean_baseline / entropic_adaptive_beta) → importance_sampling (or PPO) update on LoRA. Matches official design; expansion is an adaptation (official uses `remove_constant_reward_groups=True` and drops constant-reward groups; we expand with revision prompts for 2D).
- **Advantage computation:** Implemented locally to mirror `tinker_cookbook/rl/train.py` `compute_advantages` (single-group variant). Not imported from baseline because the official uses `TrajectoryGroup` and async/tinker stack; reimplementation uses minimal in-process training.
- **Training:** Local AdamW + response-mask importance_sampling loss; official uses tinker API (forward_backward + optim_step). Same loss and optimizer hyperparameters (lr 4e-5, betas 0.9/0.95, weight_decay 0).

## Intentional adaptations (2D pipeline)

| Aspect | Official | Reimplementation | Reason |
|--------|----------|-------------------|--------|
| Constant-reward handling | Remove group (`remove_constant_reward_groups=True`) | Feedback-based expansion (revision prompt, up to `max_expansion_rounds`) | 2D tasks often start with all-0; expansion gives a learning signal instead of discarding. |
| Batching | Dataset-driven: `groups_per_batch` groups per iteration (e.g. 64×8 rollouts) | One group per epoch: `group_size` rollouts per epoch | 2D evaluation is per-task; no multi-problem batch. |
| Reward interface | Env-specific (e.g. `get_total_rewards()` from trajectories) | `verifier.verify_code()` → score/100 | 2D uses CodeVerifier and task success score. |
| max_tokens | 26000 (CLIConfig in official) | 65536 | 2D pipeline uses 65536 in all settings for long code. |

## Parameters (official vs reimplementation)

See verification report "Parameter table" for the full list. We use max_tokens=65536 everywhere. LoRA: official TTT has no lora_alpha in config; reimplementation does not set lora_alpha (uses PEFT default).

## Entry points

- **Factory:** `get_discover_solver(..., discover_* kwargs)` → `DiscoverSolver`.
- **Solver:** `run_pretrain(task_prompt, verifier)`, `generate_code(...)`, `generate_code_from_messages(...)`, `get_system_prompt()`, `set_custom_system_prompt()`, `reset_conversation()`, `cleanup()`.
- **Pipeline:** `evaluation/evaluate.py` wires discover: (1) creates solver via `get_discover_solver` when `base_method == 'discover'`, (2) at start of `evaluate()` calls `solver.run_pretrain(task_prompt, verifier)`, (3) then runs the usual generate → verify loop.

## GPU

- Official: Tinker service (GPU count depends on deployment); single-GPU or multi-GPU per worker.
- Reimplementation: Single device (`device="cuda:0"`). Training uses gradient checkpointing and micro batching to reduce memory. For 14B/32B, consider assigning 2 GPUs per worker (e.g. tensor parallel or separate inference/train devices) if the pipeline supports it.
