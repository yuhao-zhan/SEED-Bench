# Memory Methods: Alignment with DaVinciBench/baseline/Memory

本文档对照 `DaVinciBench/baseline/Memory` 下各官方实现，逐项说明 2D_exploration 中各方法的**符合点**与**已知差异**。

---

## 1. Rememberer (RLEM)

**Baseline**: `baseline/Memory/Rememberer` — RL + experience memory (YAML history pool)，训练阶段更新 Q 表，**测试阶段只读**；Exemplar 格式为 Encouraged / Discouraged（由 Q 值驱动）。

| 维度 | 官方 | 2D_exploration | 符合？ |
|------|------|----------------|--------|
| 测试时只读 | ✓ 不调用 update | ✓ 不更新 memory | ✓ |
| 检索依据 | Matcher（DenseInsMatcher / PagePatMatcher）按 state 相似度 | DenseInsMatcher，query = task_description + last_feedback | ✓ 同思路 |
| Exemplar 格式 | Encouraged / Discouraged（Q 值高/低） | Encouraged / Discouraged（reward ≥ threshold / &lt; threshold） | ✓ |
| 数据来源 | 训练阶段在训练任务上跑出的 history pool (YAML) | 来自 evaluation_results_scratch 的 baseline 轨迹，转成 rollout 格式后加载 | ⚠️ 适配：无独立“训练阶段”，用已有轨迹当只读 memory |

**结论**: 与官方「测试时只读 + 相似度检索 + Encouraged/Discouraged 格式」一致；2D 用“预跑轨迹”替代“先训好 experience memory”，属合理适配。

---

## 2. ExpeL

**Baseline**: `baseline/Memory/ExpeL` — 三阶段：Experience Gathering → Insight Extraction（LLM 从成功轨迹提炼 rules）→ 测试时按 task/thought 相似度检索 rules 作 few-shot。

| 维度 | 官方 | 2D_exploration | 符合？ |
|------|------|----------------|--------|
| 检索 | vectorstore.similarity_search(query, k) | 按 task+feedback 相似度检索 rule_strings，格式化为 prompt | ✓ |
| 存储内容 | 提取后的 rule/insight 条目 | 从 insights.json 或 rollout 数据加载 rules；pair-based 时用单任务单 env 的轨迹 | ✓ |
| 训练/提取阶段 | 有独立 train + insight extraction | **无**：假设 rules 已由外部流程写好（或从 rollout 目录读） | ⚠️ 简化：未复现官方「先 gather 再 extract」pipeline |

**结论**: 测试时「按 query 检索 rule 并注入 prompt」与官方一致；2D 未实现官方的 experience gathering + insight extraction 阶段，需事先准备好 rules/insights（见 `EXPEL_ON_DAVINCIBENCH.md`）。

---

## 3. ReasoningBank

**Baseline**: 无开源代码，仅论文 (arXiv:2509.25140) 与 `baseline/Memory/ReasoningBank/github_reference.txt` 描述。核心：成功/失败轨迹 → 蒸馏 (title, description, content) → 检索注入；可选 MaTTS（parallel K 轨迹等）。

| 维度 | 论文/文档 | 2D_exploration | 符合？ |
|------|-----------|----------------|--------|
| 记忆项结构 | title, description, content | ✓ 同结构，JSONL 存储 | ✓ |
| 检索 | embedding 相似度 top-k | retrieve_for_prompt(task_description + last_feedback, bank_items)，Sup-SimCSE | ✓ |
| 存储时机 | 每轮/每轨迹后 extract → consolidate | 每轮 extract_memory_items_llm（或 fallback）→ store_after_iteration | ✓ |
| Success 判定 | LLM-as-judge 或类似 | judge_success_llm()：有 API 时用 LLM 判 success，否则 fallback 到 score/success | ✓ 已对齐 |
| MaTTS | parallel K 轨迹 + self-contrast + distill | reasoning_bank_k>1 时每轮生成 K 条、验证 K 条、contrast_and_distill 后取 best，并写入 bank | ✓ 已对齐 |

**结论**: 单轨迹下的「retrieve → 生成 → extract → store」与论文一致；MaTTS 与 LLM-as-judge 未实现，属简化版。

---

## 4. Memento (no_parametric)

**Baseline**: `baseline/Memory/Memento/client/no_parametric_cbr.py` + `memory/np_memory.py`。用 `load_jsonl` / `extract_pairs` / `retrieve`（Sup-SimCSE）；`build_prompt_from_cases` 按 **reward==1** 分 positive/negative。

| 维度 | 官方 | 2D_exploration | 符合？ |
|------|------|----------------|--------|
| 加载 | load_jsonl(path) → items；extract_pairs(items, key_field, value_field) → pairs | load_memory(path) 调 baseline 的 load_jsonl + extract_pairs，MEMORY_KEY_FIELD / MEMORY_VALUE_FIELD = task_description / code | ✓ |
| 检索 | memory.np_memory.retrieve(task, pairs, tokenizer, model, top_k, max_length) | 同：query = task_description + last_feedback，调 mem_retrieve，返回 list[dict] 含 question, plan, line_index | ✓ |
| Prompt 构建 | build_prompt_from_cases：reward==1 为 positive，否则 negative | build_prompt_from_cases_2d：reward ≥ REWARD_POSITIVE_THRESHOLD (0.5) 为 positive | ⚠️ 官方为二值 reward=1；2D 用 score/100 与 0.5 阈值，适配连续分数 |
| 存储 | 无在 no_parametric 脚本内写 JSONL 的明确片段（案例来自预填 memory） | store_after_iteration 追加：task_description, code, feedback, reward (1.0 或 score/100) | ✓ 2D 显式实现“每轮写入” |

**结论**: 检索与 prompt 结构（positive/negative examples）与官方一致；仅 positive 判定从「reward==1」改为「reward≥0.5」，以适配 0–100 分数。

---

## 5. A-mem-sys

**Baseline**: `baseline/Memory/A-mem-sys/agentic_memory/memory_system.py`。AgenticMemorySystem：`add_note(content)`（内部 LLM 分析 keywords/context/tags）、ChromaDB、`find_related_memories(query, k=5)` 返回 (formatted_str, ids)；周期性 `consolidate_memories`（evo_threshold）。

| 维度 | 官方 | 2D_exploration | 符合？ |
|------|------|----------------|--------|
| add_note | content + LLM analyze_content → keywords, context, tags → process_memory → ChromaDB | 直接 add_note(content)，content 为「Past attempt \| Task \| Iter \| Score + Code + Feedback」 | ✓ 接口一致；⚠️ 2D 未调用 LLM 分析，无 keywords/context/tags 增强 |
| find_related_memories | query, k=5 → (formatted_memory_string, memory_ids) | retrieve_for_prompt(..., k=5) 调 find_related_memories(query, k)，只取 memory_str | ✓ |
| 存储格式 | MemoryNote + metadata（timestamp, context, tags…） | 存纯文本 content，metadata 由 A-mem-sys 内部默认/分析生成 | ✓ |
| consolidate_memories | evo_cnt % evo_threshold == 0 时触发 | **未调用** | ⚠️ 无周期性 evolution/consolidation |

**结论**: 检索与 add_note 用法与官方一致；2D 未做「LLM 分析 content」和「按 evo_threshold 做 consolidate_memories」，为简化版。

---

## 6. ACE

**Baseline**: `baseline/Memory/ace/ace/ace.py`。Generator（带 playbook）→ Reflector.reflect(question, reasoning_trace, predicted_answer, environment_feedback, bullets_used) → update_bullet_counts(playbook, bullet_tags) → Curator.curate(current_playbook, recent_reflection, ..., token_budget, playbook_stats, next_global_id)。

| 维度 | 官方 | 2D_exploration | 符合？ |
|------|------|----------------|--------|
| Playbook 初始化 | _initialize_empty_playbook() 或传入 initial_playbook | get_initial_playbook()（同空模板）+ initial_playbook 恢复（mutation） | ✓ |
| 每轮生成 | Generator 的 prompt 内含**完整 playbook** | 将「## Current Playbook」+ playbook 以 memory_block 形式注入 revision prompt | ✓ 等价：模型每轮看到完整 playbook |
| Reflector | reflect(..., bullets_used) | 从 raw_output 解析 bullet_ids（JSON 中的 bullet_ids），extract_playbook_bullets(playbook, bullet_ids) 作为 bullets_used 传入 | ✓ 已对齐：prompt 要求输出 JSON 含 bullet_ids+code，解析后传 Reflector |
| Curator | curate(current_playbook, recent_reflection, question_context, current_step, total_samples, token_budget, playbook_stats, ..., next_global_id) | update_playbook_after_iteration(..., token_budget=8000, ...) 内部调 update_bullet_counts + curator.curate | ✓ 参数与流程一致；token_budget 用 8000（官方 run 默认 80000，可按需调） |
| 保存 | final_playbook / best_playbook 写文件 | report['final_playbook'] = self._ace_playbook，供 mutation 恢复 | ✓ |

**结论**: Reflect → update_bullet_counts → Curate 流程与官方一致；唯一差异为 bullets_used 未从 Generator 输出解析（2D 用 SolverInterface 生成代码，无 ACE bullet 标注），属合理适配。

---

## 汇总表

| 方法 | 与官方一致点 | 已知差异/简化 |
|------|--------------|-------------------------------|
| **Rememberer** | 只读检索、DenseInsMatcher、Encouraged/Discouraged 格式 | 无训练阶段，用预跑轨迹当 memory |
| **ExpeL** | 按 query 检索 rule 并注入 prompt | 无 experience gathering + insight extraction，需预填 rules |
| **ReasoningBank** | (title,description,content)、检索、每轮 extract+store | 无 LLM-as-judge、无 MaTTS parallel K |
| **Memento** | np_memory.load/extract/retrieve、positive/negative prompt | positive 判定为 reward≥0.5 而非 reward==1 |
| **A-mem-sys** | add_note、find_related_memories、k=5 | 无 add_note 的 LLM 分析、无 consolidate_memories |
| **ACE** | playbook 注入、Reflector→Curator、token_budget/curate 参数 | bullets_used=""（无 ACE Generator 的 bullet_ids）；token_budget=8000 |

以上差异均为在 2D_exploration 评估管线下的**有意适配或简化**，核心「检索/存储/注入」行为与官方设计一致。若需完全对齐某一条（如 ExpeL 的提取阶段、A-mem-sys 的 consolidation），需在对应 `*_method.py` 与 `evaluate.py` 中按 baseline 补全逻辑。
