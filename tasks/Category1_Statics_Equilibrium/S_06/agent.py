import math

def build_agent(sandbox):
    sandbox.add_block(-1.0, 0.2, 4.0, 0.4)
    return None

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    for i in range(5):
        sandbox.add_block(-1.0, 0.2 + i * 0.4, 4.0, 0.4, density=50.0)
    return None

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    for i in range(5):
        sandbox.add_block(-0.8, 0.2 + i * 0.4, 4.0, 0.4, density=100.0)
    return None

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    sandbox.add_block(-0.5, 0.2, 4.0, 0.4, density=200.0)
    sandbox.add_block(-4.5, 0.2, 4.0, 0.4, density=200.0)
    return None

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    y_surface = -0.85
    sandbox.add_block(-0.2, y_surface + 0.2, 4.0, 0.4, density=500.0)
    sandbox.add_block(-4.2, y_surface + 0.2, 4.0, 0.4, density=1000.0)
    return None

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
