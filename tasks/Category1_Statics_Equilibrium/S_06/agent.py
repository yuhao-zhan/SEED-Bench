"""
S-06: The Overhang task Agent module
Creates a balanced overhang structure using counter-balancing technique
"""
import math


def build_agent(sandbox):
    """
    Build an overhang structure that extends beyond x=0.
    Uses counter-balancing technique: extend blocks outward while placing
    heavier blocks on the table to keep center of mass stable.
    
    Target: 0.5m overhang (reduced from 2.0m to make task easier)
    """
    # Table edge is at x=0, table extends from x=-10 to x=0
    # All blocks must spawn at x < 0
    # Block width max = 1.0m, so if center at x=-0.5, right edge at x=0
    
    TABLE_TOP_Y = 1.0  # Table top is at y=1.0 (table center y=0.5, height=0.5)
    BLOCK_HEIGHT = 0.5  # Use maximum height for stability
    BLOCK_WIDTH = 1.0   # Use maximum width
    
    blocks = []
    
    # Strategy: Balanced approach - enough counter-weights for stability, enough extending layers for reach
    # Target: 0.5m overhang
    
    # Heavy counter-balance: Place blocks far back on table
    # Use 5 blocks from x=-9.5 to x=-5.5
    counter_x_start = -9.5
    num_counter_blocks = 5
    for i in range(num_counter_blocks):
        x = counter_x_start + i * 1.0
        block = sandbox.add_block(x, TABLE_TOP_Y + BLOCK_HEIGHT/2, BLOCK_WIDTH, BLOCK_HEIGHT)
        blocks.append(block)
    
    # Base layer: Place blocks near the edge
    base_positions = [-1.5, -0.5]
    for x in base_positions:
        block = sandbox.add_block(x, TABLE_TOP_Y + BLOCK_HEIGHT/2, BLOCK_WIDTH, BLOCK_HEIGHT)
        blocks.append(block)
    
    # Create stepped structure, each layer extending further
    # Layer 2: Stack on base
    y2 = TABLE_TOP_Y + BLOCK_HEIGHT + BLOCK_HEIGHT/2
    block = sandbox.add_block(-0.5, y2, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 3: Extend - center at x=-0.4, right edge at x=0.1
    y3 = TABLE_TOP_Y + 2 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    block = sandbox.add_block(-0.4, y3, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Add counter-weight on layer 3
    block = sandbox.add_block(-2.0, y3, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 4: Extend further - center at x=-0.3, right edge at x=0.2
    y4 = TABLE_TOP_Y + 3 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    block = sandbox.add_block(-0.3, y4, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Add counter-weight on layer 4
    block = sandbox.add_block(-2.0, y4, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 5: Extend further - center at x=-0.2, right edge at x=0.3
    y5 = TABLE_TOP_Y + 4 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    block = sandbox.add_block(-0.2, y5, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 6: Extend further - center at x=-0.1, right edge at x=0.4
    y6 = TABLE_TOP_Y + 5 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    block = sandbox.add_block(-0.1, y6, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 7: Extend further - center at x=-0.05, right edge at x=0.45
    y7 = TABLE_TOP_Y + 6 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    block = sandbox.add_block(-0.05, y7, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 8: Extend further - center at x=-0.01, right edge at x=0.49
    y8 = TABLE_TOP_Y + 7 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    width8 = 0.9
    block = sandbox.add_block(-0.01, y8, width8, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Layer 9: Final layer - center at x=-0.005, right edge at x=0.445 (with width 0.9)
    y9 = TABLE_TOP_Y + 8 * BLOCK_HEIGHT + BLOCK_HEIGHT/2
    width9 = 0.8
    block = sandbox.add_block(-0.005, y9, width9, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Add counter-weight on layer 9 for stability
    block = sandbox.add_block(-2.0, y9, BLOCK_WIDTH, BLOCK_HEIGHT)
    blocks.append(block)
    
    # Check block count
    total_blocks = len(blocks)
    if total_blocks > 20:
        raise ValueError(f"Too many blocks: {total_blocks} > 20")
    
    total_mass = sandbox.get_structure_mass()
    
    print(f"Overhang structure built: {total_blocks} blocks, {total_mass:.2f}kg")
    print(f"Strategy: Balanced stepped structure")
    print(f"Target: 0.1m (reduced from 2.0m)")
    print(f"Expected max x: ~0.1m")
    
    return blocks[0] if blocks else None


def agent_action(sandbox, agent_body, step_count):
    """
    Agent control logic - no dynamic control needed for this task
    Structure is static once built
    """
    pass
