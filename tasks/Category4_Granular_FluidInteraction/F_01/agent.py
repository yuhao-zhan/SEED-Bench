def build_agent(sandbox):
    x_left = 12.5
    x_middle = 13.0
    x_right = 13.5
    beam_w = sandbox.MAX_BEAM_WIDTH
    max_h = sandbox.MAX_BEAM_HEIGHT
    min_bottom_y = sandbox.MIN_BEAM_BOTTOM_Y
    density = 46.0
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
    middle_h = min(0.6, max_h)
    middle_y = 6.0
    middle_beam = sandbox.add_beam(x_middle, middle_y, width=beam_w, height=middle_h, angle=0, density=density)
    sandbox.set_material_properties(middle_beam, restitution=0.05)
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
    top_left = left_beams[-1]
    anchor_left_mid_x = (x_left + x_middle) / 2
    anchor_left_mid_y = (top_left.position.y + middle_beam.position.y) / 2
    sandbox.add_joint(top_left, middle_beam, (anchor_left_mid_x, anchor_left_mid_y), type='rigid')
    anchor_mid_right_x = (x_middle + x_right) / 2
    anchor_mid_right_y = (middle_beam.position.y + right_beams[1].position.y) / 2
    sandbox.add_joint(middle_beam, right_beams[1], (anchor_mid_right_x, anchor_mid_right_y), type='rigid')
    cross_anchor_y = (left_beams[0].position.y + right_beams[0].position.y) / 2
    sandbox.add_joint(left_beams[0], right_beams[0], (13.0, cross_anchor_y), type='rigid')
    return left_beams[0]

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    return _build_baseline_topology_dam(sandbox, density=41.0)

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    return _build_baseline_topology_dam(sandbox, density=26.0)

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    return _build_baseline_topology_dam(sandbox, density=41.0)

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    return _build_baseline_topology_dam(sandbox, density=33.0)

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass

def _build_baseline_topology_dam(sandbox, density):
    x_left = 12.5
    x_middle = 13.0
    x_right = 13.5
    beam_w = sandbox.MAX_BEAM_WIDTH
    max_h = sandbox.MAX_BEAM_HEIGHT
    min_bottom_y = sandbox.MIN_BEAM_BOTTOM_Y
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
    middle_h = min(0.6, max_h)
    middle_y = 6.0
    middle_beam = sandbox.add_beam(x_middle, middle_y, width=beam_w, height=middle_h, angle=0, density=density)
    sandbox.set_material_properties(middle_beam, restitution=0.05)
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
    top_left = left_beams[-1]
    anchor_left_mid_x = (x_left + x_middle) / 2
    anchor_left_mid_y = (top_left.position.y + middle_beam.position.y) / 2
    sandbox.add_joint(top_left, middle_beam, (anchor_left_mid_x, anchor_left_mid_y), type='rigid')
    anchor_mid_right_x = (x_middle + x_right) / 2
    anchor_mid_right_y = (middle_beam.position.y + right_beams[1].position.y) / 2
    sandbox.add_joint(middle_beam, right_beams[1], (anchor_mid_right_x, anchor_mid_right_y), type='rigid')
    cross_anchor_y = (left_beams[0].position.y + right_beams[0].position.y) / 2
    sandbox.add_joint(left_beams[0], right_beams[0], (13.0, cross_anchor_y), type='rigid')
    return left_beams[0]
