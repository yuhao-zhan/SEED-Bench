def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria when stage has visible changes."""
    criteria = base_success_criteria
    
    # Target particle count
    target_count = target_terrain_config.get("min_particles_in_hopper", 15) # Default 15
    base_count = base_terrain_config.get("min_particles_in_hopper", 15)
    
    if target_count != base_count:
        pattern = r"(1\. \*\*Material Transfer\*\*: At least )(\d+)( sand particles are deposited in the hopper zone \(x=\[-6\.0, -4\.0\] m, y=\[0\.5, 5\.0\] m; center at x=-5\.0, y=3\.0\)\.)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{target_count} (originally {base_count} in the source environment)\\g<3>",
            criteria
        )
    
    # Hopper zone bounds in success criteria
    hvx_min = float(target_terrain_config.get("hopper_valid_x_min", -6.0))
    hvx_max = float(target_terrain_config.get("hopper_valid_x_max", -4.0))
    hvy_min = float(target_terrain_config.get("hopper_valid_y_min", 0.5))
    hvy_max = float(target_terrain_config.get("hopper_valid_y_max", 5.0))
    
    bvx_min = float(base_terrain_config.get("hopper_valid_x_min", -6.0))
    bvx_max = float(base_terrain_config.get("hopper_valid_x_max", -4.0))
    bvy_min = float(base_terrain_config.get("hopper_valid_y_min", 0.5))
    bvy_max = float(base_terrain_config.get("hopper_valid_y_max", 5.0))
    
    if (hvx_min != bvx_min or hvx_max != bvx_max or hvy_min != bvy_min or hvy_max != bvy_max):
        # Update both the x and y ranges in the success criteria string
        pattern = r"(deposited in the hopper zone \(x=\[)([^\]]+)(\] m, y=\[)([^\]]+)(\] m; center at x=-5\.0, y=3\.0\)\.)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{hvx_min}, {hvx_max}\\g<3>{hvy_min}, {hvy_max}] (originally x=[{bvx_min}, {bvx_max}], y=[{bvy_min}, {bvy_max}] in the source environment) m; center at x=-5.0, y=3.0).",
            criteria
        )
        
    return criteria
