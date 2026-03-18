"""
AZR-style task proposer: generates diverse 2D physics tasks for self-play training.

Aligned with official AZR (README + paper): the model can **propose** tasks from a reference.

Modes:
  1. **Concrete task + LLM propose (--llm-propose)**: Given base_task_name (e.g. category_1_01),
     the **LLM** is given the reference task and its curriculum stages and generates a
     related variation (JSON: terrain_config / physics_config). Matches official
     "reference snippets → model generates new task". Fallback: programmatic stage sample if parse fails.
  2. **Concrete task, no LLM**: Sample from the task's curriculum stages (Initial, Stage-1, ...).
  3. **Template fallback (--task all)**: Hand-written templates; no benchmark data.

When evaluating S_01 (e.g. initial, stage-1 pair), use concrete task = category_1_01 for proposal.
"""
import json
import os
import sys
import random
import hashlib
import re
import importlib.util
from typing import Dict, Any, List, Tuple, Optional, Callable

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Import the same demonstrations used in evaluation (NOT test data)
from evaluation.prompt import INITIAL_DEMONSTRATION, load_task_prompt, parse_task_name, format_initial_prompt

# ---------------------------------------------------------------------------
# Shared prompt components (identical to evaluation format)
# ---------------------------------------------------------------------------

PHYSICAL_ANALYSIS_INSTRUCTIONS = """\
# Your Task

You are designing a physical system in a 2D physics simulation. Before writing code, you MUST reason through the physical design.

## Step 1: Physical Analysis (Required)

1. **Understand the Physics**: What physical principles govern this task? (equilibrium, kinematics, dynamics, energy, fluid interaction, etc.)

2. **Design Strategy**: How will your structure/mechanism achieve the goal? What is the key physical insight?

3. **Parameter Reasoning**: Estimate key parameters (dimensions, masses, forces, speeds) based on physical reasoning.

## Step 2: Write Code

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions

**Output Format**:

```python
def build_agent(sandbox):
    # Your implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your physical analysis, then provide the code.
"""

BASIC_PRIMITIVES_API = """\
## Available Primitives API

### 1. Add Chassis (Beam/Chassis)
```python
chassis = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Chassis center position (meters)
- `width, height`: Chassis dimensions (meters), height cannot exceed 1.0m
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, range 0-10)
- Returns: Chassis body object

### 2. Add Wheel
```python
wheel = sandbox.add_wheel(x, y, radius, density=1.0, friction=0.8)
```
- `x, y`: Wheel center position (meters)
- `radius`: Wheel radius (meters, range [0.3, 2.0])
- `density`: Density (kg/m³, range 0-10)
- `friction`: Friction coefficient (range [0, 5])
- Returns: Wheel body object
- **Important**: Ground top is at **y=1.0m**. Wheel center y = 1.0 + radius.
- **Constraint**: Maximum 2 wheels allowed

### 3. Connect Components (Joint/Actuator)
```python
joint = sandbox.connect(body_a, body_b, anchor_x, anchor_y, motor_speed=0.0, max_torque=0.0)
```
- `body_a, body_b`: Two body objects to connect
- `anchor_x, anchor_y`: Connection point position (meters)
- `motor_speed`: Motor speed (rad/s, range [-50, 50])
- `max_torque`: Maximum torque (N·m, range [0, 2000])
- Returns: Joint object

### 4. Validate Design
```python
is_valid, errors = sandbox.validate_design(chassis)
```
"""

# ---------------------------------------------------------------------------
# Task templates — diverse physics scenarios using the basic sandbox API
# Each template is a function: (rng) -> (task_name, task_description, success_criteria, env_overrides)
# ---------------------------------------------------------------------------

_TASK_TEMPLATES: List = []


def _register(fn):
    _TASK_TEMPLATES.append(fn)
    return fn


@_register
def _obstacle_course(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle must traverse terrain with varied obstacles."""
    n_obs = rng.randint(1, 3)
    obstacles = []
    for i in range(n_obs):
        x = rng.uniform(8 + i * 8, 12 + i * 8)
        h = rng.uniform(1.0, 4.5)
        a = rng.uniform(-0.5, 0.5)
        obstacles.append({"x": round(x, 1), "height": round(h, 1), "angle": round(a, 2)})
    target_x = round(rng.uniform(25, 35), 0)
    friction = round(rng.uniform(0.3, 1.5), 2)
    grav_y = round(rng.uniform(-14, -7), 1)

    obs_lines = "\n".join(
        f"  - Obstacle {i+1}: Position x={o['x']}m, height {o['height']}m, angle {o['angle']} rad"
        for i, o in enumerate(obstacles)
    )
    name = f"obstacle_course_{n_obs}obs_target{int(target_x)}"

    desc = f"""\
You need to design a vehicle that can traverse an obstacle course in DaVinci Sandbox.

## Task Environment
- Start position: x=5.0m
- Target position: x={target_x}m
- Gravity: (0, {grav_y}) m/s²
- Terrain:
  - **Ground**: width 50m, **ground top at y=1.0m**, friction={friction}
{obs_lines}

## Task Objective
Design a vehicle that can:
1. Move stably on terrain
2. Pass all {n_obs} obstacle(s)
3. Reach x={target_x}m

## Constraints
- Chassis height ≤ 1.0m
- Wheel radius ∈ [0.3, 2.0]m
- Max 2 wheels
- Motor speed ∈ [-50, 50] rad/s
- Max torque ≤ 2000 N·m
"""
    criteria = f"""\
## Success Criteria
- **Primary**: Chassis reaches x={target_x}m
- **Fail**: Falls off map (y < -10), moves backward > 5m, angular velocity > 2.0 rad/s, altitude > 8.0m
- **Score**: 100 (success), 0-80 (partial by distance), 0 (fail)
"""
    # Build env_overrides for demo/basic
    ov: Dict[str, Any] = {
        "terrain_config": {"ground_friction": friction},
        "physics_config": {"gravity": (0, grav_y)},
    }
    if len(obstacles) >= 1:
        ov["terrain_config"]["obstacle_1"] = obstacles[0]
    if len(obstacles) >= 2:
        ov["terrain_config"]["obstacle_2"] = obstacles[1]
    return name, desc, criteria, ov


@_register
def _steep_climb(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle must climb very steep terrain."""
    angle1 = round(rng.uniform(0.3, 0.8), 2)
    angle2 = round(rng.uniform(0.4, 0.9), 2)
    h1 = round(rng.uniform(2.0, 5.0), 1)
    h2 = round(rng.uniform(3.0, 6.0), 1)
    name = f"steep_climb_a{int(angle1*100)}_{int(angle2*100)}"
    desc = f"""\
You need to design a heavy-duty vehicle that can climb steep slopes in DaVinci Sandbox.

## Task Environment
- Start position: x=5.0m
- Target position: x=30.0m
- Terrain:
  - **Ground**: width 50m, ground top at y=1.0m
  - Steep ramp 1: x=12m, height {h1}m, angle {angle1} rad (very steep!)
  - Steep ramp 2: x=22m, height {h2}m, angle {angle2} rad (extremely steep!)

## Task Objective
Design a vehicle with enough torque and traction to climb steep inclines.

## Constraints
- Chassis height ≤ 1.0m, wheel radius ∈ [0.3, 2.0]m, max 2 wheels
- Motor speed ∈ [-50, 50] rad/s, max torque ≤ 2000 N·m
"""
    criteria = """\
## Success Criteria
- **Primary**: Chassis reaches x=30.0m
- **Fail**: Falls off map, moves backward > 5m, unstable (angular velocity > 2.0 rad/s)
- **Score**: 100 (success), 0-80 (partial), 0 (fail)
"""
    ov = {"terrain_config": {
        "obstacle_1": {"x": 12, "height": h1, "angle": angle1},
        "obstacle_2": {"x": 22, "height": h2, "angle": angle2},
    }}
    return name, desc, criteria, ov


@_register
def _gap_jump(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle must cross a gap in the ground."""
    gap_start = round(rng.uniform(12, 18), 1)
    gap_width = round(rng.uniform(2.0, 5.0), 1)
    gap_end = round(gap_start + gap_width, 1)
    obs_x = round(rng.uniform(gap_end + 3, 28), 1)
    obs_h = round(rng.uniform(1.0, 3.0), 1)
    name = f"gap_jump_{int(gap_start)}to{int(gap_end)}"
    desc = f"""\
You need to design a vehicle that can cross a gap in the terrain in DaVinci Sandbox.

## Task Environment
- Start position: x=5.0m
- Target position: x=30.0m
- Terrain:
  - **Ground**: width 50m, ground top at y=1.0m
  - **GAP**: No ground between x={gap_start}m and x={gap_end}m (width {gap_width}m) — vehicle must jump or bridge it!
  - Obstacle after gap: x={obs_x}m, height {obs_h}m

## Task Objective
Design a vehicle with enough speed and momentum to cross the gap and continue.

## Constraints
- Chassis height ≤ 1.0m, wheel radius ∈ [0.3, 2.0]m, max 2 wheels
- Motor speed ∈ [-50, 50] rad/s, max torque ≤ 2000 N·m
"""
    criteria = """\
## Success Criteria
- **Primary**: Chassis reaches x=30.0m
- **Fail**: Falls into gap (y < -10), moves backward > 5m
- **Score**: 100 (success), 0-80 (partial), 0 (fail)
"""
    ov = {"terrain_config": {
        "gap": {"x_start": gap_start, "x_end": gap_end},
        "obstacle_1": {"x": obs_x, "height": obs_h, "angle": 0},
        "obstacle_2": {"x": 35, "height": 0.1, "angle": 0},  # minimal
    }}
    return name, desc, criteria, ov


@_register
def _low_gravity(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle operates in low/high gravity."""
    grav = round(rng.uniform(-20, -4), 1)
    grav_label = "low" if abs(grav) < 8 else ("high" if abs(grav) > 12 else "normal")
    h1 = round(rng.uniform(1.5, 4.0), 1)
    h2 = round(rng.uniform(2.0, 5.0), 1)
    name = f"{grav_label}_gravity_{abs(int(grav))}"
    desc = f"""\
You need to design a vehicle for {grav_label} gravity ({grav} m/s²) in DaVinci Sandbox.

## Task Environment
- Start position: x=5.0m, Target: x=30.0m
- **Gravity: (0, {grav}) m/s²** — {"lighter than Earth!" if abs(grav) < 8 else "heavier than Earth!" if abs(grav) > 12 else "Earth-like"}
- Terrain: ground top at y=1.0m
  - Obstacle 1: x=15m, height {h1}m
  - Obstacle 2: x=25m, height {h2}m

## Task Objective
Design a vehicle that handles the unusual gravity and reaches the target.

## Constraints
- Chassis height ≤ 1.0m, wheel radius ∈ [0.3, 2.0]m, max 2 wheels
- Motor speed ∈ [-50, 50] rad/s, max torque ≤ 2000 N·m
"""
    criteria = """\
## Success Criteria
- **Primary**: Chassis reaches x=30.0m
- **Fail**: Falls off map, backward > 5m, unstable
- **Score**: 100 / 0-80 partial / 0 fail
"""
    ov = {
        "terrain_config": {
            "obstacle_1": {"x": 15, "height": h1, "angle": 0},
            "obstacle_2": {"x": 25, "height": h2, "angle": 0},
        },
        "physics_config": {"gravity": (0, grav)},
    }
    return name, desc, criteria, ov


@_register
def _low_friction(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle on slippery terrain."""
    friction = round(rng.uniform(0.05, 0.3), 2)
    h1 = round(rng.uniform(1.0, 3.0), 1)
    name = f"slippery_terrain_f{int(friction*100)}"
    desc = f"""\
You need to design a vehicle for very slippery terrain (friction={friction}) in DaVinci Sandbox.

## Task Environment
- Start x=5.0m, Target x=30.0m
- Terrain: ground top y=1.0m, **ground friction = {friction}** (very low!)
  - Obstacle: x=18m, height {h1}m

## Key Challenge
Low friction means wheels slip easily. You need:
- High wheel friction to compensate
- Careful torque to avoid spinning wheels
- Possibly heavier chassis for better traction

## Constraints
- Chassis height ≤ 1.0m, wheel radius ∈ [0.3, 2.0]m, max 2 wheels
- Motor speed ∈ [-50, 50] rad/s, max torque ≤ 2000 N·m
"""
    criteria = """\
## Success Criteria
- **Primary**: Chassis reaches x=30.0m
- **Fail**: Falls off, backward > 5m, unstable
- **Score**: 100 / 0-80 partial / 0 fail
"""
    ov = {"terrain_config": {
        "ground_friction": friction,
        "obstacle_1": {"x": 18, "height": h1, "angle": 0.1},
        "obstacle_2": {"x": 26, "height": 1.0, "angle": 0},
    }}
    return name, desc, criteria, ov


@_register
def _speed_run(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle must reach a far target quickly (flat terrain, emphasis on speed)."""
    target = round(rng.uniform(35, 45), 0)
    name = f"speed_run_target{int(target)}"
    desc = f"""\
You need to design the fastest possible vehicle in DaVinci Sandbox.

## Task Environment
- Start x=5.0m, Target x={target}m
- Terrain: flat ground (top at y=1.0m), minimal obstacles
  - Small bump at x=20m, height 1.0m

## Key Challenge
Maximise forward speed. Optimise for:
- High motor speed and torque
- Low drag (streamlined shape)
- Good traction without excessive weight

## Constraints
- Chassis height ≤ 1.0m, wheel radius ∈ [0.3, 2.0]m, max 2 wheels
- Motor speed ∈ [-50, 50] rad/s, max torque ≤ 2000 N·m
"""
    criteria = f"""\
## Success Criteria
- **Primary**: Chassis reaches x={target}m
- **Score**: 100 (success), 0-80 (partial by distance), 0 (fail)
"""
    ov = {"terrain_config": {
        "obstacle_1": {"x": 20, "height": 1.0, "angle": 0},
        "obstacle_2": {"x": 40, "height": 0.5, "angle": 0},
    }}
    return name, desc, criteria, ov


@_register
def _heavy_load(rng: random.Random) -> Tuple[str, str, str, Dict]:
    """Vehicle with high density (heavy) must still traverse obstacles."""
    chassis_density = round(rng.uniform(5.0, 10.0), 1)
    h1 = round(rng.uniform(2.0, 4.0), 1)
    h2 = round(rng.uniform(2.5, 5.0), 1)
    name = f"heavy_vehicle_d{int(chassis_density)}"
    desc = f"""\
You need to design a heavy vehicle (chassis density={chassis_density} kg/m³) in DaVinci Sandbox.

## Task Environment
- Start x=5.0m, Target x=30.0m
- Terrain: ground top y=1.0m
  - Obstacle 1: x=14m, height {h1}m
  - Obstacle 2: x=24m, height {h2}m

## Key Challenge
The chassis is very heavy (density={chassis_density}). You need:
- Maximum torque to overcome the weight
- Large enough wheels for clearance
- Strong enough joints

## Constraints
- Chassis height ≤ 1.0m, wheel radius ∈ [0.3, 2.0]m, max 2 wheels
- Motor speed ∈ [-50, 50] rad/s, max torque ≤ 2000 N·m
- **Chassis density must be {chassis_density} kg/m³** (heavy!)
"""
    criteria = """\
## Success Criteria
- **Primary**: Chassis reaches x=30.0m
- **Fail**: Falls off, backward > 5m, unstable
- **Score**: 100 / 0-80 partial / 0 fail
"""
    ov = {"terrain_config": {
        "obstacle_1": {"x": 14, "height": h1, "angle": 0.2},
        "obstacle_2": {"x": 24, "height": h2, "angle": -0.2},
    }}
    return name, desc, criteria, ov


# ---------------------------------------------------------------------------
# Build full prompt from template output (matches evaluation prompt format)
# ---------------------------------------------------------------------------

def _build_full_prompt(task_desc: str, criteria: str) -> str:
    """Build prompt in the exact same format as evaluation/prompt.py's format_initial_prompt."""
    return f"""# Task Description

{task_desc}

# Success Criteria

{criteria}

# Available Primitives API

{BASIC_PRIMITIVES_API}

{INITIAL_DEMONSTRATION}

{PHYSICAL_ANALYSIS_INSTRUCTIONS}"""


# ---------------------------------------------------------------------------
# Propose from concrete task (AZR: use reference task → propose related variations)
# Related = same task in different curriculum stages (Initial, Stage-1, ...).
# ---------------------------------------------------------------------------

def _is_concrete_task_spec(spec: str) -> bool:
    """True if spec is a concrete task like category_1_01 (not category_1 or all)."""
    if not spec or not isinstance(spec, str):
        return False
    s = spec.strip().lower()
    if s in ("all", "") or s.startswith("fixed:"):
        return False
    return bool(re.match(r"^category_\d+_\d+$", s))


def _build_task_prompt_for_stage(
    base_task_name: str,
    stage: Dict[str, Any],
    base_stage: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build task_prompt (description + criteria) and env_overrides for a given stage.

    Uses the task's stages.py update_task_description_for_visible_changes and
    update_success_criteria_for_visible_changes (same as evaluation).
    Returns (task_prompt_override, env_overrides).
    """
    task_path, _ = parse_task_name(base_task_name)
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    task_dir = os.path.join(script_dir, "tasks", task_path)
    stages_file = os.path.join(task_dir, "stages.py")

    base_prompt = load_task_prompt(base_task_name)
    task_prompt_override = dict(base_prompt)
    desc = base_prompt.get("task_description", "")
    criteria = base_prompt.get("success_criteria", "")

    target_terrain = stage.get("terrain_config") or {}
    base_terrain = base_stage.get("terrain_config") or {}
    target_physics = stage.get("physics_config") or {}
    base_physics = base_stage.get("physics_config") or {}

    update_desc_func = None
    update_criteria_func = None
    if os.path.exists(stages_file):
        spec = importlib.util.spec_from_file_location("task_stages", stages_file)
        stages_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stages_mod)
        for name in dir(stages_mod):
            if "update_task_description_for_visible_changes" in name.lower() and callable(getattr(stages_mod, name)):
                update_desc_func = getattr(stages_mod, name)
            if "update_success_criteria_for_visible_changes" in name.lower() and callable(getattr(stages_mod, name)):
                update_criteria_func = getattr(stages_mod, name)

    if update_desc_func:
        try:
            import inspect
            sig = inspect.signature(update_desc_func)
            if len(sig.parameters) >= 5:
                desc = update_desc_func(desc, target_terrain, base_terrain, target_physics, base_physics)
            else:
                desc = update_desc_func(desc, target_terrain, base_terrain)
        except Exception:
            desc = update_desc_func(desc, target_terrain, base_terrain)
    if update_criteria_func:
        try:
            import inspect
            sig = inspect.signature(update_criteria_func)
            if len(sig.parameters) >= 5:
                criteria = update_criteria_func(criteria, target_terrain, base_terrain, target_physics, base_physics)
            else:
                criteria = update_criteria_func(criteria, target_terrain, base_terrain)
        except Exception:
            criteria = update_criteria_func(criteria, target_terrain, base_terrain)

    suffix = stage.get("task_description_suffix", "")
    if suffix:
        desc = desc + "\n" + suffix

    task_prompt_override["task_description"] = desc
    task_prompt_override["success_criteria"] = criteria

    env_overrides = {
        "terrain_config": dict(target_terrain),
        "physics_config": dict(target_physics),
    }
    return task_prompt_override, env_overrides


def propose_task_from_concrete_task(
    base_task_name: str,
    rng: random.Random,
    step: int = 0,
) -> Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]:
    """Propose a single related task from a concrete benchmark task (AZR: reference → variations).

    Samples one of the task's curriculum stages (Initial, Stage-1, ...) and builds
    the task prompt for that environment. Verifier will run with base_task_name + env_overrides.

    Returns:
        (task_name, base_task_name, prompt_str, variation_dict, env_overrides)
    """
    from evaluation.evaluate_cross_mutated import get_all_stages

    all_envs = get_all_stages(base_task_name)
    if not all_envs:
        raise ValueError(f"Concrete task {base_task_name!r} has no stages (get_all_stages returned empty).")

    stage = rng.choice(all_envs)
    base_stage = next((e for e in all_envs if e.get("stage_id") == "Initial"), all_envs[0])

    task_prompt_override, env_overrides = _build_task_prompt_for_stage(base_task_name, stage, base_stage)
    prompt_str = format_initial_prompt(task_prompt_override)

    stage_id = stage.get("stage_id", "Initial")
    uid = hashlib.md5(f"{base_task_name}_{stage_id}_{step}_{rng.random()}".encode()).hexdigest()[:6]
    task_name = f"proposed_{base_task_name}_{stage_id}_{uid}"

    variation = {
        "source": "concrete_task",
        "base_task_name": base_task_name,
        "stage_id": stage_id,
        "env_overrides": env_overrides,
    }
    return task_name, base_task_name, prompt_str, variation, env_overrides


# ---------------------------------------------------------------------------
# LLM-based task proposal (official AZR: model proposes tasks from reference)
# ---------------------------------------------------------------------------

PROPOSE_TASK_SYSTEM = """You are helping create training variations for a 2D physics simulation benchmark.

Your job is to propose a **related** task variation by specifying environment parameters. You will be given a reference task and its existing curriculum stages (each stage has terrain_config and physics_config). You must output a single JSON object that defines a **new** variation — either a combination inspired by the stages or a new but physically reasonable setting.

Output format: put the JSON inside a fenced block, e.g.:
```json
{"terrain_config": {...}, "physics_config": {...}}
```
- Use only keys that appear in the reference stages (e.g. gap_width, max_structure_mass, gravity, wind_force, joint_max_force, joint_max_torque, anchor_max_force, anchor_max_torque). Omit a key to keep the default.
- terrain_config and physics_config must be plain objects (no nested arrays except for gravity as [x, y]).
- Propose values that are related to the task and physically plausible."""

PROPOSE_TASK_USER_TEMPLATE = """## Reference task: {base_task_name}

### Task description (summary)
{task_description_summary}

### Existing curriculum stages (for reference; propose a NEW variation)
{stages_summary}

Propose one new related variation as a single JSON object with "terrain_config" and/or "physics_config". Output only the JSON block, no other text."""


def _stages_summary_for_proposal(base_task_name: str, all_stages: List[Dict[str, Any]]) -> str:
    """Build a short text summary of stages for the propose prompt."""
    lines = []
    for s in all_stages:
        sid = s.get("stage_id", "?")
        title = s.get("title", "")
        tc = s.get("terrain_config") or {}
        pc = s.get("physics_config") or {}
        parts = [f"- **{sid}** ({title})"]
        if tc:
            parts.append(f"  terrain_config: {json.dumps(tc)}")
        if pc:
            parts.append(f"  physics_config: {json.dumps(pc)}")
        lines.append(" ".join(parts))
    return "\n".join(lines) if lines else "(Initial only)"


def _parse_proposed_env_overrides(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extract terrain_config/physics_config from model output. Returns None if invalid."""
    if not raw_text or not isinstance(raw_text, str):
        return None
    # Prefer ```json ... ``` block
    json_block = re.search(r"```(?:json)?\s*\n?(.*?)```", raw_text, re.DOTALL)
    if json_block:
        raw_text = json_block.group(1).strip()
    else:
        raw_text = raw_text.strip()
    try:
        obj = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    terrain = obj.get("terrain_config")
    physics = obj.get("physics_config")
    if terrain is not None and not isinstance(terrain, dict):
        return None
    if physics is not None and not isinstance(physics, dict):
        return None
    return {
        "terrain_config": dict(terrain) if terrain else {},
        "physics_config": dict(physics) if physics else {},
    }


def propose_task_llm(
    base_task_name: str,
    generate_fn: Callable[[str], str],  # (prompt_text) -> raw model output
    rng: random.Random,
    step: int = 0,
) -> Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]:
    """Propose a single task by having the LLM generate a related variation (official AZR style).

    generate_fn(prompt_text) should return the model's raw text (e.g. from solver.generate_code
    or model.generate). If the output cannot be parsed as env_overrides, falls back to
    propose_task_from_concrete_task (programmatic stage sample).

    Returns:
        (task_name, base_task_name, prompt_str, variation_dict, env_overrides)
    """
    from evaluation.evaluate_cross_mutated import get_all_stages

    all_stages = get_all_stages(base_task_name)
    if not all_stages:
        return propose_task_from_concrete_task(base_task_name, rng, step=step)

    base_prompt = load_task_prompt(base_task_name)
    desc_summary = (base_prompt.get("task_description", "") or "")[:1500]
    stages_summary = _stages_summary_for_proposal(base_task_name, all_stages)
    user_content = PROPOSE_TASK_USER_TEMPLATE.format(
        base_task_name=base_task_name,
        task_description_summary=desc_summary,
        stages_summary=stages_summary,
    )
    # Single prompt: system + user (generate_fn may wrap with chat template elsewhere)
    propose_prompt = f"{PROPOSE_TASK_SYSTEM}\n\n{user_content}"
    try:
        raw_output = generate_fn(propose_prompt)
    except Exception:
        raw_output = ""
    if not isinstance(raw_output, str):
        raw_output = str(raw_output) if raw_output else ""

    parsed = _parse_proposed_env_overrides(raw_output)
    if not parsed:
        return propose_task_from_concrete_task(base_task_name, rng, step=step)

    # Build a synthetic stage so we can reuse _build_task_prompt_for_stage
    base_stage = next((e for e in all_stages if e.get("stage_id") == "Initial"), all_stages[0])
    synthetic_stage = {
        "stage_id": "LLM-Proposed",
        "terrain_config": parsed["terrain_config"],
        "physics_config": parsed["physics_config"],
        "task_description_suffix": "",
    }
    task_prompt_override, env_overrides = _build_task_prompt_for_stage(
        base_task_name, synthetic_stage, base_stage
    )
    prompt_str = format_initial_prompt(task_prompt_override)
    uid = hashlib.md5(f"{base_task_name}_llm_{step}_{rng.random()}".encode()).hexdigest()[:6]
    task_name = f"proposed_{base_task_name}_llm_{uid}"
    variation = {
        "source": "llm_propose",
        "base_task_name": base_task_name,
        "env_overrides": env_overrides,
    }
    return task_name, base_task_name, prompt_str, variation, env_overrides


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_task(
    rng: random.Random,
    step: int = 0,
) -> Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]:
    """Propose a single training task from templates (demo/basic variations, no benchmark).

    Returns:
        (task_name, base_task, prompt_str, variation_dict, env_overrides)
    """
    template_fn = rng.choice(_TASK_TEMPLATES)
    raw_name, desc, criteria, env_ov = template_fn(rng)

    # Make name unique per step
    uid = hashlib.md5(f"{raw_name}_{step}_{rng.random()}".encode()).hexdigest()[:6]
    task_name = f"proposed_{raw_name}_{uid}"

    prompt = _build_full_prompt(desc, criteria)
    variation = {
        "template": template_fn.__name__,
        "raw_name": raw_name,
        "env_overrides": env_ov,
    }

    return task_name, "demo/basic", prompt, variation, env_ov


def propose_batch(
    batch_size: int,
    seed: int = 42,
    rank: int = 0,
    step: int = 0,
    base_task_name: Optional[str] = None,
    generate_fn: Optional[Callable[[str], str]] = None,
) -> List[Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]]:
    """Propose a batch of training tasks (deterministic per rank & step).

    If base_task_name is a concrete task (e.g. category_1_01 for S_01):
      - If generate_fn is provided (LLM propose): the model proposes related variations
        from the reference task + stages; fallback to stage sampling if parse fails.
      - Else: sample from that task's curriculum stages (programmatic).
    Otherwise uses template-based propose (demo/basic, no benchmark data).

    Returns list of (task_name, base_task, prompt_str, variation_dict, env_overrides).
    """
    rng = random.Random(seed + rank)
    if base_task_name and _is_concrete_task_spec(base_task_name):
        if generate_fn is not None:
            return [
                propose_task_llm(base_task_name, generate_fn, rng, step=step)
                for _ in range(batch_size)
            ]
        return [
            propose_task_from_concrete_task(base_task_name, rng, step=step)
            for _ in range(batch_size)
        ]
    return [propose_task(rng, step=step) for _ in range(batch_size)]
