# GENOME method (2D reimplementation)

Phase 1 runs the official GENOME GA (from `baseline/Parameter_Policy/GENOME`) with 2D task fitness; Phase 2 uses the best LoRA for refinement.

## LoRA experts directory (required for Phase 1)

The pipeline uses `get_genome_experts_dir()` → `genome/experts/`. The **official** `get_lora_pools(lora_dir)` (we do not modify it) only recognizes subdirs with these **exact names**:

- `code_alpaca`, `gpt4_alpaca`, `cot`, `lima`, `oasst1`, `open_orca`, `flan_v2`, `science_literature`, `wizardlm`, `sharegpt`

Each subdir must contain a valid LoRA adapter: at least `adapter_model.safetensors` and `adapter_config.json` (same format as the official GENOME repo).

You need **at least two** such expert subdirs under `genome/experts/` for the GA to run.

### Setup

1. **Create structure and optionally link existing LoRAs**

   From this directory (`methods/Parameter_Policy/genome/`):

   ```bash
   python bootstrap_lora_dir.py
   ```

   This creates `experts/` and one placeholder subdir with a README. Then add at least one more expert: either create another subdir with one of the names above and put your LoRA files there, or use:

   ```bash
   python bootstrap_lora_dir.py --link-dir /path/to/parent
   ```

   where `/path/to/parent` contains subdirs named as above (e.g. `code_alpaca`, `gpt4_alpaca`). The script will create symlinks under `experts/` so that `get_lora_pools(experts)` finds them.

2. **Or** create `experts/` manually and add at least two subdirs from the list above, each with `adapter_model.safetensors` (and `adapter_config.json`).

No changes are required in the evaluation scripts; only this directory and the experts layout under it.
