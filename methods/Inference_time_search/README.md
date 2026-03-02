# Inference-time search methods on 2D_exploration

## Science-CodeEvolve

This method runs [science-codeevolve](https://github.com/inter-co/science-codeevolve) (CodeEvolve) for each 2D task and converts its output into the same report format (GIF + JSON, 1st pass only) as baseline/sys_feedback.

## Requirements

- **CodeEvolve** and its dependencies. From repo root:
  ```bash
  pip install -e DaVinciBench/baseline/Inference_time_search/science-codeevolve
  ```
  Or use a separate conda env and set `CODEEVOLVE_PYTHON` to that env's python when running.

- **OpenAI API**: Uses the same default `API_KEY` and `BASE_URL` as [evaluation/solver_interface.py](../evaluation/solver_interface.py). No need to export; override with `--api-key` if needed.
- **Local model**: Pass `--model-type local --model-name /path/to/model`; no API_BASE/API_KEY (wrapper sets dummy for CodeEvolve CLI).

## Run commands

From `DaVinciBench/2D_exploration/scripts/`:

**OpenAI API (same defaults as baseline, no export):**
```bash
python evaluation/run_evaluate_parallel.py --task category_1 --api-parallel 16 \
  --model-type openai --model-name deepseek-v3.2 \
  --max-iterations 20 --method science_codeevolve --context all
```

**Local model (path only):**
```bash
python evaluation/run_evaluate_parallel.py --task category_1 --num-workers 8 \
  --model-type local --model-name /path/to/Qwen3-14B \
  --max-iterations 20 --method science_codeevolve --context all
```

**Mutation from an existing log:**
```bash
python evaluation/run_mutation_from_log.py --log evaluation_results/category_1_01/Qwen3-14B/science_codeevolve/all_1st_pass_YYYYMMDD_pseudo.json \
  --method science_codeevolve
```

**Fill missing mutations for science_codeevolve logs:**
```bash
python evaluation/run_all_missing_mutations.py --results-dir evaluation_results
```

Results are written under `evaluation_results/<task>/<model_id>/science_codeevolve/` with the same naming as other methods (`all_1st_pass_YYYYMMDD_pseudo.json`, etc.), and GIFs under the gif tree.

---

## Alpha Evolve (OpenEvolve)

This method runs [OpenEvolve](DaVinciBench/baseline/Inference_time_search/openevolve) (open-source AlphaEvolve) for each 2D task: 20 evolution iterations per run, then converts output to the same report format (GIF + JSON, 1st pass only). LLM usage is the same as other methods: **openai** uses [solver_interface](DaVinciBench/2D_exploration/scripts/evaluation/solver_interface.py) API; **local** loads the HuggingFace model in-process (no vLLM or API needed), same as baseline/sys_feedback.

### Requirements

- **OpenEvolve** and its dependencies. From repo root:
  ```bash
  pip install -e DaVinciBench/baseline/Inference_time_search/openevolve
  ```

### Run commands

From `DaVinciBench/2D_exploration/scripts/`:

**OpenAI API:**
```bash
python evaluation/run_evaluate_parallel.py --task category_1 --api-parallel 16 \
  --model-type openai --model-name deepseek-v3.2 \
  --max-iterations 20 --method alpha_evolve --context all
```

**Local model:**
```bash
python evaluation/run_evaluate_parallel.py --task category_1 --num-workers 8 \
  --model-type local --model-name /path/to/Qwen3-14B \
  --max-iterations 20 --method alpha_evolve --context all
```

**Mutation from an existing log:**
```bash
python evaluation/run_mutation_from_log.py --log evaluation_results/category_1_01/openai_deepseek-v3.2/alpha_evolve/all_1st_pass_YYYYMMDD_pseudo.json \
  --method alpha_evolve
```

Results are written under `evaluation_results/<task>/<model_id>/alpha_evolve/` with the same naming (`all_1st_pass_YYYYMMDD_pseudo.json`, etc.), and GIFs under the gif tree.
