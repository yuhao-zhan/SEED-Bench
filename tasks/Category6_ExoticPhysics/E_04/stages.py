"""
E-04: Variable Mass task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters (mass variation frequency/amplitude,
base excitation, joint limits, fatigue, damping). The solver agent is NOT told the exact
parameter changes; it must infer from feedback.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# Nominal joint limits and constants from environment.py (source defaults)
DEFAULT_JOINT_BREAK_FORCE = 6.0
DEFAULT_JOINT_BREAK_TORQUE = 10.0
DEFAULT_FATIGUE_TAU_SECONDS = 100.0


def _fmt_limit(value: float) -> str:
    """Format force/torque limit for prompt (handles small values like 1e-10)."""
    if value == 0 or (abs(value) < 1e-6 and value != 0):
        return f"{value:.4g}"
    if abs(value) >= 1000 or (abs(value) < 0.001 and value != 0):
        return f"{value:.4g}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Aerodynamic Loading**: Environmental wind effects may exert pressure on the structure.
- **Gravitational Field**: The gravitational acceleration vector may be significantly different in magnitude or direction.
- **Dynamic Mass**: The temporal variation of mass may follow different frequency or amplitude patterns.
- **Mass Variation Spatial Phase**: How the phase of mass oscillation varies with beam position along the structure.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """
    Update task description with visible changes: joint limits, build zone, mass, span, complexity, etc.
    Format: [new_value] (originally [old_value] in the source environment).
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    # 1. Joint Limits
    base_force = base_physics_config.get("joint_break_force", DEFAULT_JOINT_BREAK_FORCE)
    base_torque = base_physics_config.get("joint_break_torque", DEFAULT_JOINT_BREAK_TORQUE)
    target_force = target_physics_config.get("joint_break_force", base_force)
    target_torque = target_physics_config.get("joint_break_torque", base_torque)

    if target_force != base_force:
        force_pattern = r"(- \*\*Joint Limits \(nominal\)\*\*: Joints fail if reaction force exceeds )(\d+\.?\d*e?-?\d*)(\s*N)( or reaction torque exceeds )"
        description = re.sub(
            force_pattern,
            lambda m: f"{m.group(1)}{_fmt_limit(target_force)} N (originally {_fmt_limit(base_force)} N in the source environment){m.group(4)}",
            description,
        )

    if target_torque != base_torque:
        torque_pattern = r"(reaction torque exceeds )(\d+\.?\d*e?-?\d*)(\s*N·m\s*)(\(before fatigue decay\))"
        description = re.sub(
            torque_pattern,
            lambda m: f"{m.group(1)}{_fmt_limit(target_torque)} N·m (originally {_fmt_limit(base_torque)} N·m in the source environment) {m.group(4)}",
            description,
        )

    # 2. Fatigue (Time Constant)
    base_fatigue = base_physics_config.get("fatigue_tau_seconds", DEFAULT_FATIGUE_TAU_SECONDS)
    target_fatigue = target_physics_config.get("fatigue_tau_seconds", base_fatigue)
    if target_fatigue != base_fatigue:
        fatigue_pattern = r"(- \*\*Fatigue\*\*: Joint strength \(force and torque limits\) decays exponentially over time with a time constant of )(\d+\.?\d*)( s\.)"
        description = re.sub(
            fatigue_pattern,
            lambda m: f"{m.group(1)}{_fmt_limit(target_fatigue)} s (originally {_fmt_limit(base_fatigue)} s in the source environment).",
            description,
        )

    # 3. Build Zone: "- **Build Zone**: x in [5.0, 15.0] m, y in [1.5, 8.0] m."
    bz_pattern = r"(- \*\*Build Zone\*\*: x in \[)(\d+\.?\d*)(,\s*)(\d+\.?\d*)(\] m, y in \[)(\d+\.?\d*)(,\s*)(\d+\.?\d*)(\] m)"
    def bz_replace(m):
        t_xmin = target_terrain_config.get("build_zone_x_min", base_terrain_config.get("build_zone_x_min", 5.0))
        b_xmin = base_terrain_config.get("build_zone_x_min", 5.0)
        t_xmax = target_terrain_config.get("build_zone_x_max", base_terrain_config.get("build_zone_x_max", 15.0))
        b_xmax = base_terrain_config.get("build_zone_x_max", 15.0)
        t_ymin = target_terrain_config.get("build_zone_y_min", base_terrain_config.get("build_zone_y_min", 1.5))
        b_ymin = base_terrain_config.get("build_zone_y_min", 1.5)
        t_ymax = target_terrain_config.get("build_zone_y_max", base_terrain_config.get("build_zone_y_max", 8.0))
        b_ymax = base_terrain_config.get("build_zone_y_max", 8.0)
        
        s = m.group(1)
        s += f"{_fmt_limit(t_xmin)}" + (f" (originally {_fmt_limit(b_xmin)} in the source environment)" if t_xmin != b_xmin else "")
        s += m.group(3)
        s += f"{_fmt_limit(t_xmax)}" + (f" (originally {_fmt_limit(b_xmax)} in the source environment)" if t_xmax != b_xmax else "")
        s += m.group(5)
        s += f"{_fmt_limit(t_ymin)}" + (f" (originally {_fmt_limit(b_ymin)} in the source environment)" if t_ymin != b_ymin else "")
        s += m.group(7)
        s += f"{_fmt_limit(t_ymax)}" + (f" (originally {_fmt_limit(b_ymax)} in the source environment)" if t_ymax != b_ymax else "")
        s += m.group(9)
        return s
    description = re.sub(bz_pattern, bz_replace, description)

    # 3. Span (Objective): "1. Spans from x=6.0m to x=14.0m."
    span_pattern = r"(\d+\. Spans from x=)(\d+\.?\d*)m( to x=)(\d+\.?\d*)m"
    def span_replace(m):
        t_left = target_terrain_config.get("span_left_x", base_terrain_config.get("span_left_x", 6.0))
        b_left = base_terrain_config.get("span_left_x", 6.0)
        t_right = target_terrain_config.get("span_right_x", base_terrain_config.get("span_right_x", 14.0))
        b_right = base_terrain_config.get("span_right_x", 14.0)
        
        s = m.group(1)
        s += f"{_fmt_limit(t_left)}m" + (f" (originally {_fmt_limit(b_left)}m in the source environment)" if t_left != b_left else "")
        s += m.group(3)
        s += f"{_fmt_limit(t_right)}m" + (f" (originally {_fmt_limit(b_right)}m in the source environment)" if t_right != b_right else "")
        return s
    description = re.sub(span_pattern, span_replace, description)

    # 4. Complexity (Objective): "2. Uses at least 5 beams and 6 joints."
    comp_pattern = r"(\d+\. Uses at least )(\d+)\s+beams( and )(\d+)\s+joints"
    def comp_replace(m):
        t_beams = target_terrain_config.get("min_beams", base_terrain_config.get("min_beams", 5))
        b_beams = base_terrain_config.get("min_beams", 5)
        t_joints = target_terrain_config.get("min_joints", base_terrain_config.get("min_joints", 6))
        b_joints = base_terrain_config.get("min_joints", 6)
        
        s = m.group(1)
        s += f"{t_beams} beams" + (f" (originally {b_beams} beams in the source environment)" if t_beams != b_beams else "")
        s += m.group(3)
        s += f"{t_joints} joints" + (f" (originally {b_joints} joints in the source environment)" if t_joints != b_joints else "")
        return s
    description = re.sub(comp_pattern, comp_replace, description)

    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes: Mass budget, Span, complexity."""
    description = base_success_criteria

    # 1. Mass Budget: "(default 400 kg)"
    target_mass = target_terrain_config.get("max_structure_mass", base_terrain_config.get("max_structure_mass", 400.0))
    base_mass = base_terrain_config.get("max_structure_mass", 400.0)
    if target_mass != base_mass:
        pattern = r"(\(default )(\d+\.?\d*)(\s*kg\))"
        description = re.sub(pattern, lambda m: f"(default {_fmt_limit(target_mass)} kg (originally {_fmt_limit(base_mass)} kg in the source environment))", description)

    # 2. Span (Criteria): "2. **Span**: Structure spans from at least x <= 6.0m to x >= 14.0m."
    span_pattern = r"(2\. \*\*Span\*\*: Structure spans from at least x <= )(\d+\.?\d*)m( to x >= )(\d+\.?\d*)m"
    def span_crit_replace(m):
        t_left = target_terrain_config.get("span_left_x", base_terrain_config.get("span_left_x", 6.0))
        b_left = base_terrain_config.get("span_left_x", 6.0)
        t_right = target_terrain_config.get("span_right_x", base_terrain_config.get("span_right_x", 14.0))
        b_right = base_terrain_config.get("span_right_x", 14.0)
        
        s = m.group(1)
        s += f"{_fmt_limit(t_left)}m" + (f" (originally {_fmt_limit(b_left)}m in the source environment)" if t_left != b_left else "")
        s += " to x >= "
        s += f"{_fmt_limit(t_right)}m" + (f" (originally {_fmt_limit(b_right)}m in the source environment)" if t_right != b_right else "")
        return s
    description = re.sub(span_pattern, span_crit_replace, description)


    # 3. Complexity (Criteria): "3. **Complexity**: Meets the minimum beam (5) and joint (6) counts."
    comp_pattern = r"(3\. \*\*Complexity\*\*: Meets the minimum beam \()(\d+)(\) and joint \()(\d+)(\) counts)"
    def comp_crit_replace(m):
        t_beams = target_terrain_config.get("min_beams", base_terrain_config.get("min_beams", 5))
        b_beams = base_terrain_config.get("min_beams", 5)
        t_joints = target_terrain_config.get("min_joints", base_terrain_config.get("min_joints", 6))
        b_joints = base_terrain_config.get("min_joints", 6)
        
        s = m.group(1)
        s += f"{t_beams}" + (f" (originally {b_beams} in the source environment)" if t_beams != b_beams else "")
        s += m.group(3)
        s += f"{t_joints}" + (f" (originally {b_joints} in the source environment)" if t_joints != b_joints else "")
        s += m.group(5)
        return s
    description = re.sub(comp_pattern, comp_crit_replace, description)

    return description

def get_e04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-04 variants.
    Stages use fundamentally different physical challenges.
    """
    return [
        # Stage-1: High-Frequency Resonance + Low Limit
        {
            "stage_id": "Stage-1",
            "title": "Resonant Instability",
            "mutation_description": "Structural mass varies at high frequency with large amplitude, targeting standard beam resonance.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "mass_freq_1": 1.5,
                "mass_amp_1": 0.4,
                "joint_break_force": 0.005,
                "joint_break_torque": 0.002,
            },
        },
        # Stage-2: Zero Torque (Purely Axial) + Wind
        {
            "stage_id": "Stage-2",
            "title": "The Weld-less Truss",
            "mutation_description": "Joints cannot resist ANY torque. Structure must be a perfect funicular arch or truss.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_break_torque": 1e-10,
                "wind_pressure": 10000.0,
                "fatigue_tau_seconds": 400.0,
            },
        },
        # Stage-3: Massive Lateral Load (Extreme Wind + Twisting Phase)
        {
            "stage_id": "Stage-3",
            "title": "The Lateral Vortex",
            "mutation_description": "Extreme wind pressure combined with high spatial mass phase gradient creating non-uniform twisting loads.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "wind_pressure": 1500.0,
                "mass_phase_gradient": 15.0,
                "mass_amp_1": 0.4,
                "fatigue_tau_seconds": 400.0,
                "joint_break_torque": 0.05,
            },
        },

        # Stage-4: The Event Horizon (Lateral Gravity + Fatigue + Zero Torque)
        {
            "stage_id": "Stage-4",
            "title": "Gravitational Shear",
            "mutation_description": "Massive lateral gravity vector combined with zero torque capacity and rapid fatigue.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (15.0, -30.0),
                "joint_break_torque": 1e-10,
                "fatigue_tau_seconds": 60.0,
            },
        },
    ]

