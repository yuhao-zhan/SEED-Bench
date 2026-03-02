"""
AZR-style task proposer: generates diverse 2D physics tasks for self-play training.

Design:
  - Uses the two demo tasks (basic vehicle + control slider) as **few-shot format
    examples** (same INITIAL_DEMONSTRATION from evaluation/prompt.py — NOT test data).
  - Generates diverse physics task variations with **unique descriptive names**.
  - All tasks use the generic `demo/basic` sandbox API (beams, wheels, joints) which
    can represent many 2D physics scenarios.
  - Prompts follow the exact same format as evaluation (physical analysis + code
    template) so training ↔ test format is consistent.
  - CodeVerifier evaluates using the demo environments + env_overrides.

No benchmark test data is used → zero data leakage.
"""
import os
import sys
import json
import random
import hashlib
from typing import Dict, Any, List, Tuple, Optional

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Import the same demonstrations used in evaluation (NOT test data)
from evaluation.prompt import INITIAL_DEMONSTRATION

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
# Public API
# ---------------------------------------------------------------------------

def propose_task(
    rng: random.Random,
    step: int = 0,
) -> Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]:
    """Propose a single training task (no benchmark data leakage).

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
) -> List[Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]]:
    """Propose a batch of training tasks (deterministic per rank & step).

    Returns list of (task_name, base_task, prompt_str, variation_dict, env_overrides).
    """
    rng = random.Random(seed + rank)
    return [propose_task(rng, step=step) for _ in range(batch_size)]
