# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Main beam connecting to load at (3, 0)
    main_beam = sandbox.add_beam(x=1.5, y=0, width=3, height=0.2, angle=0, density=1.0)
    
    # Counterweight beam to balance the load
    counterweight_beam = sandbox.add_beam(x=-2, y=0, width=4, height=0.2, angle=0, density=375)
    
    # Connect both beams to the pivot at (0, 0)
    sandbox.add_joint(main_beam, 'pivot', (0, 0), type='pivot')
    sandbox.add_joint(counterweight_beam, 'pivot', (0, 0), type='pivot')
    
    return main_beam

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END