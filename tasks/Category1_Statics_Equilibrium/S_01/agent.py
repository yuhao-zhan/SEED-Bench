"""
S-01: The Bridge task Agent module
Reference solution: Clean flat bridge with minimal supports
"""
import math


def build_agent(sandbox):
    """
    Build a clean flat bridge at ground level (y=10m) to connect two cliffs.
    Simplified design with minimal supports while maintaining stability.
    """
    LEFT_CLIFF_X = 10.0
    RIGHT_CLIFF_X = 25.0
    GAP_WIDTH = 15.0
    
    DECK_TOP_Y = 10.0  # Deck top at cliff level
    DECK_HEIGHT = 0.6  # Thicker deck for stiffness
    DECK_Y = DECK_TOP_Y - DECK_HEIGHT/2  # Deck center: 9.7m
    
    left_cliff = sandbox._terrain_bodies.get("left_cliff")
    right_cliff = sandbox._terrain_bodies.get("right_cliff")
    
    if not left_cliff or not right_cliff:
        raise ValueError("Cliff bodies not found in environment")
    
    # Main deck - Split into 2 beams (7.5m each) to respect 10m max width constraint
    deck_segment_width = 7.5
    
    # Left deck segment: x=10 to x=17.5
    deck_left_center_x = LEFT_CLIFF_X + deck_segment_width / 2
    deck_left = sandbox.add_beam(
        x=deck_left_center_x,
        y=DECK_Y,
        width=deck_segment_width,
        height=DECK_HEIGHT,
        angle=0,
        density=5.0
    )
    for fixture in deck_left.fixtures:
        fixture.friction = 0.8
    
    # Right deck segment: x=17.5 to x=25
    deck_right_center_x = LEFT_CLIFF_X + deck_segment_width + deck_segment_width / 2
    deck_right = sandbox.add_beam(
        x=deck_right_center_x,
        y=DECK_Y,
        width=deck_segment_width,
        height=DECK_HEIGHT,
        angle=0,
        density=5.0
    )
    for fixture in deck_right.fixtures:
        fixture.friction = 0.8
    
    # Connect the two deck segments
    deck_connection_x = LEFT_CLIFF_X + deck_segment_width  # x=17.5
    sandbox.add_joint(deck_left, deck_right, (deck_connection_x, DECK_TOP_Y), type='rigid')
    
    # Single support layer (simplified from 3 layers)
    support_y = 8.0
    
    # Left support segment
    support_left = sandbox.add_beam(
        x=deck_left_center_x,
        y=support_y,
        width=deck_segment_width,
        height=0.8,
        angle=0,
        density=3.0
    )
    
    # Right support segment - shorten to avoid extending into cliff
    # End support layer just before cliff edge (x=24.9m instead of x=25m)
    support_right_end_x = RIGHT_CLIFF_X - 0.1  # End at x=24.9m
    support_right_start_x = deck_connection_x  # Start at x=17.5m
    support_right_width = support_right_end_x - support_right_start_x  # ~7.4m
    support_right_center_x = (support_right_start_x + support_right_end_x) / 2
    support_right = sandbox.add_beam(
        x=support_right_center_x,
        y=support_y,
        width=support_right_width,
        height=0.8,
        angle=0,
        density=3.0
    )
    
    # Connect support segments
    sandbox.add_joint(support_left, support_right, (deck_connection_x, support_y), type='rigid')
    
    # Minimal vertical supports - only 6 evenly spaced supports
    # Stop before cliff edge to avoid extending into cliff
    num_supports = 6
    for i in range(num_supports + 1):
        support_x = LEFT_CLIFF_X + (i * GAP_WIDTH / num_supports)
        
        # Skip support at cliff edge (x=25m) to avoid extending into cliff
        if support_x >= RIGHT_CLIFF_X:
            continue
        
        # Determine which deck segment to connect to
        target_deck = deck_right if support_x >= deck_connection_x else deck_left
        # Only connect to support_right if support_x is within its range
        target_support = support_right if (support_x >= deck_connection_x and support_x <= support_right_end_x) else support_left
        
        vertical = sandbox.add_beam(
            x=support_x,
            y=(support_y + DECK_Y) / 2,
            width=0.5,
            height=abs(DECK_Y - support_y),
            angle=0,
            density=3.0
        )
        sandbox.add_joint(target_support, vertical, (support_x, support_y), type='rigid')
        sandbox.add_joint(target_deck, vertical, (support_x, DECK_TOP_Y), type='rigid')
    
    # Anchor to cliffs - simplified connections
    sandbox.add_joint(left_cliff, deck_left, (LEFT_CLIFF_X, DECK_TOP_Y), type='rigid')
    sandbox.add_joint(left_cliff, support_left, (LEFT_CLIFF_X, support_y), type='rigid')
    
    sandbox.add_joint(right_cliff, deck_right, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    # Anchor support_right at its end point, not at cliff edge
    sandbox.add_joint(right_cliff, support_right, (support_right_end_x, support_y), type='rigid')
    
    # Extension from right cliff edge to target (x=25m to x=30m)
    # Start slightly after cliff edge to avoid extending deep into cliff
    extension_start_x = RIGHT_CLIFF_X + 0.1  # Start just after cliff edge
    extension_end_x = 30.0  # Target position
    extension_width = extension_end_x - extension_start_x  # Calculate width dynamically
    extension_center_x = (extension_start_x + extension_end_x) / 2
    extension = sandbox.add_beam(
        x=extension_center_x,
        y=DECK_Y,
        width=extension_width,
        height=DECK_HEIGHT,
        angle=0,
        density=5.0
    )
    for fixture in extension.fixtures:
        fixture.friction = 0.8
    
    # Connect extension to main deck at cliff edge
    sandbox.add_joint(deck_right, extension, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    # Also anchor to cliff at the edge for stability
    sandbox.add_joint(right_cliff, extension, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    
    print(f"Bridge constructed: {len(sandbox._bodies)} beams, {len(sandbox._joints)} joints, {total_mass:.2f}kg")
    
    return deck_left


def agent_action(sandbox, agent_body, step_count):
    """
    Agent control logic - prevent vehicle from flipping
    """
    if hasattr(sandbox, '_terrain_bodies'):
        vehicle_chassis = sandbox._terrain_bodies.get("vehicle_chassis")
        if vehicle_chassis:
            target_speed = 4.0
            current_vx = vehicle_chassis.linearVelocity.x
            current_vy = vehicle_chassis.linearVelocity.y
            angular_vel = vehicle_chassis.angularVelocity
            angle = vehicle_chassis.angle
            
            # Normalize angle to [-pi, pi]
            normalized_angle = (angle + math.pi) % (2 * math.pi) - math.pi
            
            # Anti-flip control
            if abs(normalized_angle) > 0.3:
                target_speed = 2.0
            elif abs(normalized_angle) > 0.1:
                target_speed = 2.5
            
            if abs(angular_vel) > 0.5:
                target_speed = 1.5
            
            # Smooth velocity control
            if abs(current_vx - target_speed) > 0.01:
                new_vx = current_vx + (target_speed - current_vx) * 0.1
                vehicle_chassis.linearVelocity = (new_vx, current_vy)
            
            # Apply angular damping
            if abs(angular_vel) > 0.3:
                vehicle_chassis.angularVelocity = angular_vel * 0.95
