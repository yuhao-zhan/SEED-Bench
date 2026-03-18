# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Base foundation (4m wide, 0.1m height)
    base = sandbox.add_beam(x=0, y=0, width=4, height=0.1, angle=0, density=1.0)
    
    # Vertical column segments (0.5m width, 10m height each)
    column1 = sandbox.add_beam(x=0, y=0, width=0.5, height=10, angle=0, density=2.0)
    column2 = sandbox.add_beam(x=0, y=10, width=0.5, height=10, angle=0, density=2.0)
    column3 = sandbox.add_beam(x=0, y=20, width=0.5, height=10, angle=0, density=2.0)
    column4 = sandbox.add_beam(x=0, y=30, width=0.5, height=5, angle=0, density=2.0)
    
    # Connect vertical columns with rigid joints
    sandbox.add_joint(column1, column2, (0, 10), type='rigid')
    sandbox.add_joint(column2, column3, (0, 20), type='rigid')
    sandbox.add_joint(column3, column4, (0, 30), type='rigid')
    
    # Cross bracing at 10m, 20m, 30m heights
    brace1 = sandbox.add_beam(x=-2, y=10, width=4, height=0.2, angle=0, density=1.5)
    sandbox.add_joint(brace1, column1, (-0.25, 10), type='rigid')
    sandbox.add_joint(brace1, column1, (0.25, 10), type='rigid')
    
    brace2 = sandbox.add_beam(x=-2, y=20, width=4, height=0.2, angle=0, density=1.5)
    sandbox.add_joint(brace2, column2, (-0.25, 20), type='rigid')
    sandbox.add_joint(brace2, column2, (0.25, 20), type='rigid')
    
    brace3 = sandbox.add_beam(x=-2, y=30, width=4, height=0.2, angle=0, density=1.5)
    sandbox.add_joint(brace3, column3, (-0.25, 30), type='rigid')
    sandbox.add_joint(brace3, column3, (0.25, 30), type='rigid')
    
    # Tuned Mass Damper (TMD) at 35m height
    tmd = sandbox.add_beam(x=0, y=35, width=2, height=0.5, angle=0, density=5.0)
    # Spring-damper connection between column4 and TMD
    spring = sandbox.add_spring(column4, tmd, (0, 35), (0, 35), stiffness=400, damping=0.3)
    
    return column4  # Return main vertical column as the agent body

def agent_action(sandbox, agent_body, step_count):
    # No active control needed - passive damping system handles all forces
    pass
# EVOLVE-BLOCK-END