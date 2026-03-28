# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DaVinciBench is a physics-based reasoning benchmark. AI agents generate mechanism designs (Python code) that are executed in a Box2D sandbox environment to solve physical reasoning tasks. Each task requires building an agent with specific primitives (beams, wheels, joints) to achieve an objective (reach a position, balance forces, etc.).

## Architecture

### Tasks (`tasks/`)
Each task category is a directory containing task variants (e.g., `S_01`, `K_02`). Each task contains:
- `agent.py` - `build_agent(sandbox)` and `agent_action(sandbox, agent_body, step_count)` functions
- `environment.py` - Physics environment configuration (Box2D world setup)
- `evaluator.py` - Success criteria and scoring
- `renderer.py` - Visualization
- `prompt.py` - Task-specific prompt additions
- `stages.py` - Environment stages for cross-mutation evaluation
- `test_*.py` - Test scripts

**Task Categories** (category prefixes in task names):
- `Category1_Statics_Equilibrium` / `S_XX` - Structural stability tasks
- `Category2_Kinematics_Linkages` / `K_XX` - Mechanical linkage tasks
- `Category3_Dynamics_Energy` / `D_XX` - Energy and momentum tasks
- `Category4_Granular_FluidInteraction` / `F_XX` - Fluid/granular physics tasks
- `Category5_Cybernetics_Control` / `C_XX` - Control system tasks
- `Category6_ExoticPhysics` / `E_XX` - Unusual physics scenarios

### Methods (`methods/`)
Agent/memory methods that wrap the base evaluation loop:
- `Context/` - reflexion, self_refine, textgrad (revision-based methods)
- `Memory/` - rememberer, expel, reasoning_bank, memento_nonparametric, a_mem_sys, ace (memory-augmented methods)
- `Inference_time_search/` - Tree-of-Thought style search
- `Parameter_Policy/` - Training-based methods: genome, theta_evolve, discover, ragen, seal, soar, absolute_zero

### Evaluation (`evaluation/`)
- `evaluate.py` - Single-task from-scratch evaluation
- `evaluate_mutated.py` - Sequence-based mutation evaluation
- `evaluate_cross_mutated.py` - Pair-based cross-mutation (source_env → target_env)
- `prompt.py` - Prompt formatting templates
- `verifier.py` - Executes agent code in sandbox, checks success
- `solver_interface.py` - LLM API calls (OpenAI, Anthropic, Google, vLLM)
- `utils.py` - Task resolution, path helpers, max_steps calculation
- `run_evaluate_parallel.py` - Parallel multi-task launcher

### Common (`common/`)
- `simulator.py` - Box2D physics engine wrapper (PPM=40 pixels/meter, 60 FPS)
- `renderer.py` - pygame-based visualization and GIF generation

## Running Tasks

### Run a single task test (from task directory):
```bash
python tasks/Category1_Statics_Equilibrium/S_01/test_agent.py
```

### Run parallel evaluation:
```bash
python evaluation/run_evaluate_parallel.py --task <spec> --model_type <type> --model_name <name> --method <method>
```
Task specs: `all`, `category_1`, `category_2_01`, `Category1_Statics_Equilibrium/S_01`

### Run audit (generates audit reports):
```bash
./auto_audit.sh --task <spec>
./auto_audit.sh --task category_1 --start_from S_03  # start from specific task
```

### Run feedback iteration:
```bash
./auto_feedback.sh --task <spec>
```

### Available methods for evaluation:
`baseline`, `sys_feedback`, `reflexion`, `textgrad`, `self_refine`, `self_refine_inner_only`, `rememberer`, `expel`, `reasoning_bank`, `memento_nonparametric`, `ace`, `tree_of_thought`, `theta_evolve`, `soar`, `ragen`, `discover`, `seal`, `genome`, `absolute_zero_iter`

## Sandbox Primitives API

Available in `tasks/primitives_api.py`. Key primitives:
- `sandbox.add_beam(x, y, width, height, angle, density)` / `add_block()` / `add_wheel()` / `add_static_beam()` - Create bodies
- `sandbox.connect(body_a, body_b, anchor_x, anchor_y, motor_speed, max_torque)` - Create joints
- `sandbox.apply_force(body, force_x, force_y, point_x, point_y)` - Apply forces
- Body state: `body.position`, `body.linearVelocity`, `body.angle`, `body.angularVelocity`

## Cross-Mutation Evaluation

Cross-mutation tests generalization: an agent built for one environment stage is evaluated on another. Stage mappings are defined in `tasks/*/stages.py` and loaded via `evaluation.evaluate_cross_mutated.get_all_stages()`.

## Key Files for Each Task Type

- Adding a new task: Create directory under `tasks/CategoryX_*` with `agent.py`, `environment.py`, `evaluator.py`, `renderer.py`
- Adding a new method: Create module under `methods/` and wire into `evaluation/evaluate.py`
- Adding new task stages: Edit `stages.py` in the task directory

## Context Compaction Priority

When Claude Code's context window fills and automatic compaction occurs, preserve information in this order:

1. Architecture decisions and constraint rationale
2. Modified files (agent.py, evaluator.py, environment.py, feedback.py)
3. Validation/test state and pass/fail status
4. TODO items and remaining violations
5. Tool outputs (can be re-read from logs)

## Git Session Management

**This is mandatory at the end of every session.**

### End-of-Session Checklist
1. Run `git status` to see what changed
2. Stage meaningful changes: `git add <files>` (NOT `git add .`)
3. Commit with a **descriptive message** following this format:
   ```
   <area>: <what changed> — <why>

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   ```
   Examples:
   - `harness: add HANDOFF.md generation to auto_audit.sh`
   - `benchmark: fix joint breaking logic in S_01 evaluator`
   - `memory: add user_preferences.md with code style rules`
4. Update `.claude/PROGRESS.md` — add the commit to the Recent Commits table

### If Changes Break Something
1. **Do NOT keep iterating** — git stash or git reset --hard to last known good commit
2. Identify which specific change caused the breakage via `git bisect` or `git log -p`
3. Revert only the problematic part, then re-run tests
4. This is the "后悔药" — use it freely, not as last resort

### Commit Message Rules
- `<area>`: directory or module name (e.g., `harness`, `benchmark`, `tasks/S_01`)
- `<what>`: specific change (e.g., `add HANDOFF.md generation`)
- `<why>`: motivation (e.g., `to enable cross-session continuity`)
- Never commit with message like "fix" or "update" — be specific
- New files in `.claude/` are always meaningful — always commit them
