"""
AZR-style training pipeline for 2D_exploration: propose (task pool) -> solve (generate) -> verify (CodeVerifier) -> reward -> REINFORCE.

Run from scripts/:
  python -m training.train --model-name <HF_NAME_OR_PATH> [--task category_1] [--steps 100] [--batch-size 4] [--log-dir training_logs]
Logs: proposed_tasks.jsonl, verify_results.jsonl, rewards_summary.jsonl; checkpoints in log-dir/checkpoints/.
"""
