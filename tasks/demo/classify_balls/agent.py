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

    sensor = sandbox.add_raycast_sensor(
        origin=(-0.5, 5.35),
        direction=(1.0, 0.0),
        length=2.0
    )






    piston = sandbox.add_piston(
        base_pos=(-0.25, 4.0),
        direction=(1.0, 0.0),
        max_length=4.0,
        speed=20.0,
        density=8.0
    )





    delay = sandbox.add_delay(
        input_signal=sensor,
        delay_seconds=3.5,
        output_duration=5.0
    )


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


    if 'input_signal_value' not in delay:
        delay['input_signal_value'] = False





    if detected_color == 'RED':

        delay['input_signal_value'] = True
    elif detected_color == 'BLUE':

        delay['input_signal_value'] = False


