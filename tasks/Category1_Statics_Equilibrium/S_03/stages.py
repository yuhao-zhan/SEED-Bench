"""
S-03: The Cantilever task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update Reach Goal
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        # Pattern does not consume trailing period; it remains after the match
        pattern = r"(- \*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m"
        description = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m in the source environment)", description)
    
    # Update Mass Limit
    target_mass = target_terrain_config.get("max_structure_mass", 15000.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15000.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Limit\*\*: < )(\d+,?\d*) kg"
        description = re.sub(pattern, f"\\g<1>{target_mass:,.0f} kg (originally {base_mass:,.0f} kg in the source environment)", description)
    
    # Update Payload mass (task_description: "Each payload has mass **500 kg** (applied at t=5s and t=15s).")
    target_load_mass = target_terrain_config.get("load_mass", 500.0)
    base_load_mass = base_terrain_config.get("load_mass", 500.0)
    if target_load_mass != base_load_mass:
        pattern = r"(Each payload has mass \*\*)(\d+,?\d*)( kg\*\*)( \(applied at t=5s and t=15s\))\."
        description = re.sub(pattern, f"\\g<1>{target_load_mass:,.0f}\\g<3>\\g<4> (originally {base_load_mass:,.0f} kg in the source environment).", description)

    # Update load application times (VISIBLE: "at t=5s and t=15s")
    default_load_attach = 5.0
    default_load_2_attach = 15.0
    target_t1 = float(target_terrain_config.get("load_attach_time", default_load_attach))
    target_t2 = float(target_terrain_config.get("load_2_attach_time", default_load_2_attach))
    base_t1 = float(base_terrain_config.get("load_attach_time", default_load_attach))
    base_t2 = float(base_terrain_config.get("load_2_attach_time", default_load_2_attach))
    if target_t1 != base_t1 or target_t2 != base_t2:
        pattern = r"(t=)(\d+\.?\d*)(s and t=)(\d+\.?\d*)(s)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_t1:.1f}s and t={target_t2:.1f}s (originally {base_t1:.1f}s and {base_t2:.1f}s in the source environment)",
                description,
            )

    # Update load hold duration (VISIBLE: "10 seconds each")
    target_duration = float(target_terrain_config.get("load_duration", 10.0))
    base_duration = float(base_terrain_config.get("load_duration", 10.0))
    if target_duration != base_duration:
        pattern = r"(Support all applied payloads for )(\d+\.?\d*)( seconds each)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_duration:.1f} seconds each (originally {base_duration:.1f} seconds in the source environment)",
                description,
            )

    # Update Internal Joint Limits (force and torque)
    default_internal_force = 100000000.0
    default_internal_torque = 100000000.0
    target_f = target_terrain_config.get("max_internal_force", default_internal_force)
    base_f = base_terrain_config.get("max_internal_force", default_internal_force)
    target_t = target_terrain_config.get("max_internal_torque", default_internal_torque)
    base_t = base_terrain_config.get("max_internal_torque", default_internal_torque)
    if target_f != base_f:
        pattern = r"(Beam-to-beam joints fail if force exceeds \*\*)([\d,]+)( N\*\*)"
        description = re.sub(pattern, f"\\g<1>{target_f:,.0f}\\g<3> (originally {base_f:,.0f} N in the source environment)", description)
    if target_t != base_t:
        # Match only Internal line: it ends with " N·m**."; Wall Anchor has " N·m** (exceeding"
        pattern = r"(or torque exceeds \*\*)([\d,]+)( N·m\*\*\.)"
        description = re.sub(pattern, f"\\g<1>{target_t:,.0f} N·m** (originally {base_t:,.0f} N·m in the source environment).", description)
    
    # Update Wall Anchor Limits (task_description: first occurrence is Internal, second is Wall Anchor)
    default_anchor_f = 100000000.0
    default_anchor_t = 100000000.0
    target_af = target_terrain_config.get("max_anchor_force", default_anchor_f)
    base_af = base_terrain_config.get("max_anchor_force", default_anchor_f)
    target_at = target_terrain_config.get("max_anchor_torque", default_anchor_t)
    base_at = base_terrain_config.get("max_anchor_torque", default_anchor_t)
    if target_af != base_af or target_at != base_at:
        # Match the Wall Anchor line specifically (force then torque)
        pattern_wa = r"(- \*\*Wall Anchor Limits\*\*: Wall anchors fail if force exceeds \*\*)([\d,]+)( N\*\* or torque exceeds \*\*)([\d,]+)( N·m\*\* \(exceeding causes anchor failure\)\.)"
        if re.search(pattern_wa, description):
            description = re.sub(
                pattern_wa,
                f"\\g<1>{target_af:,.0f}\\g<3>{target_at:,.0f} N·m** (originally {base_af:,.0f} N and {base_at:,.0f} N·m in the source environment) (exceeding causes anchor failure).",
                description,
            )
    
    # Update Minimum Tip Height
    target_mth = target_terrain_config.get("min_tip_height_limit", -15.0)
    base_mth = base_terrain_config.get("min_tip_height_limit", -15.0)
    if target_mth != base_mth:
        pattern = r"(- \*\*Minimum Tip Height\*\*: The structure must not sag below y = )(-?\d+\.?\d*) m "
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_mth:.1f} m (originally {base_mth:.1f} m in the source environment) ", description)
    
    # Update Reach Deflection Tolerance
    default_tol = 1.0
    target_tol = float(target_terrain_config.get("reach_tolerance", default_tol))
    base_tol = float(base_terrain_config.get("reach_tolerance", default_tol))
    if target_tol != base_tol:
        pattern = r"(- \*\*Reach Deflection Tolerance\*\*: .*? within )(\d+\.?\d*)( m of the target\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_tol:.1f} m (originally {base_tol:.1f} m in the source environment) of the target.", description)
    
    # Update Forbidden Anchor Zones (format: [new_value] (originally [old_value] in the source environment))
    target_forbidden = target_terrain_config.get("forbidden_anchor_y")
    base_forbidden = base_terrain_config.get("forbidden_anchor_y")
    if target_forbidden is not None and len(target_forbidden) >= 2:
        y_min, y_max = float(target_forbidden[0]), float(target_forbidden[1])
        base_str = "no restrictions"
        if base_forbidden is not None and len(base_forbidden) >= 2:
            base_str = f"y = [{float(base_forbidden[0]):.1f}, {float(base_forbidden[1]):.1f}] m"
        pattern = r"(- \*\*Forbidden Anchor Zones\*\*: )Wall anchors may be restricted to certain vertical segments \(y range\)\. In the source environment there are no restrictions\."
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>Anchors are forbidden in y = [{y_min:.1f}, {y_max:.1f}] m (originally {base_str} in the source environment).",
                description,
            )

    # Update Obstacles: when active, include explicit geometry (originally ... in the source environment)
    if target_terrain_config.get("obstacle_active", False):
        rects = target_terrain_config.get("obstacle_rects", [])
        if rects:
            parts = []
            for rect in rects:
                if len(rect) >= 4:
                    x_min, y_min, x_max, y_max = float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])
                    parts.append(f"x = [{x_min:.1f}, {x_max:.1f}] m, y = [{y_min:.1f}, {y_max:.1f}] m")
            obstacle_desc = "; ".join(parts) if parts else "static obstructions present"
        else:
            obstacle_desc = "static obstructions present"
        pattern = r"(- \*\*Obstacles\*\*: )(.*?)( \(originally none in the source environment\)\.)"
        if re.search(pattern, description):
            replacement = r"\g<1>Static obstructions occupy axis-aligned region(s): " + obstacle_desc + " (originally none in the source environment)."
            description = re.sub(pattern, replacement, description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Reach in Success Criteria
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(\(Tip reaches x >= )(\d+\.?\d*)m\)\."
        criteria = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m in the source environment)).", criteria)
    
    # Update Mass Budget in Success Criteria
    target_mass = target_terrain_config.get("max_structure_mass", 15000.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15000.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Budget\*\*: < )(\d+,?\d*) kg"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:,.0f} kg (originally {base_mass:,.0f} kg in the source environment)", criteria)
    
    # Update Payload Mass in Success Criteria
    target_load_mass = target_terrain_config.get("load_mass", 500.0)
    base_load_mass = base_terrain_config.get("load_mass", 500.0)
    if target_load_mass != base_load_mass:
        pattern = r"(- \*\*Payload Mass\*\*: )(\d+,?\d*)( kg per applied load\.)"
        criteria = re.sub(pattern, f"\\g<1>{target_load_mass:,.0f}\\g<3> (originally {base_load_mass:,.0f} kg in the source environment)", criteria)

    # Update load hold duration in Success Criteria ("10s test duration")
    target_duration = float(target_terrain_config.get("load_duration", 10.0))
    base_duration = float(base_terrain_config.get("load_duration", 10.0))
    if target_duration != base_duration:
        pattern = r"(Successfully supports all payloads for the )(\d+\.?\d*)(s test duration\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_duration:.1f}s test duration (originally {base_duration:.1f}s in the source environment).",
                criteria,
            )

    # Update Internal Joint Limits in Success Criteria (only the Internal line, not Wall Anchor)
    default_internal = 100000000.0
    target_f = target_terrain_config.get("max_internal_force", default_internal)
    base_f = base_terrain_config.get("max_internal_force", default_internal)
    target_t = target_terrain_config.get("max_internal_torque", default_internal)
    base_t = base_terrain_config.get("max_internal_torque", default_internal)
    if target_f != base_f:
        pattern = r"(- \*\*Internal Joint Limits\*\*: Max force )([\d,]+)( N;)"
        criteria = re.sub(pattern, f"\\g<1>{target_f:,.0f} N (originally {base_f:,.0f} N in the source environment);", criteria)
    if target_t != base_t:
        pattern = r"(- \*\*Internal Joint Limits\*\*:.*?max torque )([\d,]+)( N·m \()"
        criteria = re.sub(pattern, f"\\g<1>{target_t:,.0f} N·m (originally {base_t:,.0f} N·m in the source environment) (", criteria)

    # Update Wall Anchor Limits in Success Criteria (line: "Wall Anchor Limits: Max force ...; max torque ...")
    default_anchor = 100000000.0
    target_af = target_terrain_config.get("max_anchor_force", default_anchor)
    base_af = base_terrain_config.get("max_anchor_force", default_anchor)
    target_at = target_terrain_config.get("max_anchor_torque", default_anchor)
    base_at = base_terrain_config.get("max_anchor_torque", default_anchor)
    if target_af != base_af or target_at != base_at:
        pattern_wa = r"(- \*\*Wall Anchor Limits\*\*: Max force )([\d,]+)( N; max torque )([\d,]+)( N·m )\(exceeding causes failure\)\."
        if re.search(pattern_wa, criteria):
            criteria = re.sub(
                pattern_wa,
                f"\\g<1>{target_af:,.0f}\\g<3>{target_at:,.0f}\\g<5> (originally {base_af:,.0f} N and {base_at:,.0f} N·m in the source environment) (exceeding causes failure).",
                criteria,
            )
    
    # Update Minimum Tip Height in Success Criteria (e.g. "y >= -15.0 m).")
    target_mth = target_terrain_config.get("min_tip_height_limit", -15.0)
    base_mth = base_terrain_config.get("min_tip_height_limit", -15.0)
    if target_mth != base_mth:
        pattern_mth = r"(y >= )(-?\d+\.?\d*)( m\)\.)"
        if re.search(pattern_mth, criteria):
            criteria = re.sub(pattern_mth, f"\\g<1>{target_mth:.1f} m) (originally {base_mth:.1f} m in the source environment).", criteria)
    
    # Update Reach Tolerance in Success Criteria
    default_tol = 1.0
    target_tol = float(target_terrain_config.get("reach_tolerance", default_tol))
    base_tol = float(base_terrain_config.get("reach_tolerance", default_tol))
    if target_tol != base_tol:
        pattern_tol = r"(- \*\*Reach Tolerance\*\*: Under load, tip x may be up to )(\d+\.?\d*)( m short of target and still satisfy reach\.)"
        if re.search(pattern_tol, criteria):
            criteria = re.sub(pattern_tol, f"\\g<1>{target_tol:.1f} m (originally {base_tol:.1f} m in the source environment) short of target and still satisfy reach.", criteria)

    # Update Forbidden Anchor Zones in Success Criteria
    target_forbidden = target_terrain_config.get("forbidden_anchor_y")
    base_forbidden = base_terrain_config.get("forbidden_anchor_y")
    if target_forbidden is not None and len(target_forbidden) >= 2:
        y_min, y_max = float(target_forbidden[0]), float(target_forbidden[1])
        base_str = "none"
        if base_forbidden is not None and len(base_forbidden) >= 2:
            base_str = f"y = [{float(base_forbidden[0]):.1f}, {float(base_forbidden[1]):.1f}] m"
        pattern = r"(- \*\*Forbidden Anchor Zones\*\*: )None in the source environment\."
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>y = [{y_min:.1f}, {y_max:.1f}] m forbidden (originally {base_str} in the source environment).",
                criteria,
            )
        
    return criteria


def get_s03_curriculum_stages() -> List[Dict[str, Any]]:
    # DYNAMICALLY GENERATED UNIFORM SUFFIX (Union of all mutated variables in S_03 Stages 1-4)
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Operational Range**: The required horizontal extension (Target Reach) from the anchor wall may have changed.
 - **Structural Load Capacity**: The target load mass and the total structural mass budget may have been adjusted to different levels.
 - **Joint Integrity Thresholds**: The maximum force and torque that internal (beam-to-beam) joints can withstand may differ from the source environment; exceeding these limits causes immediate structural failure.
 - **Localized Force Fields**: Invisible spatial anomalies might exert powerful repulsive or attractive forces on any structure within their radius of influence.
 - **Anchor Zoning Constraints**: Certain vertical segments of the wall may be restricted (Forbidden Anchor Zones), preventing any joints from being anchored within those height ranges.
 - **Static Obstructions**: Massive, impenetrable structures might be present in the build zone, necessitating complex geometries to navigate around them.
 - **Dynamic Load Impacts**: The payload might be dropped from a height rather than being placed statically, introducing severe impulse forces.
 - **Atmospheric Oscillations**: Variable or oscillatory wind forces may act on the structure, inducing complex dynamic stresses.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Brittle Connections",
            "mutation_description": "Single Variable: Extreme internal joint fragility.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 25.0, 
                "load_mass": 800.0, 
                "max_structure_mass": 8000.0,
                "max_internal_force": 200000.0,
                "max_internal_torque": 200000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Magnetic Anomaly",
            "mutation_description": "Single Variable: Extreme spatial repulsion forcing complex structural compensation.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 28.0,
                "load_mass": 1500.0,
                "max_structure_mass": 10000.0,
            },
            "physics_config": {
                "spatial_force": {
                    "center": (14.0, 10.0),
                    "magnitude": 1200000.0,
                    "radius": 18.0,
                    "type": "repulsion"
                }
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Blockaded Wall",
            "mutation_description": "Multi-variable: Wall forbidden zone + Massive Obstacle. Forces extreme low construction.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 28.0,
                "load_mass": 1200.0,
                "max_structure_mass": 10000.0,
                "forbidden_anchor_y": [-5.0, 15.0],
                "obstacle_active": True,
                "obstacle_rects": [
                    [5.0, 5.0, 30.0, 25.0],
                ],
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Multi-variable: Fragile joints + Repulsion Field + Forbidden Wall + Dropped Loads + Oscillatory Wind.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 35.0,
                "load_mass": 1500.0,
                "max_structure_mass": 15000.0,
                "max_internal_force": 1000000.0,
                "max_internal_torque": 1000000.0,
                "forbidden_anchor_y": [0.0, 10.0],
                "load_type": "dropped",
                "drop_height": 8.0,
            },
            "physics_config": {
                "spatial_force": {
                    "center": (15.0, 8.0),
                    "magnitude": 40000.0,
                    "radius": 12.0,
                    "type": "repulsion"
                },
                "wind": {
                    "force": (0, 800.0),
                    "oscillatory": True,
                    "frequency": 0.5
                }
            },
        },
    ]
