import math

def _base_build_agent(sandbox):
    jumper = sandbox.get_jumper()
    if jumper is None:
        raise ValueError("Jumper not found in environment")
    pad = sandbox.add_beam(
        x=5.0,
        y=2.75,
        width=1.0,
        height=0.2,
        angle=0,
        density=40.0,
    )
    sandbox.set_material_properties(pad, restitution=0.2)
    sandbox.add_joint(pad, None, (5.0, 2.75), type="rigid")
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(
            f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg"
        )
    return jumper

def build_agent(sandbox):
    return _base_build_agent(sandbox)

def agent_action(sandbox, agent_body, step_count):
    if step_count != 0:
        return
    vx, vy = 10.0, 15.9
    sandbox.set_jumper_velocity(vx, vy)

def build_agent_stage_1(sandbox):
    return _base_build_agent(sandbox)

def agent_action_stage_1(sandbox, agent_body, step_count):
    if step_count != 0:
        return
    vx, vy = 55.33, 43.95
    sandbox.set_jumper_velocity(vx, vy)

def build_agent_stage_2(sandbox):
    return _base_build_agent(sandbox)

def agent_action_stage_2(sandbox, agent_body, step_count):
    if step_count != 0:
        return
    vx, vy = 82.95, 44.86
    sandbox.set_jumper_velocity(vx, vy)

def build_agent_stage_3(sandbox):
    return _base_build_agent(sandbox)

def agent_action_stage_3(sandbox, agent_body, step_count):
    if step_count != 0:
        return
    vx, vy = 115.87, 98.24
    sandbox.set_jumper_velocity(vx, vy)

def build_agent_stage_4(sandbox):
    return _base_build_agent(sandbox)

def agent_action_stage_4(sandbox, agent_body, step_count):
    if step_count != 0:
        return
    vx, vy = 74.47, 63.77
    sandbox.set_jumper_velocity(vx, vy)
