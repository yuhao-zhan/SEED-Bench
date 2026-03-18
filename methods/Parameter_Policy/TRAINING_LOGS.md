# Parameter_Policy 训练日志说明

对 **discover**、**genome**、**ragen**、**seal**、**soar**、**theta_evolve** 六种涉及参数/训练的方法，所有训练相关结果统一保存在 **`scripts/training_log/`** 下，便于排查训练过程、对齐 official repo 和 benchmark 要求。

## 日志位置（统一根目录）

所有训练日志根目录：**`DaVinciBench/2D_exploration/scripts/training_log/`**

目录结构（与 category / task / model / method 一一对应）：

```
training_log/
  {category}/              # 如 Category1_Statics_Equilibrium
    {task}/                 # 如 S_01
      {model_id}/           # 如 Qwen3-4B
        {method}/           # seal, ragen, soar, discover, genome, theta_evolve
          training_config.json
          training_loss.json
          training_loss.jsonl
          training_warnings.jsonl
          training_summary.txt
          prompt_sample.txt         # 部分 method 有
          loss_fig/
            loss_vs_step.png        # 有 loss 记录时自动生成（需 matplotlib）
          rollouts/                 # （RAGEN / Discover / SOAR）rollout 阶段所有 LLM 输出
            llm_calls.jsonl         # 按顺序的每一次 LLM 调用：完整 prompt + raw_output + code + score/feedback
            episodes/               # （RAGEN）按 episode：episode_000.json, episode_001.json, ...
            epochs/                # （Discover）按 epoch：epoch_001.json, ...
            generations/            # （SOAR）按 generation：gen_001.json, ...
```

- **discover / ragen / seal / soar**：完整训练日志（config、loss、warnings、summary），有 loss 时自动生成 `loss_fig/loss_vs_step.png`。
- **ragen / discover / soar**：额外写入 **rollouts/**，保存 rollout 阶段**每一次** LLM 的输入与完整输出，便于复现与排查“中间干了什么”。
- **genome**：Phase 1（GA）运行时写入 config + summary（无 loss 曲线，无 rollouts）。
- **theta_evolve**：外部进程训练，运行结束后写入 config + summary（无 loss 曲线，无 rollouts）。

## 文件含义

| 文件 | 内容 |
|------|------|
| **training_config.json** | 本次运行的配置：method 名、task、`max_iterations` / `max_steps_verifier`、prompt 格式说明、method 自身超参，以及 benchmark 对齐 checklist。 |
| **training_loss.json** | 完整 loss-step 序列，可用于画 loss 曲线。 |
| **training_loss.jsonl** | 与上面相同内容，按行追加。 |
| **training_warnings.jsonl** | 训练过程中的 warning/error 记录。 |
| **training_summary.txt** | 人类可读摘要：method、task、benchmark checklist、loss 条数、warning/error 条数、summary extra。 |
| **prompt_sample.txt** | （部分 method）记录的 prompt 样本。 |
| **loss_fig/loss_vs_step.png** | 由 `training_loss.json` 自动绘制的 loss-step 曲线（需安装 matplotlib）。 |
| **rollouts/llm_calls.jsonl** | 按时间顺序的每一次 LLM 调用：`seq`、`episode`/`turn`/`epoch`/`generation`/`iteration`/`candidate_idx`、`prompt_text`、`messages`、`raw_output`、`extracted_code`、`score`、`success`、`error`、`feedback`、`token_usage`。 |
| **rollouts/episodes/** (RAGEN) | 每个 episode 一个 JSON：该 episode 内所有 turn 的完整数据（prompt、raw_output、code、score、feedback 等）。 |
| **rollouts/epochs/** (Discover) | 每个 epoch 一个 JSON：该 epoch 所有 trajectory（含 expansion 后的）的完整数据。 |
| **rollouts/generations/** (SOAR) | 每个 generation 一个 JSON：该 generation 内各 step 的 best 记录（prompt、code、raw_llm_output、score 等）。 |

## 用于排查的内容

- **max_iterations 是否生效**：看 `training_config.json` 里的 `max_iterations`、`benchmark_checklist.max_iterations_used`。
- **prompt 格式/内容**：看 `training_config.json` 的 `prompt_format` 和（若有）`prompt_sample.txt`。
- **训练效果**：看 `training_loss.json` 或 `loss_fig/loss_vs_step.png`；看 `training_summary.txt` 的 summary extra。
- **中途 warning/error**：看 `training_warnings.jsonl` 和 `training_summary.txt` 末尾。
- **LLM 中间到底输出了什么**：看 `rollouts/llm_calls.jsonl`（每次调用的完整输入/输出）；按 episode/epoch/generation 看则用 `rollouts/episodes/`、`rollouts/epochs/`、`rollouts/generations/`。

## 六种方法覆盖情况

| 方法 | 训练日志 | 说明 |
|------|----------|------|
| **discover** | ✅ 完整 + rollouts | run_pretrain 时写入 config、loss、warnings、summary、loss 图；rollouts 下按 epoch 保存每次 rollout 的完整 LLM 输入/输出。 |
| **genome** | ✅ config+summary | Phase 1（GA）在 evaluate_from_scratch 或单独跑时写入 config + summary（无 rollouts）。 |
| **ragen** | ✅ 完整 + rollouts | run_pretrain 时写入 config、loss、warnings、summary、loss 图；rollouts 下按 episode/turn 保存每次 LLM 调用的完整输入/输出。 |
| **seal** | ✅ 完整 | 每次 TTT（train_on_solutions）写入 config、loss、warnings、summary、loss 图（无 rollouts，TTT 用已有 solution 文本训练）。 |
| **soar** | ✅ 完整 + rollouts | run_pretrain 时写入 config、每轮 SFT 的 loss、warnings、summary、loss 图；rollouts 下按 generation/iteration 保存每次候选与 refinement 的完整 LLM 输出。 |
| **theta_evolve** | ✅ config+summary | run_single_task 结束后写入 config + summary（训练在外部进程）。 |

## 与 official repo 的对应

- **SEAL**：baseline/Parameter_Policy/SEAL/few-shot/arclib/update_model.py
- **RAGEN**：baseline/Parameter_Policy/RAGEN/
- **SOAR**：baseline/Parameter_Policy/SOAR/（training/train_unsloth.py 等）
- **Discover**：对应 baseline 中 Discover 的 TTT 与 advantage 设计
- **GENOME**：baseline/Parameter_Policy/GENOME/
- **ThetaEvolve**：baseline/Parameter_Policy/ThetaEvolve/

训练超参在 `training_config.json` 的 `method_params`（或根字段）中，可与 official 脚本/配置对比。
