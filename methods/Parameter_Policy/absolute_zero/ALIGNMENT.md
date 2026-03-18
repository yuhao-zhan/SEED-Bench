# Absolute Zero Reimplementation — Alignment with Official Repo

Reference: `DaVinciBench/baseline/Parameter_Policy/Absolute-Zero-Reasoner/` (arXiv:2505.03335).

## 1. What is imported from the official repo

- **Nothing is currently imported** from the baseline. The official stack uses veRL (Ray, FSDP, vLLM rollout, DataProto) and `CodeIORewardManager` tied to parquet data and code_i/code_o/code_f problem types with Python execution. Our 2D pipeline uses the existing evaluation `CodeVerifier` and task/environment interface, so reward and training loop are **minimal adapters** around the same algorithm (REINFORCE++ + PPO clip).

- **Reward semantics aligned with official** (reward_managers.py): format error → -1.0; wrong but well-formatted → -0.5; correct → 0–1. We use the same -1.0 and -0.5; additional tiers (-0.8, -0.3) are 2D-specific shaping for denser signal (see `training/train.py` `azr_reward`).

## 2. Training parameters (aligned unless noted)

| Parameter | Official (azr_ppo_trainer.yaml / main) | Reimplementation | Match |
|-----------|----------------------------------------|-------------------|-------|
| lr (actor) | 1e-6 | --lr 1e-6 | Yes |
| clip_ratio | 0.2 | --clip-ratio 0.2 | Yes |
| grad_clip | 1.0 | --grad-clip 1.0 | Yes |
| temperature | 1.0 (rollout) | --temperature 1.0 | Yes |
| top_p | 1 | --top-p 1.0 | Yes |
| max_prompt_length | 8096 | --max-prompt-length 8096 | Yes |
| max_response_length | 8096 | --max-response-length 8096 (or 2048 for 14B ZeRO-3 in run_train.sh) | Yes |
| ppo_epochs | 1 | 1 (per step) | Yes |
| gamma | 1.0 | implicit (outcome reward) | Yes |
| seed | azr.seed: 1 | --seed 1 | Yes |
| total_epochs / steps | total_epochs: 30 (over data) | --steps (e.g. 200) | By design: 2D has no fixed dataset; we use gradient steps instead of epochs |

## 3. Intentional differences (2D task)

- **Task source**: Official PROPOSE (task proposal + learnability reward) + SOLVE (accuracy reward) on code/math. We use a 2D task proposer or fixed pool; reward comes from `CodeVerifier` (2D simulation success/score).
- **LLM-based task proposal (optional)**: When training with a **concrete task** (e.g. `category_1_01` for S_01) and `--llm-propose`, the **model** proposes related task variations from the reference task and its curriculum stages (official AZR: "Using the reference ... design a new and unique ..."). The propose prompt includes the task description and existing stages (terrain_config / physics_config); the model outputs a JSON object with `terrain_config` and/or `physics_config` for a new variation. We parse it and build the task prompt; if parsing fails we fall back to programmatic stage sampling. See `training/task_proposer.py` (`propose_task_llm`, `PROPOSE_TASK_SYSTEM`, `PROPOSE_TASK_USER_TEMPLATE`).
- **Reward tiers**: We add -0.8 (trivial/too short code) and -0.3 (runtime error) for denser 2D signal; -1.0 and -0.5 match official.
- **Infrastructure**: Official uses Ray + veRL (FSDP, vLLM rollout, CodeIORewardManager). We use HuggingFace Accelerate + DeepSpeed ZeRO-2/3 and a single-model generate + verify loop to fit the 2D benchmark and evaluation scripts without changing them.

## 4. Entry points for evaluation

- **Method name**: `absolute_zero_iter`.
- **Solver**: `get_azr_solver(model_name, model_path=None, device=None)` → `AbsoluteZeroSolver`. The evaluator (`evaluate.py`) calls `get_azr_solver` when `base_method == 'absolute_zero_iter'` and uses `solver.generate_code(prompt, use_conversation=False)`; no evaluation script changes required.

## 5. GPU

- **Official**: Multi-node Ray, `n_gpus_per_node: 8`, `tensor_model_parallel_size: 2` for vLLM rollout; FSDP for actor/critic.
- **Reimplementation**: Single-node multi-GPU via Accelerate (ZeRO-2 or ZeRO-3). `run_train.sh` documents: 8B single-GPU possible with optimizer offload; 14B requires 4+ GPUs; 32B ZeRO-3. Evaluation uses the same vLLM-based solver (tp_size from env or device_count); one task pair per worker in `run_evaluate_parallel.py`.
