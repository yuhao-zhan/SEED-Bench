import math

def build_agent(sandbox):
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

def agent_action(sandbox, agent_body, step_count):
    if step_count != 0:
        return
    vx, vy = 10.0, 15.9
    sandbox.set_jumper_velocity(vx, vy)
