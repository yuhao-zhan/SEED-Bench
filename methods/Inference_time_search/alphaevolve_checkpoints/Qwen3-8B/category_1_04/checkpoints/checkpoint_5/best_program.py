# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Create a static pivot body at (0,0) with zero density
    pivot_body = sandbox.add_beam(x=0, y=0, width=0.05, height=0.05, angle=0, density=0.0)
    
    # Main beam connecting pivot to load at (3,0)
    main_beam = sandbox.add_beam(x=0, y=0, width=3, height=0.1, angle=0, density=1.0)
    
    # Counter-weight beam extending from pivot to left
    counter_beam = sandbox.add_beam(x=-6, y=0, width=0.2, height=0.1, angle=0, density=5101.5)
    
    # Connect main beam to pivot with rigid joint
    sandbox.add_joint(main_beam, pivot_body, anchor_point=(0,0), type='rigid')
    
    # Connect counter-weight beam to pivot with rigid joint
    sandbox.add_joint(counter_beam, pivot_body, anchor_point=(0,0), type='rigid')
    
    return main_beam

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END