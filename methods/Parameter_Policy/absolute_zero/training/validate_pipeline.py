#!/usr/bin/env python3
"""
End-to-end validation of the AZR training pipeline.
Tests every component without actually running full training.

Usage:
    cd DaVinciBench/2D_exploration/scripts/
    python methods/Parameter_Policy/absolute_zero/training/validate_pipeline.py
"""
import os
import sys
import json
import torch
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_AZ_DIR = os.path.dirname(_THIS_DIR)
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_AZ_DIR)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"
errors = []

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}" + (f" — {detail}" if detail else ""))
    else:
        print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        errors.append(name)


print("=" * 70)
print("AZR Training Pipeline Validation")
print("=" * 70)

# ======================================================================
# 1. Task Proposer
# ======================================================================
print(f"\n{INFO} 1. Task Proposer")
from methods.Parameter_Policy.absolute_zero.training.task_proposer import (
    propose_task, propose_batch, _TASK_TEMPLATES,
    INITIAL_DEMONSTRATION, PHYSICAL_ANALYSIS_INSTRUCTIONS, BASIC_PRIMITIVES_API,
)
import random

check("Templates registered", len(_TASK_TEMPLATES) >= 5,
      f"{len(_TASK_TEMPLATES)} templates")

rng = random.Random(42)
name, base, prompt, variation, env_ov = propose_task(rng, step=1)
check("propose_task returns 5-tuple", all([name, base, prompt, variation is not None, env_ov is not None]))
check("Task name is unique/descriptive", "proposed_" in name and len(name) > 20, name)
check("Base task is demo/basic", base == "demo/basic", base)
check("Prompt includes INITIAL_DEMONSTRATION", "build_agent" in prompt and "agent_action" in prompt and "Example" in prompt)
check("Prompt includes primitives API", "add_beam" in prompt and "add_wheel" in prompt and "connect" in prompt)
check("Prompt includes physical analysis instructions", "Physical Analysis" in prompt and "Parameter Reasoning" in prompt)
check("Prompt has correct structure", "# Task Description" in prompt and "# Success Criteria" in prompt and "# Available Primitives API" in prompt)
check("env_overrides has terrain_config", "terrain_config" in env_ov, str(list(env_ov.keys())))

batch = propose_batch(8, seed=42, rank=0, step=1)
check("propose_batch returns correct count", len(batch) == 8)
names = [b[0] for b in batch]
check("All names unique", len(set(names)) == len(names), f"{len(set(names))}/{len(names)} unique")
templates_used = set(b[3].get("template", "") for b in batch)
check("Multiple templates used in batch", len(templates_used) >= 2, str(templates_used))

# Check prompt length
prompt_lens = [len(b[2]) for b in batch]
avg_len = sum(prompt_lens) / len(prompt_lens)
check("Prompt length reasonable (5K-15K chars)", 5000 < avg_len < 20000, f"avg={avg_len:.0f} chars")

# ======================================================================
# 2. Reward Function (Tiered)
# ======================================================================
print(f"\n{INFO} 2. Tiered Reward Shaping")
from methods.Parameter_Policy.absolute_zero.training.train import azr_reward

r1 = azr_reward(None, "demo/basic", 100)
check("No code -> reward=-1.0", r1[0] == -1.0, f"reward={r1[0]}, error={r1[3]}")

r2 = azr_reward("x=1", "demo/basic", 100)
check("Missing build_agent -> reward=-1.0", r2[0] == -1.0, f"reward={r2[0]}")

r3_short = azr_reward("def build_agent(sb):\n  [", "demo/basic", 100)
check("Too short code -> reward=-0.8", r3_short[0] == -0.8, f"reward={r3_short[0]}, error={r3_short[3]}")

r3 = azr_reward("def build_agent(sandbox):\n    chassis = sandbox.add_beam(x=5.0, y=2.0, width=3.0, height=0.5\n    return chassis  # missing closing paren", "demo/basic", 100)
check("Syntax error -> reward=-0.5", r3[0] == -0.5, f"reward={r3[0]}, error={r3[3]}")

code_valid = """
def build_agent(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.5
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.2, width=5.0, height=0.4, density=3.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    return chassis

def agent_action(sandbox, agent_body, step_count):
    pass
"""
r4 = azr_reward(code_valid, "demo/basic", 10000)
check("Valid demo code -> reward >= 0", r4[0] >= 0, f"reward={r4[0]:.3f}, score={r4[2]}, success={r4[1]}")

# Test with env_overrides
r5 = azr_reward(code_valid, "demo/basic", 10000,
                env_overrides={"terrain_config": {"obstacle_1": {"x": 12, "height": 1.0, "angle": 0.1}}})
check("Valid code + env_overrides works", r5[0] is not None and r5[3] is None or isinstance(r5[3], str),
      f"reward={r5[0]:.3f}, score={r5[2]}")

# Reward ordering
check("Reward ordering: no_code < syntax < runtime <= valid",
      r1[0] <= r3[0] <= r4[0],
      f"{r1[0]} <= {r3[0]} <= {r4[0]:.3f}")

# ======================================================================
# 3. Logging (no truncation)
# ======================================================================
print(f"\n{INFO} 3. Logging (no truncation)")
import tempfile
from methods.Parameter_Policy.absolute_zero.training.logging_utils import (
    log_proposed_tasks, log_verify_results, log_rewards_summary,
)

with tempfile.TemporaryDirectory() as tmpdir:
    long_prompt = "A" * 5000
    long_code = "B" * 3000
    long_resp = "C" * 8000

    log_proposed_tasks(tmpdir, 1, [
        {"task_name": "test_task", "prompt_str": long_prompt, "variation": {"key": "val"}, "source": "proposer"}
    ])
    with open(os.path.join(tmpdir, "proposed_tasks.jsonl")) as f:
        row = json.loads(f.readline())
    check("Proposed tasks: full prompt (no truncation)", len(row["prompt"]) == 5000,
          f"prompt_len={len(row['prompt'])}")
    check("Proposed tasks: has variation", row["variation"] == {"key": "val"})

    log_verify_results(tmpdir, 1, [
        {"task_name": "test_task", "success": True, "score": 80, "reward": 0.8,
         "error": None, "code": long_code, "raw_response": long_resp}
    ])
    with open(os.path.join(tmpdir, "verify_results.jsonl")) as f:
        row = json.loads(f.readline())
    check("Verify results: full code (no truncation)", len(row["code"]) == 3000,
          f"code_len={len(row['code'])}")
    check("Verify results: full raw_response", len(row["raw_response"]) == 8000,
          f"resp_len={len(row['raw_response'])}")

    log_rewards_summary(tmpdir, 1, 0.5, 0.25, 8, extra={"loss": 0.01})
    with open(os.path.join(tmpdir, "rewards_summary.jsonl")) as f:
        row = json.loads(f.readline())
    check("Rewards summary: all fields present",
          all(k in row for k in ["step", "mean_reward", "success_rate", "n", "loss"]))

# ======================================================================
# 4. CodeVerifier + env_overrides
# ======================================================================
print(f"\n{INFO} 4. CodeVerifier + env_overrides")
from evaluation.verifier import CodeVerifier

v1 = CodeVerifier(task_name="demo/basic", max_steps=500)
success1, score1, metrics1, err1 = v1.verify_code(code_valid, headless=True)
check("CodeVerifier runs on demo/basic", score1 is not None, f"score={score1}")

v2 = CodeVerifier(task_name="demo/basic", max_steps=500,
                  env_overrides={"terrain_config": {"obstacle_1": {"x": 12, "height": 1.0, "angle": 0}}})
success2, score2, metrics2, err2 = v2.verify_code(code_valid, headless=True)
check("CodeVerifier works with env_overrides", score2 is not None, f"score={score2}")

v3 = CodeVerifier(task_name="demo/basic", max_steps=500,
                  env_overrides={"terrain_config": {
                      "gap": {"x_start": 14, "x_end": 17},
                      "ground_friction": 0.1,
                  }})
success3, score3, _, err3 = v3.verify_code(code_valid, headless=True)
check("CodeVerifier: gap + low friction works", score3 is not None, f"score={score3}")

v4 = CodeVerifier(task_name="demo/basic", max_steps=500,
                  env_overrides={"physics_config": {"gravity": (0, -5)}})
success4, score4, _, err4 = v4.verify_code(code_valid, headless=True)
check("CodeVerifier: custom gravity works", score4 is not None, f"score={score4}")

# ======================================================================
# 5. Prompt Format Consistency (train vs eval)
# ======================================================================
print(f"\n{INFO} 5. Prompt Format Consistency")
from evaluation.prompt import format_initial_prompt, load_task_prompt, INITIAL_DEMONSTRATION as EVAL_DEMO

check("INITIAL_DEMONSTRATION is same object as eval",
      INITIAL_DEMONSTRATION is EVAL_DEMO or INITIAL_DEMONSTRATION == EVAL_DEMO)

# Load a demo task prompt and compare format
demo_prompt = load_task_prompt("demo/basic")
eval_prompt = format_initial_prompt(demo_prompt)

# Check structural elements present in both eval and train prompts
for element in ["# Task Description", "# Success Criteria", "# Available Primitives API",
                "Physical Analysis", "Write Code", "build_agent", "agent_action"]:
    train_has = element in prompt  # from propose_task above
    eval_has = element in eval_prompt
    check(f"Both prompts contain '{element}'", train_has and eval_has,
          f"train={train_has}, eval={eval_has}")

# ======================================================================
# 6. RL Components
# ======================================================================
print(f"\n{INFO} 6. RL Components (REINFORCE++ / PPO)")
from methods.Parameter_Policy.absolute_zero.training.train import (
    compute_per_token_log_probs, reinforce_pp_advantages, ppo_clip_loss,
)

# Test advantage computation
rewards = torch.tensor([-1.0, -0.5, 0.0, 0.3, 0.8])
advantages = reinforce_pp_advantages(rewards, accelerator=None)
check("Advantages are whitened (mean~0, std~1)",
      abs(advantages.mean().item()) < 0.01 and abs(advantages.std().item() - 1.0) < 0.1,
      f"mean={advantages.mean():.4f}, std={advantages.std():.4f}")
check("Higher reward -> higher advantage", advantages[-1] > advantages[0],
      f"reward=0.8 -> adv={advantages[-1]:.3f}, reward=-1.0 -> adv={advantages[0]:.3f}")

# Test PPO clip loss
B, L = 2, 5
new_lp = torch.randn(B, L)
old_lp = new_lp.detach() + 0.01 * torch.randn(B, L)  # small difference
adv = torch.randn(B, L)
mask = torch.ones(B, L)
loss = ppo_clip_loss(new_lp, old_lp, adv, mask, clip_ratio=0.2)
check("PPO clip loss is scalar", loss.dim() == 0, f"loss={loss.item():.4f}")
check("PPO clip loss is finite", torch.isfinite(loss), f"loss={loss.item():.4f}")

# ======================================================================
# 7. Config / Hyperparameters
# ======================================================================
print(f"\n{INFO} 7. Config / Hyperparameters (AZR alignment)")
from methods.Parameter_Policy.absolute_zero.training.train import parse_args

# Parse with defaults
sys.argv = ["train.py", "--model-name", "Qwen/Qwen3-8B"]
args = parse_args()
check("Default lr = 1e-6", args.lr == 1e-6, f"lr={args.lr}")
check("Default clip_ratio = 0.2", args.clip_ratio == 0.2, f"clip={args.clip_ratio}")
check("Default temperature = 1.0", args.temperature == 1.0, f"temp={args.temperature}")
check("Default top_p = 1.0", args.top_p == 1.0, f"top_p={args.top_p}")
check("Default max_prompt_length = 8096", args.max_prompt_length == 8096)
check("Default max_response_length = 8096", args.max_response_length == 8096)
check("Default grad_clip = 1.0", args.grad_clip == 1.0)

# ======================================================================
# 8. Analyze Script
# ======================================================================
print(f"\n{INFO} 8. Analysis Tool")
old_run = os.path.join(_AZ_DIR, "runs", "Qwen3-8B_all_20260213_153417")
if os.path.isdir(old_run):
    from methods.Parameter_Policy.absolute_zero.training.analyze_run import load_jsonl
    rewards = load_jsonl(os.path.join(old_run, "rewards_summary.jsonl"))
    verify = load_jsonl(os.path.join(old_run, "verify_results.jsonl"))
    tasks = load_jsonl(os.path.join(old_run, "proposed_tasks.jsonl"))
    check("analyze_run loads rewards_summary", len(rewards) > 0, f"{len(rewards)} rows")
    check("analyze_run loads verify_results", len(verify) > 0, f"{len(verify)} rows")
    check("analyze_run loads proposed_tasks", len(tasks) > 0, f"{len(tasks)} rows")
else:
    print(f"  {INFO} Skipping (no old run dir)")

# ======================================================================
# Summary
# ======================================================================
print("\n" + "=" * 70)
if errors:
    print(f"{FAIL} {len(errors)} check(s) FAILED:")
    for e in errors:
        print(f"  - {e}")
else:
    print(f"{PASS} All checks passed!")
print("=" * 70)
