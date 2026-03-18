# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Create deck beam spanning the gap (x=10 to x=25, y=12.5)
    deck = sandbox.add_beam(17.5, 12.5, 15, 0.5, density=1.0)
    
    # Create vertical supports anchored to cliffs
    left_support = sandbox.add_beam(10, 11.25, 0.5, 2.5, density=1.0)
    right_support = sandbox.add_beam(25, 11.25, 0.5, 2.5, density=1.0)
    
    # Connect vertical supports to cliffs (assuming static bodies exist at cliff positions)
    sandbox.add_joint(left_support, None, (10, 10), type='rigid')
    sandbox.add_joint(right_support, None, (25, 10), type='rigid')
    
    # Connect deck to vertical supports
    sandbox.add_joint(deck, left_support, (10, 12.5), type='rigid')
    sandbox.add_joint(deck, right_support, (25, 12.5), type='rigid')
    
    return deck

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END