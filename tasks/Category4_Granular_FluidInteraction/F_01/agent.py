"""
F-01: The Dam task Agent module (three-strip bridge variant)
Reference: ONE connected structure using all THREE strips — left column (8 beams), ONE middle
bridge beam (x=[12.9,13.1]), right column (2 beams). Two cross-joints: left–middle and middle–right.
At most 11 beam-to-beam joints; min 3 beams per band; middle strip at most 1 beam; right strip at most 2; leakage <= 0.1%.
"""


def build_agent(sandbox):
    """
    Build one connected dam: left column (8 beams), one middle bridge beam, right column (2 beams).
    Joints: 7 (left) + 1 (right) + 2 (left–middle, middle–right) = 10 <= 11.
    Bands: [0.5,2.5] and [2.5,5] get 3 left + 1 right each; [5,7.5] gets 2 left + 1 middle.
    """
    x_left = 12.5
    x_middle = 13.0
    x_right = 13.5
    beam_w = min(0.6, getattr(sandbox, 'MAX_BEAM_WIDTH', 0.6))
    max_h = getattr(sandbox, 'MAX_BEAM_HEIGHT', 1.5)
    min_bottom_y = getattr(sandbox, 'MIN_BEAM_BOTTOM_Y', 0.5)
    density = 46.0

    # Left column: 8 beams, height 0.7 — bands [0.5,2.5] 3, [2.5,5] 3, [5,7.5] 2
    left_layer_h = min(0.7, max_h)
    left_n = 8
    left_first_y = min_bottom_y + left_layer_h / 2
    left_beams = []
    for i in range(left_n):
        cy = left_first_y + i * left_layer_h
        b = sandbox.add_beam(x_left, cy, width=beam_w, height=left_layer_h, angle=0, density=density)
        sandbox.set_material_properties(b, restitution=0.05)
        left_beams.append(b)
    for i in range(1, left_n):
        y_anchor = (left_beams[i].position.y + left_beams[i - 1].position.y) / 2
        sandbox.add_joint(left_beams[i], left_beams[i - 1], (x_left, y_anchor), type='rigid')

    # Middle strip: exactly 1 beam (bridge) at x=13.0, y in [5,7.5] so band [5,7.5] has 3 beams
    middle_h = min(0.6, max_h)
    middle_y = 6.0
    middle_beam = sandbox.add_beam(x_middle, middle_y, width=beam_w, height=middle_h, angle=0, density=density)
    sandbox.set_material_properties(middle_beam, restitution=0.05)

    # Right column: 2 beams, height 1.5 — both in lower bands
    right_layer_h = min(1.5, max_h)
    right_n = 2
    right_first_y = min_bottom_y + right_layer_h / 2
    right_beams = []
    for i in range(right_n):
        cy = right_first_y + i * right_layer_h
        b = sandbox.add_beam(x_right, cy, width=beam_w, height=right_layer_h, angle=0, density=density)
        sandbox.set_material_properties(b, restitution=0.05)
        right_beams.append(b)
    sandbox.add_joint(right_beams[1], right_beams[0], (x_right, (right_beams[1].position.y + right_beams[0].position.y) / 2), type='rigid')

    # Cross-joint 1: left (top of left column, index 7, y~5.75) to middle — anchor between them
    anchor_left_mid_x = (x_left + x_middle) / 2
    anchor_left_mid_y = (left_beams[7].position.y + middle_beam.position.y) / 2
    sandbox.add_joint(left_beams[7], middle_beam, (anchor_left_mid_x, anchor_left_mid_y), type='rigid')

    # Cross-joint 2: middle to right (connect to top right beam index 1 for stability)
    anchor_mid_right_x = (x_middle + x_right) / 2
    anchor_mid_right_y = (middle_beam.position.y + right_beams[1].position.y) / 2
    sandbox.add_joint(middle_beam, right_beams[1], (anchor_mid_right_x, anchor_mid_right_y), type='rigid')

    # Cross-joint 3: bottom A-frame — left[0] to right[0] for better seal (11 joints total)
    cross_anchor_y = (left_beams[0].position.y + right_beams[0].position.y) / 2
    sandbox.add_joint(left_beams[0], right_beams[0], (13.0, cross_anchor_y), type='rigid')

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    if len(sandbox.bodies) > sandbox.MAX_BEAM_COUNT:
        raise ValueError(f"Beam count {len(sandbox.bodies)} exceeds maximum {sandbox.MAX_BEAM_COUNT}")
    right_count = sum(1 for b in sandbox.bodies
                     if getattr(sandbox, 'BUILD_ZONE_RIGHT_X_MIN', 13.4) <= b.position.x <= getattr(sandbox, 'BUILD_ZONE_RIGHT_X_MAX', 13.6))
    if right_count > getattr(sandbox, 'MAX_BEAMS_RIGHT_STRIP', 2):
        raise ValueError(f"Right strip has {right_count} beams; at most {sandbox.MAX_BEAMS_RIGHT_STRIP} allowed")
    middle_count = sum(1 for b in sandbox.bodies
                      if getattr(sandbox, 'BUILD_ZONE_MIDDLE_X_MIN', 12.9) <= b.position.x <= getattr(sandbox, 'BUILD_ZONE_MIDDLE_X_MAX', 13.1))
    if middle_count > getattr(sandbox, 'MAX_BEAMS_MIDDLE_STRIP', 1):
        raise ValueError(f"Middle strip has {middle_count} beams; at most {sandbox.MAX_BEAMS_MIDDLE_STRIP} allowed")
    terrain_count = sandbox.get_terrain_joint_count()
    if terrain_count > sandbox.MAX_TERRAIN_ANCHORS:
        raise ValueError(f"Terrain anchors {terrain_count} exceeds maximum {sandbox.MAX_TERRAIN_ANCHORS}")
    beam_joints = len(sandbox.joints) - terrain_count
    if beam_joints > getattr(sandbox, 'MAX_JOINT_COUNT', 11):
        raise ValueError(f"Beam-to-beam joint count {beam_joints} exceeds maximum {sandbox.MAX_JOINT_COUNT}")

    return left_beams[0]


def agent_action(sandbox, agent_body, step_count):
    pass
