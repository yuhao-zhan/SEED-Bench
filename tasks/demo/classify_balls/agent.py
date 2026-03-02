"""
ClassifyBalls task Agent module
Strategy: Use sensor + delay + piston to push red balls right
"""


def build_agent(sandbox):
    """
    Build ball classification device
    
    Strategy:
    - Blue balls naturally fall into blue bin (x=1.0, width=2.0) - NO ACTION NEEDED
    - Red balls need push right to reach red bin (x=4.5, width=2.0, range 3.5-5.5)
    """
    # 1. Sensor: Detect ball color
    sensor = sandbox.add_raycast_sensor(
        origin=(-0.5, 5.35),
        direction=(1.0, 0.0),
        length=2.0
    )
    
    # 2. Piston: Push red balls right
    # Strategy: Push ball right immediately as it leaves conveyor
    # Place piston at conveyor end (x=0.0) at moderate height (y=4.0) to catch ball early
    # Piston head_length=0.5, so base_pos at x=-0.25 means piston starts from x=0.0
    # Piston extends from x=0.0 to x=4.0, pushing ball to red bin (x=4.5, range 3.5-5.5)
    piston = sandbox.add_piston(
        base_pos=(-0.25, 4.0),  # At conveyor end, moderate height to catch falling ball
        direction=(1.0, 0.0),
        max_length=4.0,  # Extends to x=4.0, pushing ball into red bin range
        speed=20.0,  # Fast speed to push ball to red bin
        density=8.0  # Higher density for stronger push
    )
    
    # 3. Delay: Wait for ball to reach piston
    # Ball travels from sensor (-0.5) to conveyor end (0.0) at 0.5 m/s = 1 second
    # Then needs to leave conveyor (x>0) and fall slightly: takes ~2-3 seconds
    # Delay to ensure ball has left conveyor and is falling
    delay = sandbox.add_delay(
        input_signal=sensor,
        delay_seconds=3.5,  # Delay for ball to leave conveyor
        output_duration=5.0  # Long push duration to ensure ball reaches red bin
    )
    
    # 4. Wire
    wire = sandbox.add_wire(source=delay, target=piston)
    
    return {
        'sensor': sensor,
        'piston': piston,
        'delay': delay,
        'wire': wire
    }


def agent_action(sandbox, agent_components, step_count):
    """
    Agent action: Update delay input
    CRITICAL: Only activate piston for RED balls, NOT for BLUE balls
    - When RED ball detected: Set delay input to True (will trigger piston after delay)
    - When BLUE ball detected: Set delay input to False (piston stays retracted)
    - When no ball detected: Keep previous state (don't change)
    """
    sensor = agent_components['sensor']
    delay = agent_components['delay']
    
    detected_color = sandbox.get_detected_object_color(sensor)
    
    # Initialize if not exists
    if 'input_signal_value' not in delay:
        delay['input_signal_value'] = False
    
    # CRITICAL LOGIC: Only trigger delay for RED balls
    # When RED ball is detected, set input to True (rising edge will trigger delay)
    # When BLUE ball is detected, set input to False (no trigger, piston stays retracted)
    # When NONE, keep previous state to avoid interfering with ongoing delay
    if detected_color == 'RED':
        # RED ball detected: Set to True to trigger delay
        delay['input_signal_value'] = True
    elif detected_color == 'BLUE':
        # BLUE ball detected: Set to False to prevent any activation
        delay['input_signal_value'] = False
    # When detected_color == 'NONE', don't change input_signal_value
    # This allows delay to complete its output duration without interference