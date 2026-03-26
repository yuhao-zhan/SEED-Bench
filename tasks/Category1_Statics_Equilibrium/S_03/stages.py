"""
S-03: The Cantilever task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update Reach Goal (cascading-safe: match optional " (originally ...)")
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(- \*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m(?: \(originally [^)]+\))?\.?"
        description = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m in the source environment).", description)
    
    # Update Mass Limit (cascading-safe)
    target_mass = target_terrain_config.get("max_structure_mass", 15000.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15000.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Limit\*\*: <= )([\d,]+)( kg)(?: \(originally [^)]+\))?\.?"
        description = re.sub(pattern, f"\\g<1>{target_mass:,.0f} kg (originally {base_mass:,.0f} kg in the source environment).", description)
    
    # Update Payload mass (task_description: "Each payload has mass **500 kg** (applied at t=5s and t=15s).")
    # Cascading-safe: match mass number only so it works whether or not load times were updated first.
    target_load_mass = target_terrain_config.get("load_mass", 500.0)
    base_load_mass = base_terrain_config.get("load_mass", 500.0)
    if target_load_mass != base_load_mass:
        # Match "Each payload has mass **NNN kg**" plus rest of sentence up to " The first payload".
        # This regex avoids strict dependency on the punctuation at the end of the load times part.
        pattern = r"(Each payload has mass \*\*)(\d+,?\d*)( kg\*\*)(.*?)(\s+The first payload)"
        def _replace_mass(m):
            mid = m.group(4)
            # If load times were already updated, mid will end with "))." or similar.
            # We want to insert the mass "originally" part before the final "." if it exists.
            if mid.endswith("."):
                mid_content = mid[:-1]
                return f"{m.group(1)}{target_load_mass:,.0f}{m.group(3)}{mid_content} (originally {base_load_mass:,.0f} kg in the source environment).{m.group(5)}"
            elif mid.endswith(". "):
                mid_content = mid[:-2]
                # group(5) usually starts with a space, so we don't add one here after the period.
                return f"{m.group(1)}{target_load_mass:,.0f}{m.group(3)}{mid_content} (originally {base_load_mass:,.0f} kg in the source environment).{m.group(5)}"
            return f"{m.group(1)}{target_load_mass:,.0f}{m.group(3)}{mid} (originally {base_load_mass:,.0f} kg in the source environment){m.group(5)}"
        if re.search(pattern, description):
            description = re.sub(pattern, _replace_mass, description, count=1)

    # Update load application times (VISIBLE: "at t=5s and t=15s")
    default_load_attach = 5.0
    default_load_2_attach = 15.0
    target_t1 = float(target_terrain_config.get("load_attach_time", default_load_attach))
    target_t2 = float(target_terrain_config.get("load_2_attach_time", default_load_2_attach))
    base_t1 = float(base_terrain_config.get("load_attach_time", default_load_attach))
    base_t2 = float(base_terrain_config.get("load_2_attach_time", default_load_2_attach))
    if target_t1 != base_t1 or target_t2 != base_t2:
        # Match "at t=5s and t=15s" followed by optional " (originally ...)" and optional punctuation.
        pattern1 = r"\(e\.g\., at (t=)(\d+\.?\d*)(s and t=)(\d+\.?\d*)(s)(?: \(originally [^)]+\))?\)\.?\s*"
        pattern2 = r"\(applied at (t=)(\d+\.?\d*)(s and t=)(\d+\.?\d*)(s)(?: \(originally [^)]+\))?\)\.?\s*"
        replacement1 = f"(e.g., at t={target_t1:.1f}s and t={target_t2:.1f}s (originally {base_t1:.1f}s and {base_t2:.1f}s in the source environment)). "
        replacement2 = f"(applied at t={target_t1:.1f}s and t={target_t2:.1f}s (originally {base_t1:.1f}s and {base_t2:.1f}s in the source environment)). "
        if re.search(pattern1, description):
            description = re.sub(pattern1, replacement1, description)
        if re.search(pattern2, description):
            description = re.sub(pattern2, replacement2, description)

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

    # Update Internal Joint Limits (force and torque) (cascading-safe)
    default_internal_force = 100000000.0
    default_internal_torque = 100000000.0
    target_f = target_terrain_config.get("max_internal_force", default_internal_force)
    base_f = base_terrain_config.get("max_internal_force", default_internal_force)
    target_t = target_terrain_config.get("max_internal_torque", default_internal_torque)
    base_t = base_terrain_config.get("max_internal_torque", default_internal_torque)
    if target_f != base_f:
        pattern = r"(Beam-to-beam joints fail if force exceeds \*\*)([\d,]+)( N\*\*)(?: \(originally [^)]+\))?"
        description = re.sub(pattern, f"\\g<1>{target_f:,.0f} N** (originally {base_f:,.0f} N in the source environment)", description)
    if target_t != base_t:
        # Match Internal line: " N·m**." or " N·m** (originally ...)."
        pattern = r"(or torque exceeds \*\*)([\d,]+)( N·m\*\*)(?: \(originally [^)]+\))?\.?"
        description = re.sub(pattern, f"\\g<1>{target_t:,.0f} N·m** (originally {base_t:,.0f} N·m in the source environment).", description)
    
    # Update Wall Anchor Limits (task_description; cascading-safe)
    default_anchor_f = 100000000.0
    default_anchor_t = 100000000.0
    target_af = target_terrain_config.get("max_anchor_force", default_anchor_f)
    base_af = base_terrain_config.get("max_anchor_force", default_anchor_f)
    target_at = target_terrain_config.get("max_anchor_torque", default_anchor_t)
    base_at = base_terrain_config.get("max_anchor_torque", default_anchor_t)
    if target_af != base_af or target_at != base_at:
        # Replacement uses literal " N·m**" so trailing clause appears once (no duplicate from \g<5>)
        pattern_wa = r"(- \*\*Wall Anchor Limits\*\*: Wall anchors fail if force exceeds \*\*)([\d,]+)( N\*\* or torque exceeds \*\*)([\d,]+)( N·m\*\*)(?: \(originally [^)]+\))? \(exceeding causes anchor failure\)\."
        if re.search(pattern_wa, description):
            description = re.sub(
                pattern_wa,
                f"\\g<1>{target_af:,.0f} N** or torque exceeds **{target_at:,.0f} N·m** (originally {base_af:,.0f} N and {base_at:,.0f} N·m in the source environment) (exceeding causes anchor failure).",
                description,
            )
    
    # Update Minimum Tip Height (cascading-safe)
    target_mth = target_terrain_config.get("min_tip_height_limit", -15.0)
    base_mth = base_terrain_config.get("min_tip_height_limit", -15.0)
    if target_mth != base_mth:
        pattern = r"(- \*\*Minimum Tip Height\*\*: The structure must not sag below y = )(-?\d+\.?\d*)( m )(?:\(originally [^)]+\) )?"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_mth:.1f} m (originally {base_mth:.1f} m in the source environment) ", description)
    
    # Update Reach Deflection Tolerance (cascading-safe: match " m of the target." or " m (originally ...) of the target.")
    # Prompt text ends with "of the target." (no closing paren).
    default_tol = 1.0
    target_tol = float(target_terrain_config.get("reach_tolerance", default_tol))
    base_tol = float(base_terrain_config.get("reach_tolerance", default_tol))
    if target_tol != base_tol:
        pattern = r"(- \*\*Reach Deflection Tolerance\*\*: .*? within )(\d+\.?\d*)( m )(?:\(originally [^)]+\) )?of the target\."
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_tol:.1f} m (originally {base_tol:.1f} m in the source environment) of the target.", description)
    
    # Update Forbidden Anchor Zones: match either initial text or already-updated "Anchors are forbidden in y = [...]"
    target_forbidden = target_terrain_config.get("forbidden_anchor_y")
    base_forbidden = base_terrain_config.get("forbidden_anchor_y")
    if target_forbidden is not None and len(target_forbidden) >= 2:
        y_min, y_max = float(target_forbidden[0]), float(target_forbidden[1])
        base_str = "no restrictions"
        if base_forbidden is not None and len(base_forbidden) >= 2:
            base_str = f"y = [{float(base_forbidden[0]):.1f}, {float(base_forbidden[1]):.1f}] m"
        # Try initial format first
        pattern_initial = r"(- \*\*Forbidden Anchor Zones\*\*: )Wall anchors may be restricted to certain vertical segments \(y range\)\. In the source environment there are no restrictions\."
        pattern_updated = r"(- \*\*Forbidden Anchor Zones\*\*: )Anchors are forbidden in y = \[[^\]]+\] m \(originally [^)]+\)\."
        replacement = f"\\g<1>Anchors are forbidden in y = [{y_min:.1f}, {y_max:.1f}] m (originally {base_str} in the source environment)."
        if re.search(pattern_initial, description):
            description = re.sub(pattern_initial, replacement, description)
        elif re.search(pattern_updated, description):
            description = re.sub(pattern_updated, replacement, description)

    # Update Obstacles: when active, include explicit geometry (originally ... in the source environment).
    # Cascade "originally" from base_terrain_config when base already had obstacles.
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
        base_rects = base_terrain_config.get("obstacle_rects", [])
        if base_terrain_config.get("obstacle_active", False) and base_rects:
            base_parts = []
            for rect in base_rects:
                if len(rect) >= 4:
                    x_min, y_min, x_max, y_max = float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])
                    base_parts.append(f"x = [{x_min:.1f}, {x_max:.1f}] m, y = [{y_min:.1f}, {y_max:.1f}] m")
            originally_str = ("; ".join(base_parts) + " in the source environment") if base_parts else "static obstructions in the source environment"
        else:
            originally_str = "none in the source environment"
        pattern = r"(- \*\*Obstacles\*\*: )(.*?)( \(originally )(none in the source environment|static obstructions in the source environment|.*?)(\)\.)"
        if re.search(pattern, description):
            replacement = r"\g<1>Static obstructions occupy axis-aligned region(s): " + obstacle_desc + " (originally " + originally_str + ")."
            description = re.sub(pattern, replacement, description)

    # Update Payload application (load_type and drop_height) when mutated to "dropped"
    target_load_type = target_terrain_config.get("load_type", "static")
    base_load_type = base_terrain_config.get("load_type", "static")
    target_drop = float(target_terrain_config.get("drop_height", 10.0))
    base_drop = float(base_terrain_config.get("drop_height", 10.0))
    if target_load_type == "dropped":
        # Update the sentence that says "in the source environment payloads are placed statically (no drop)"
        pattern_static = r"in the source environment payloads are placed statically \(no drop\)\.?"
        drop_sentence = f"Payloads are **dropped** from {target_drop:.1f} m height (originally placed statically in the source environment)."
        if re.search(pattern_static, description):
            description = re.sub(pattern_static, drop_sentence, description)
    elif base_load_type == "dropped" and target_load_type == "static":
        # Revert to static if needed (e.g. when base was mutated)
        pattern_dropped = r"Payloads are \*\*dropped\*\* from [\d.]+ m height \(originally placed statically in the source environment\)\. "
        if re.search(pattern_dropped, description):
            description = re.sub(pattern_dropped, "in the source environment payloads are placed statically (no drop). ", description)

    # Update anchor_strength_map (Regional Anchor Weakness): when set, state segment and multipliers
    target_strength_map = target_terrain_config.get("anchor_strength_map", None)
    base_strength_map = base_terrain_config.get("anchor_strength_map", None)
    if target_strength_map and len(target_strength_map) > 0:
        parts = []
        for entry in target_strength_map:
            if len(entry) >= 4:
                y_lo, y_hi, f_mult, t_mult = float(entry[0]), float(entry[1]), float(entry[2]), float(entry[3])
                parts.append(f"y = [{y_lo:.1f}, {y_hi:.1f}] m: force and torque at {f_mult*100:.2f}% and {t_mult*100:.2f}% of base limits")
        if parts:
            strength_desc = "; ".join(parts)
            base_str = "none in the source environment"
            if base_strength_map and len(base_strength_map) > 0 and len(base_strength_map[0]) >= 4:
                be = base_strength_map[0]
                base_str = f"y = [{float(be[0]):.1f}, {float(be[1]):.1f}] m at {float(be[2])*100:.2f}%/{float(be[3])*100:.2f}% in the source environment"
            pattern_anchor = r"(When segment-specific anchor strength applies, the vertical segment \(y range\) and force/torque multipliers are stated explicitly\.)"
            pattern_anchor_updated = r"(Regional anchor weakness: .*? \(originally [^)]+\)\.)"
            replacement_anchor = f"Regional anchor weakness: {strength_desc} (originally {base_str})."
            if re.search(pattern_anchor, description):
                description = re.sub(pattern_anchor, replacement_anchor, description)
            elif re.search(pattern_anchor_updated, description):
                description = re.sub(pattern_anchor_updated, replacement_anchor, description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Reach in Success Criteria (cascading-safe)
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(\(Tip reaches x >= )(\d+\.?\d*)m(?: \(originally [^)]+\))?\)\."
        criteria = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m in the source environment)).", criteria)
    
    # Update Mass Budget in Success Criteria (cascading-safe)
    target_mass = target_terrain_config.get("max_structure_mass", 15000.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15000.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Budget\*\*: <= )([\d,]+)( kg)(?: \(originally [^)]+\))?\.?"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:,.0f} kg (originally {base_mass:,.0f} kg in the source environment).", criteria)
    
    # Update Payload Mass in Success Criteria (cascading-safe)
    target_load_mass = target_terrain_config.get("load_mass", 500.0)
    base_load_mass = base_terrain_config.get("load_mass", 500.0)
    if target_load_mass != base_load_mass:
        pattern = r"(- \*\*Payload Mass\*\*: )([\d,]+)( kg per applied load)(?: \(originally [^)]+\))?\.?"
        criteria = re.sub(pattern, f"\\g<1>{target_load_mass:,.0f}\\g<3> (originally {base_load_mass:,.0f} kg in the source environment).", criteria)

    # Update load hold duration in Success Criteria (cascading-safe)
    target_duration = float(target_terrain_config.get("load_duration", 10.0))
    base_duration = float(base_terrain_config.get("load_duration", 10.0))
    if target_duration != base_duration:
        # Update numbered item
        pattern = r"(Successfully supports all payloads for the )(\d+\.?\d*)(s test duration)(?: \(originally [^)]+\))?\.?"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_duration:.1f}s test duration (originally {base_duration:.1f}s in the source environment).",
                criteria,
            )
        # Update bullet point
        pattern_bullet = r"(- \*\*Load Duration\*\*: Support each payload for )(\d+\.?\d*)( seconds)(?: \(originally [^)]+\))?\.?"
        if re.search(pattern_bullet, criteria):
            criteria = re.sub(
                pattern_bullet,
                f"\\g<1>{target_duration:.1f} seconds (originally {base_duration:.1f} seconds in the source environment).",
                criteria,
            )

    # Update Internal Joint Limits in Success Criteria (cascading-safe)
    default_internal = 100000000.0
    target_f = target_terrain_config.get("max_internal_force", default_internal)
    base_f = base_terrain_config.get("max_internal_force", default_internal)
    target_t = target_terrain_config.get("max_internal_torque", default_internal)
    base_t = base_terrain_config.get("max_internal_torque", default_internal)
    if target_f != base_f:
        pattern = r"(- \*\*Internal Joint Limits\*\*: Max force )([\d,]+)( N)(?: \(originally [^)]+\))?;"
        criteria = re.sub(pattern, f"\\g<1>{target_f:,.0f} N (originally {base_f:,.0f} N in the source environment);", criteria)
    if target_t != base_t:
        pattern = r"(- \*\*Internal Joint Limits\*\*:.*?max torque )([\d,]+)( N·m )(?:\(originally [^)]+\) )?\("
        criteria = re.sub(pattern, f"\\g<1>{target_t:,.0f} N·m (originally {base_t:,.0f} N·m in the source environment) (", criteria)

    # Update Wall Anchor Limits in Success Criteria (cascading-safe)
    default_anchor = 100000000.0
    target_af = target_terrain_config.get("max_anchor_force", default_anchor)
    base_af = base_terrain_config.get("max_anchor_force", default_anchor)
    target_at = target_terrain_config.get("max_anchor_torque", default_anchor)
    base_at = base_terrain_config.get("max_anchor_torque", default_anchor)
    if target_af != base_af or target_at != base_at:
        # Replacement uses literal " N·m " so trailing clause appears once (no duplicate from \g<5>)
        pattern_wa = r"(- \*\*Wall Anchor Limits\*\*: Max force )([\d,]+)( N; max torque )([\d,]+)( N·m )(?:\(originally [^)]+\) )?\(exceeding causes failure\)\."
        if re.search(pattern_wa, criteria):
            criteria = re.sub(
                pattern_wa,
                f"\\g<1>{target_af:,.0f}\\g<3>{target_at:,.0f} N·m (originally {base_af:,.0f} N and {base_at:,.0f} N·m in the source environment) (exceeding causes failure).",
                criteria,
            )
    
    # Update Minimum Tip Height in Success Criteria (cascading-safe)
    target_mth = target_terrain_config.get("min_tip_height_limit", -15.0)
    base_mth = base_terrain_config.get("min_tip_height_limit", -15.0)
    if target_mth != base_mth:
        pattern_mth = r"(y >= )(-?\d+\.?\d*)( m\))(?: \(originally [^)]+\))?\.?"
        if re.search(pattern_mth, criteria):
            criteria = re.sub(pattern_mth, f"\\g<1>{target_mth:.1f} m) (originally {base_mth:.1f} m in the source environment).", criteria)
    
    # Update Reach Tolerance in Success Criteria (cascading-safe)
    default_tol = 1.0
    target_tol = float(target_terrain_config.get("reach_tolerance", default_tol))
    base_tol = float(base_terrain_config.get("reach_tolerance", default_tol))
    if target_tol != base_tol:
        pattern_tol = r"(- \*\*Reach Tolerance\*\*: Under load, tip x may be up to )(\d+\.?\d*)( m )(?:\(originally [^)]+\) )?short of target and still satisfy reach\.?"
        if re.search(pattern_tol, criteria):
            criteria = re.sub(pattern_tol, f"\\g<1>{target_tol:.1f} m (originally {base_tol:.1f} m in the source environment) short of target and still satisfy reach.", criteria)

    # Update Forbidden Anchor Zones in Success Criteria (match initial or already-updated)
    target_forbidden = target_terrain_config.get("forbidden_anchor_y")
    base_forbidden = base_terrain_config.get("forbidden_anchor_y")
    if target_forbidden is not None and len(target_forbidden) >= 2:
        y_min, y_max = float(target_forbidden[0]), float(target_forbidden[1])
        base_str = "none"
        if base_forbidden is not None and len(base_forbidden) >= 2:
            base_str = f"y = [{float(base_forbidden[0]):.1f}, {float(base_forbidden[1]):.1f}] m"
        pattern_initial = r"(- \*\*Forbidden Anchor Zones\*\*: )None in the source environment\."
        pattern_updated = r"(- \*\*Forbidden Anchor Zones\*\*: )y = \[[^\]]+\] m forbidden \(originally [^)]+\)\."
        replacement = f"\\g<1>y = [{y_min:.1f}, {y_max:.1f}] m forbidden (originally {base_str} in the source environment)."
        if re.search(pattern_initial, criteria):
            criteria = re.sub(pattern_initial, replacement, criteria)
        elif re.search(pattern_updated, criteria):
            criteria = re.sub(pattern_updated, replacement, criteria)

    # Update Regional anchor strength in Success Criteria (anchor_strength_map)
    target_strength_map = target_terrain_config.get("anchor_strength_map", None)
    base_strength_map = base_terrain_config.get("anchor_strength_map", None)
    if target_strength_map and len(target_strength_map) > 0:
        parts = []
        for entry in target_strength_map:
            if len(entry) >= 4:
                y_lo, y_hi, f_mult, t_mult = float(entry[0]), float(entry[1]), float(entry[2]), float(entry[3])
                parts.append(f"y = [{y_lo:.1f}, {y_hi:.1f}] m at {f_mult*100:.2f}%/{t_mult*100:.2f}%")
        if parts:
            strength_desc = "; ".join(parts)
            base_str = "none in the source environment"
            if base_strength_map and len(base_strength_map) > 0 and len(base_strength_map[0]) >= 4:
                be = base_strength_map[0]
                base_str = f"y = [{float(be[0]):.1f}, {float(be[1]):.1f}] m at {float(be[2])*100:.2f}%/{float(be[3])*100:.2f}% in the source environment"
            pattern_ra = r"(- \*\*Regional anchor strength\*\*: )None in the source environment; when present, the vertical segment and force/torque multipliers are stated\.?"
            pattern_ra_updated = r"(- \*\*Regional anchor strength\*\*: ).*? \(originally [^)]+\)\.?"
            repl_ra = f"\\g<1>{strength_desc} (originally {base_str})."
            if re.search(pattern_ra, criteria):
                criteria = re.sub(pattern_ra, repl_ra, criteria)
            elif re.search(pattern_ra_updated, criteria):
                criteria = re.sub(pattern_ra_updated, repl_ra, criteria)

    # Update Payload application in Success Criteria (load_type/drop_height)
    target_load_type = target_terrain_config.get("load_type", "static")
    base_load_type = base_terrain_config.get("load_type", "static")
    target_drop = float(target_terrain_config.get("drop_height", 10.0))
    if target_load_type == "dropped":
        pattern_payload = r"(- \*\*Payload application\*\*: )Static \(placed on structure at the given times\) in the source environment\.?"
        if re.search(pattern_payload, criteria):
            criteria = re.sub(
                pattern_payload,
                f"\\g<1>Dropped from {target_drop:.1f} m height (originally static in the source environment).",
                criteria,
            )
    elif base_load_type == "dropped":
        pattern_dropped = r"(- \*\*Payload application\*\*: )Dropped from [\d.]+ m height \(originally static in the source environment\)\.?"
        if re.search(pattern_dropped, criteria):
            criteria = re.sub(pattern_dropped, "\\g<1>Static (placed on structure at the given times) in the source environment.", criteria)
        
    return criteria


def get_s03_curriculum_stages() -> List[Dict[str, Any]]:
    # Define the stages first without the suffix
    stages_data = [
        {
            "stage_id": "Stage-1",
            "title": "The Brittle Connections",
            "mutation_description": "Single Variable: Extreme internal joint fragility.",
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
            "title": "The Fragile Anchors",
            "mutation_description": "Single Variable: Severely reduced wall anchor capacity. Wall anchors fail at force and torque thresholds far below standard conditions; the resulting root reaction from any conventional long cantilever exceeds these limits. Standard solutions fail when anchor force or torque exceeds the new critical threshold. The agent must discover the fragile anchors through failure (anchor break at the wall) and adapt—e.g. a much shorter moment arm, a stiffer root, or a design that keeps reaction force and torque at the wall below the critical threshold.",
            "terrain_config": {
                "max_anchor_force": 68000.0,
                "max_anchor_torque": 58000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Subterranean Gorge",
            "mutation_description": "Multi-variable: Overhead Obstacle + Low Anchor Zone + Attraction Field + Weak Anchors. Forces low-slung, heavily reinforced construction.",
            "terrain_config": {
                "target_reach": 32.0,
                "load_mass": 1200.0,
                "max_structure_mass": 12000.0,
                "forbidden_anchor_y": [-2.0, 30.0],
                "anchor_strength_map": [[-20.0, -12.0, 0.2, 0.2]],
                "obstacle_active": True,
                "obstacle_rects": [
                    [0.0, 4.0, 25.0, 30.0],
                ],
            },
            "physics_config": {
                "spatial_force": {
                    "center": (16.0, -12.0),
                    "magnitude": 1500000.0,
                    "radius": 20.0,
                    "type": "attraction"
                },
                "wind": {
                    "force": (1200.0, 0),
                    "oscillatory": True,
                    "frequency": 0.4
                }
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Multi-variable: Fragile joints + Repulsion Field + Forbidden Wall + Dropped Loads + Oscillatory Wind.",
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

    # Map variables to their descriptions
    variable_descriptions = {
        "target_reach": "**Operational Range**: The required horizontal extension (Target Reach) from the anchor wall may have been significantly adjusted.",
        "load_mass": "**Structural Load Capacity**: The target load mass may have been tuned to test extreme material efficiency.",
        "max_structure_mass": "**Mass Budget**: The total structural mass budget may be constrained.",
        "max_internal_force": "**Joint Integrity Thresholds**: The maximum force that internal (beam-to-beam) joints can withstand may differ significantly from standard conditions.",
        "max_internal_torque": "**Joint Torque Thresholds**: The maximum torque internal joints can endure may differ significantly from standard conditions.",
        "max_anchor_force": "**Wall Anchor Force Limit**: The maximum force wall anchors can sustain before failure may differ significantly from standard conditions.",
        "max_anchor_torque": "**Wall Anchor Torque Limit**: The maximum torque wall anchors can sustain before failure may differ significantly from standard conditions.",
        "anchor_strength_map": "**Regional Anchor Weakness**: Certain vertical segments of the wall may exhibit structural integrity that differs from standard conditions, affecting anchor stability.",
        "forbidden_anchor_y": "**Forbidden Anchor Zones**: Specific vertical segments of the wall may be restricted from attaching anchors.",
        "obstacle_active": "**Static Obstructions**: Massive, impenetrable structures might be present in the build zone, necessitating complex geometries to navigate around them.",
        "obstacle_rects": "**Obstacle Layout**: The specific coordinates and dimensions of static obstructions in the environment may vary.",
        "load_type": "**Dynamic Load Impacts**: The payload might be dropped from a height rather than being placed statically, introducing severe impulse forces.",
        "drop_height": "**Payload Drop Height**: The height from which payloads are dropped may vary.",
        "spatial_force": "**Localized Force Fields**: Invisible spatial anomalies might exert powerful repulsive or attractive forces on any structure within their radius of influence.",
        "wind": "**Atmospheric Oscillations**: Variable or oscillatory wind forces may act on the structure, inducing complex dynamic stresses."
    }

    # Dynamically extract the union of mutated variables
    mutated_keys = set()
    for stage in stages_data:
        terrain = stage.get("terrain_config", {})
        physics = stage.get("physics_config", {})
        mutated_keys.update(terrain.keys())
        mutated_keys.update(physics.keys())

    # Build the suffix text
    suffix_lines = [
        "## Environmental Anomalies Detected",
        "Sensors indicate that this region exhibits non-standard physical properties.",
        "While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:"
    ]
    
    for key in sorted(mutated_keys):
        if key in variable_descriptions:
            suffix_lines.append(f" - {variable_descriptions[key]}")

    suffix_lines.append("")
    suffix_lines.append("**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.")
    
    uniform_suffix = "\n".join(suffix_lines)

    # Assign suffix back to stages
    for stage in stages_data:
        stage["task_description_suffix"] = uniform_suffix

    return stages_data
