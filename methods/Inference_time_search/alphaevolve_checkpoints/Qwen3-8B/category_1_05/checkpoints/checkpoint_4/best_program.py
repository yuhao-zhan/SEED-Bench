# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Add vertical columns around the Core
    columns = []
    # Create columns at (1.3, 0), (-1.3, 0), (0, 1.3), (0, -1.3)
    for dx, dy in [(1.3, 0), (-1.3, 0), (0, 1.3), (0, -1.3)]:
        column = sandbox.add_beam(x=dx, y=2.25, width=0.5, height=4.5, density=1.0)
        columns.append(column)
        sandbox.set_material_properties(column, restitution=0.2)
    
    # Add horizontal beams at y=4.5m connecting columns
    # Beam between (1.3, 0) and (-1.3, 0)
    horizontal_beam = sandbox.add_beam(x=0, y=4.25, width=2.6, height=0.5, density=1.0)
    sandbox.set_material_properties(horizontal_beam, restitution=0.2)
    
    # Connect horizontal beam to columns
    for i, col in enumerate(columns):
        if i == 0 or i == 1:  # Columns at (1.3, 0) and (-1.3, 0)
            anchor_x = col.x
            anchor_y = 4.5
            joint = sandbox.add_joint(col, horizontal_beam, anchor_point=(anchor_x, anchor_y), type='rigid')
    
    # Add vertical beam connecting (0, 1.3) and (0, -1.3)
    vertical_beam = sandbox.add_beam(x=0, y=2.25, width=2.6, height=0.5, density=1.0)
    sandbox.set_material_properties(vertical_beam, restitution=0.2)
    
    # Connect vertical beam to columns
    for i, col in enumerate(columns):
        if i == 2 or i == 3:  # Columns at (0, 1.3) and (0, -1.3)
            anchor_x = 0
            anchor_y = 4.5
            joint = sandbox.add_joint(col, vertical_beam, anchor_point=(anchor_x, anchor_y), type='rigid')
    
    return columns[0]  # Return any body for reference

def agent_action(sandbox, agent_body, step_count):
    # No control needed; structure is static
    pass
# EVOLVE-BLOCK-END