"""
S-04: The Balancer task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Pivot Connection Type: The type of connection at the central support may differ from the default (rigid weld), potentially allowing free rotation (revolute joint).
 - Fragile Anchor Points: The central pivot joint's static torque capacity may differ from the default. If the net torque exceeds this threshold, the fulcrum will snap.
 - Rotational Friction: The friction at the pivot point may differ from the default, affecting natural damping and sensitivity to mass imbalance.
 - Precision Thresholds: The allowable angle for "balance" may differ from the default, requiring you to discover the effective tolerance through feedback.
 - Lateral Wind Currents: Persistent horizontal air currents may exert forces on all components, creating overturning torques that must be countered by offset mass distributions.
 - Gravitational Fluctuations: Local gravity may differ from Earth-standard, affecting the magnitude of mass imbalance and structural stress.
 - Spatial Obstructions: Static structural barriers occupy parts of the workspace, forcing non-linear designs to navigate around "no-build" zones.
 - Dynamic Loading: The target mass may be dropped from a height rather than starting in a static position, requiring your structure to absorb kinetic energy while maintaining equilibrium.
 - Angular Damping: Rotational damping of bodies may be altered, affecting how quickly oscillations decay.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update description for visible changes."""
    description = base_description
    
    # Update Load Mass
    base_mass = base_terrain_config.get("load_mass", 200.0)
    target_mass = target_terrain_config.get("load_mass", 200.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*The Load\*\*: A heavy block \(mass: )(\d+\.?\d*)( kg\) )"
        description = re.sub(
            pattern,
            f"\\g<1>{target_mass:.1f} kg (originally {base_mass:.1f} kg in the source environment)) ",
            description,
        )

    # Update max angle deviation in task description when mutated
    base_angle = base_terrain_config.get("max_angle_deviation_deg", 10.0)
    target_angle = target_terrain_config.get("max_angle_deviation_deg", 10.0)
    if target_angle != base_angle:
        angle_pattern = r"(horizontal angle within ±)(\d+\.?\d*)( degrees)(\))( for \d+ seconds\.)"
        if re.search(angle_pattern, description):
            description = re.sub(
                angle_pattern,
                lambda m: f"{m.group(1)}{target_angle:.1f}{m.group(3)} (originally ±{base_angle:.1f} degrees in the source environment)){m.group(5)}",
                description,
            )

    if target_terrain_config.get("drop_load"):
        description = description.replace(
            "It may automatically attach (weld) to your structure if any part of your design is built within 0.5m of (3, 5.5), OR it may be DROPPED from above, starting at (3, 9). When dropped, the load is considered caught when within 0.6 m of any part of your structure.",
            "The load will be DROPPED from above, starting at (3, 9) (originally static—attach when within 0.5 m of (3, 5.5)—in the source environment). When dropped, the load is considered caught when within 0.6 m of any part of your structure. You must catch and balance it without it touching the ground."
        )

    # Update pivot torque capacity (when fragile) when mutated
    default_max_joint_torque = 1000.0
    base_torque = base_terrain_config.get("max_joint_torque", default_max_joint_torque)
    target_torque = target_terrain_config.get("max_joint_torque", default_max_joint_torque)
    if target_torque != base_torque:
        torque_pattern = r"(- \*\*Pivot torque capacity\*\* \(when fragile\): In environments where the pivot is fragile, the joint fails if the magnitude of static torque about the pivot exceeds )(\d+\.?\d*)( N·m\.)"
        if re.search(torque_pattern, description):
            description = re.sub(
                torque_pattern,
                lambda m: f"{m.group(1)}{target_torque:.1f} N·m (originally {base_torque:.1f} N·m in the source environment).",
                description,
            )
    
    # Update pivot connection type when force_pivot_joint (revolute) is used
    if target_terrain_config.get("force_pivot_joint"):
        pivot_conn_pattern = r"(2\. Connects to the pivot point at \(0, 5\)\.)"
        if re.search(pivot_conn_pattern, description):
            description = re.sub(
                pivot_conn_pattern,
                "2. Connects to the pivot point at (0, 5). The pivot is a free-rotating (revolute) joint (originally a fixed weld in the source environment).",
                description,
            )
    
    # Update balance_time when mutated (task description: "for 15 seconds.")
    default_balance_time = 15.0
    base_balance_time = base_terrain_config.get("balance_time", default_balance_time)
    target_balance_time = target_terrain_config.get("balance_time", default_balance_time)
    if target_balance_time != base_balance_time:
        balance_time_pattern = r"( for )(\d+\.?\d*)( seconds\.)"
        if re.search(balance_time_pattern, description):
            description = re.sub(
                balance_time_pattern,
                f"\\g<1>{target_balance_time:.1f} seconds (originally {base_balance_time:.1f} s in the source environment).",
                description,
                1,
            )

    # Update ground_y_failure when mutated (task description: "y < -5.0 m) will lead to failure.")
    default_ground_y = -5.0
    base_ground_y = base_terrain_config.get("ground_y_failure", default_ground_y)
    target_ground_y = target_terrain_config.get("ground_y_failure", default_ground_y)
    if target_ground_y != base_ground_y:
        ground_lt_pattern = r"(y < )(-?\d+\.?\d*)( m\) will lead to failure\.)"
        if re.search(ground_lt_pattern, description):
            description = re.sub(
                ground_lt_pattern,
                f"\\g<1>{target_ground_y:.1f} m (originally {base_ground_y:.1f} m in the source environment)) will lead to failure.",
                description,
            )

    # Update obstacles when obstacle_active and obstacles list present
    # Use world coordinates (add PIVOT_Y to y) so prompt matches environment._create_terrain
    PIVOT_Y = 5.0
    if target_terrain_config.get("obstacle_active"):
        rects = target_terrain_config.get("obstacles", [])
        if rects:
            world_rects = [(r[0], r[1] + PIVOT_Y, r[2], r[3] + PIVOT_Y) for r in rects]
            obstacle_desc = "; ".join(f"[{xmin:.1f}, {ymin:.1f}, {xmax:.1f}, {ymax:.1f}]" for xmin, ymin, xmax, ymax in world_rects)
            old = "The environment may contain static obstacles you must build around, or experience"
            new = f"Static obstructions occupy axis-aligned region(s): {obstacle_desc} (originally none in the source environment). The environment may experience"
            description = description.replace(old, new)
    
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    if target_terrain_config.get("drop_load"):
        criteria = criteria.replace(
            "Successfully catch or connect to the heavy load at x=3.0.",
            "Successfully catch the falling load and prevent it from touching the ground (originally catch or connect to the heavy load at x=3.0 in the source environment)."
        )
    
    base_angle = base_terrain_config.get("max_angle_deviation_deg", 10.0)
    max_angle = target_terrain_config.get("max_angle_deviation_deg", 10.0)
    if max_angle != base_angle:
        criteria = criteria.replace("within ±10 degrees", f"within ±{max_angle:.1f} degrees (originally ±{base_angle:.1f} degrees in the source environment)")

    # Update balance_time when mutated (success criteria: "for at least 15 seconds")
    default_balance_time = 15.0
    base_balance_time = base_terrain_config.get("balance_time", default_balance_time)
    target_balance_time = target_terrain_config.get("balance_time", default_balance_time)
    if target_balance_time != base_balance_time:
        criteria_balance_pattern = r"(for at least )(\d+\.?\d*)( seconds after the load is supported\.)"
        if re.search(criteria_balance_pattern, criteria):
            criteria = re.sub(
                criteria_balance_pattern,
                f"\\g<1>{target_balance_time:.1f} seconds (originally {base_balance_time:.1f} s in the source environment) after the load is supported.",
                criteria,
                1,
            )

    # Update ground_y_failure when mutated (success criteria: "y >= -5.0 m) or any surface other than the pivot.")
    default_ground_y = -5.0
    base_ground_y = base_terrain_config.get("ground_y_failure", default_ground_y)
    target_ground_y = target_terrain_config.get("ground_y_failure", default_ground_y)
    if target_ground_y != base_ground_y:
        criteria_ground_pattern = r"(The structure does not touch the ground \(y >= )(-?\d+\.?\d*)( m\) or any surface other than the pivot\.)"
        if re.search(criteria_ground_pattern, criteria):
            criteria = re.sub(
                criteria_ground_pattern,
                f"\\g<1>{target_ground_y:.1f} m (originally {base_ground_y:.1f} m in the source environment)) or any surface other than the pivot.",
                criteria,
            )

    return criteria


def get_s04_curriculum_stages() -> List[Dict[str, Any]]:
    """Returns ordering stage configs."""
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Glass Fulcrum",
            "mutation_description": "The pivot joint is extremely brittle. It will snap if the net torque exceeds a tiny threshold, requiring near-perfect static balance.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "fragile_joints": True, 
                "max_joint_torque": 100.0, 
                "load_mass": 200.0,
                "max_angle_deviation_deg": 10.0,
            },
            "physics_config": {
                "gravity": (0, -10.0),
                "angular_damping": 1.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Frictionless Void",
            "mutation_description": "Pivot friction is eliminated and the stability requirement is significantly tightened. Any minor oscillation will lead to failure.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "pivot_friction": 0.0,
                "load_mass": 200.0,
                "max_angle_deviation_deg": 2.0,
            },
            "physics_config": {
                "angular_damping": 0.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Hurricane Gravity",
            "mutation_description": "Extreme gravity and lateral wind combine to create overwhelming overturning torque, while obstacles block standard counterweight paths.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "obstacle_active": True,
                "obstacles": [
                    [-4.5, -2.0, -1.5, 0.0], # Block left build zone
                    [1.0, 0.5, 2.5, 2.0], # Block right build zone
                ],
                "wind_active": True,
                "wind_force_multiplier": 5.0,
                "load_mass": 200.0,
                "max_angle_deviation_deg": 20.0,
            },
            "physics_config": {
                "gravity": (0, -40.0),
                "angular_damping": 10.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Kinetic Impact",
            "mutation_description": "Catch a falling load in a high-gravity wind-swept environment with a brittle pivot and spatial constraints. The impact force must be carefully managed.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True, 
                "obstacle_active": True,
                "obstacles": [
                    [2.0, 3.5, 4.0, 4.5], # Above load
                    [-0.5, 2.5, 0.5, 3.5], # Above pivot
                ],
                "wind_active": True,
                "wind_force_multiplier": 10.0,
                "drop_load": True,
                "load_mass": 200.0,
                "fragile_joints": True,
                "max_joint_torque": 500000.0, 
                "max_angle_deviation_deg": 80.0,
            },
            "physics_config": {
                "gravity": (0, -20.0),
                "angular_damping": 5.0,
            },
        },
    ]
