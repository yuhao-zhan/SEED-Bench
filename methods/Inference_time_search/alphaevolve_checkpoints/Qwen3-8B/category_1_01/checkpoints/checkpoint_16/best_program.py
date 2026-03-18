# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Create a horizontal beam spanning from x=10 to x=25 (15m)
    # The beam's center is at x= (10 + 25)/2 = 17.5m, y=10m
    beam = sandbox.add_beam(x=17.5, y=10, width=2, height=0.5, angle=0, density=1.0)
    # Connect to the left cliff at x=10, y=10
    left_cliff_joint = sandbox.add_joint(beam, None, (10, 10), type='rigid')
    # Connect to the right cliff at x=25, y=10
    right_cliff_joint = sandbox.add_joint(beam, None, (25, 10), type='rigid')
    # Set material properties to have low restitution (to reduce bouncing)
    sandbox.set_material_properties(beam, restitution=0.2)
    return beam

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END