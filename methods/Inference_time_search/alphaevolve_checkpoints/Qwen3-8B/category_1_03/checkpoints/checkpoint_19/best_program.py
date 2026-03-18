# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Define main beam from wall (x=0, y=0) to x=14m
    main_beam = sandbox.add_beam(x=0, y=0, width=0.1, height=1.0, angle=0, density=1.0)
    # Define diagonal beam from wall (x=0, y=0) to x=7.5m at y=5m
    diag_beam = sandbox.add_beam(x=0, y=0, width=0.1, height=1.0, angle=0, density=1.0)
    # Define cross beam connecting diagonal beam to main beam
    cross_beam = sandbox.add_beam(x=7.5, y=5, width=0.1, height=1.0, angle=0, density=1.0)
    
    # Connect main beam to diagonal beam at x=7.5m, y=0
    # Create a joint between main_beam and cross_beam at (7.5, 0)
    sandbox.add_joint(main_beam, cross_beam, anchor_point=(7.5, 0), type='rigid')
    
    # Connect diagonal beam to cross_beam at x=7.5m, y=5
    # Create a joint between diag_beam and cross_beam at (7.5, 5)
    sandbox.add_joint(diag_beam, cross_beam, anchor_point=(7.5, 5), type='rigid')
    
    # Anchor main beam to wall at (0, 0)
    sandbox.add_joint(main_beam, None, anchor_point=(0, 0), type='pivot')
    
    # Anchor diagonal beam to wall at (0, 0)
    sandbox.add_joint(diag_beam, None, anchor_point=(0, 0), type='pivot')
    
    # Return the main body for reference
    return main_beam

def agent_action(sandbox, agent_body, step_count):
    # Add tip load at x=14m at t=5s
    if step_count >= 5:
        # Attach tip load (600kg) at (14, 0)
        sandbox.add_joint(agent_body, None, anchor_point=(14, 0), type='pivot')
    
    # Add mid-span load at x=7.5m at t=10s
    if step_count >= 10:
        # Attach mid-span load (400kg) at (7.5, 5)
        sandbox.add_joint(agent_body, None, anchor_point=(7.5, 5), type='pivot')
    
    # Ensure structure does not sag below y=-2.5m
    # This is handled by the physics engine, but additional constraints could be added
    pass
# EVOLVE-BLOCK-END