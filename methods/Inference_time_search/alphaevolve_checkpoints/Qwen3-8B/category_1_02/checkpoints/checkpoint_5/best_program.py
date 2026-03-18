# EVOLVE-BLOCK-START
def build_agent(sandbox):
    base = sandbox.add_beam(x=-2, y=0, width=4, height=1, density=1.0)
    current_y = 1
    last_beam = base
    for i in range(1, 31):  # Add 30 upper beams to reach 31m height
        width = 4 - i
        if width < 0.1:
            width = 0.1
        beam = sandbox.add_beam(x=-2, y=current_y, width=width, height=1, density=1.0)
        last_beam = beam
        current_y += 1
    # Add TMD at the top of the tower
    tmd = sandbox.add_beam(x=-2, y=31, width=1, height=1, density=1.0)
    # Connect TMD to the main tower with spring and damper
    # Calculate anchor points for spring connection
    tmd_anchor = (-2 + 0.5, 31.5)  # Center of TMD
    last_beam_anchor = (-2 + last_beam.width / 2, 30.5)  # Center of last main beam
    spring = sandbox.add_spring(
        body_a=tmd, body_b=last_beam,
        anchor_a=tmd_anchor, anchor_b=last_beam_anchor,
        stiffness=4, damping=2
    )
    return base

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END