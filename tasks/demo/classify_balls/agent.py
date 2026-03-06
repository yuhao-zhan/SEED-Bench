





def build_agent(sandbox):





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

        : sensor,

        : piston,

        : delay,

        : wire

    }





def agent_action(sandbox, agent_components, step_count):



    sensor = agent_components['sensor']

    delay = agent_components['delay']



    detected_color = sandbox.get_detected_object_color(sensor)





    if 'input_signal_value' not in delay:

        delay['input_signal_value'] = False











    if detected_color == 'RED':



        delay['input_signal_value'] = True

    elif detected_color == 'BLUE':



        delay['input_signal_value'] = False





